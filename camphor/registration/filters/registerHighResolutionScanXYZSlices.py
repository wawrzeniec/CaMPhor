from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO

"""
This filter registers the high-resolution scan to the average trial data
It first calculates the average of all pre-stimulus time frames for all trials,
averages over all trials, up-samples the result and then registers the high-resolution
scan to this data by using x-y-z slice registration
"""
class registerHighResolutionScanXYZSlices(camphorRegistrationMethod):
    def __init__(self):
        super(registerHighResolutionScanXYZSlices, self).__init__()
        self._parameters = registerHighResolutionScanXYZSlicesParameters()
        self.nDone = 0
        self.nTotal = 1

    @property
    def parameters(self):
        return self._parameters

    def execute(self, camphor):
        # Only first brain, for now
        brain = range(camphor.project.nBrains)
        brain = [0]

        # Checks that the HRS exists in all target brains
        for b in brain:
            if camphor.project.brain[b].highResScan is None:
                self.message('Error: No high-resolution scan in brain #{:d}', progress=100)
                return None

        # Determines the total number of trials to do
        nBrains = len(brain)
        self.nTotal = 0
        for b in brain:
            self.nTotal += camphor.project.brain[b].nTrials

        transformlist = []
        self.nDone = 0

        self.message('[Step 1 of 3] Calculating baselines...',progress=0)
        for b in brain:
            nTrials = camphor.project.brain[b].nTrials
            baselines = []
            for i in range(nTrials):
                # 1. Loads the data
                camphor.openFileFromProject(brain=b,trial=i,view=0)
                data = camphor.rawData
                #Applies the existing transforms
                transforms = camphor.project.brain[b].trial[i].transforms
                for t in transforms:
                    if(t.active):
                        data = t.apply(data)

                # 2. calculate the mean baseline
                baselines.append(self.calculateBaseline(data, endframe=camphor.ini['baseline_endframe']))

                self.nDone += 1
                self.message('[Step 1 of 3] Calculating baselines {:d}/{:d}, trial {:d}/{:d}'.format(b+1, nBrains, i+1, nTrials),
                             progress=100 * self.nDone / self.nTotal)

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

            self.nDone = 0
            self.nTotal = len(baselines)
            self.message('[Step 2 of 3] Averaging baselines...', progress=100 * self.nDone / self.nTotal)
            averageBaseline = numpy.zeros(baselines[0].shape, dtype=numpy.double)
            for bl in baselines:
                averageBaseline += bl
                self.nDone += 1
                self.message('[Step 2 of 3] Averaging baselines...', progress=100 * self.nDone / self.nTotal)

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

            averageBaseline /= self.nTotal

            # Loads the high-res scan
            camphor.openFileFromProject(brain=b, trial=-1, view=0)
            data = camphor.rawData
            transforms = camphor.project.brain[b].highResScan.transforms
            for t in transforms:
                if (t.active):
                    data = t.apply(data)

            self.message('[Step 3 of 3] Registering high-resolution scan...', progress=0)
            transformlist.append(self.registerImage(averageBaseline, data, camphor.project.brain[b].highResScan))

        self.message('Registration completed', progress=100)
        return transformlist

    def calculateBaseline(self, data, endframe):

        lx, ly, lz = data[0].shape

        baseline = numpy.zeros([lx, ly, lz])
        for i in range(endframe):
            baseline[:, :, :] += data[i]
        baseline[:, :, :] /= endframe

        return baseline

    def registerImage(self, template, data, target):

        # Creates the transform object
        transformobject = registerHighResolutionScanXYZSlicesTransform(self)

        fixed_image = sitk.GetImageFromArray(template) # template is passed as double already so no need to cast
        moving_image = sitk.GetImageFromArray(data[0].astype(numpy.double))

        lxf,lyf,lzf = fixed_image.GetSize()
        lxm, lym, lzm = moving_image.GetSize()
        fixed_image.SetSpacing((lxm/lxf,lym/lyf,lzm/lzf))

        # First we need to resample the template to match the dimensions of the data
        resampled_template = sitk.Image(moving_image.GetSize(), moving_image.GetPixelIDValue())
        resampled_template.SetSpacing((1,1,1))
        resampled_template.SetOrigin(moving_image.GetOrigin())
        resampled_template.SetDirection(moving_image.GetDirection())

        # Resample original image using identity transform and the BSpline interpolator.
        resample = sitk.ResampleImageFilter()
        resample.SetReferenceImage(resampled_template)
        resample.SetInterpolator(sitk.sitkBSpline)
        resample.SetTransform(sitk.Transform())
        resampled_template  = resample.Execute(fixed_image)

        template = sitk.GetArrayFromImage(resampled_template)
        d = data[0]

        nSlices = template.shape
        totalnSlices = sum(nSlices)

        slicesDone = 0
        sliceTransform = []

        self.nTotal = totalnSlices
        self.nDone = slicesDone

        for curAxis in range(3):
            for curSlice in range(nSlices[curAxis]):
                if curAxis == 0:
                    fixed_image = sitk.GetImageFromArray(template[curSlice, :, :].astype(numpy.double))
                    moving_image = sitk.GetImageFromArray(d[curSlice, :, :].astype(numpy.double))
                elif curAxis == 1:
                    fixed_image = sitk.GetImageFromArray(template[:, curSlice, :].astype(numpy.double))
                    moving_image = sitk.GetImageFromArray(d[:, curSlice, :].astype(numpy.double))
                elif curAxis == 2:
                    fixed_image = sitk.GetImageFromArray(template[:, :, curSlice].astype(numpy.double))
                    moving_image = sitk.GetImageFromArray(d[:, :, curSlice].astype(numpy.double))

                initial_transform = sitk.CenteredTransformInitializer(fixed_image,
                                                                      moving_image,
                                                                      sitk.Euler2DTransform(),
                                                                      sitk.CenteredTransformInitializerFilter.GEOMETRY)

                self.registration_method = sitk.ImageRegistrationMethod()

                # similarity metric settings
                # registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
                self.registration_method.SetMetricAsCorrelation()
                # registration_method.SetMetricAsANTSNeighborhoodCorrelation(5)
                # registration_method.SetMetricAsJointHistogramMutualInformation(numberOfHistogramBins=20,varianceForJointPDFSmoothing=1.5)
                # registration_method.SetMetricAsMeanSquares() # mean squares does not seem to work well at all

                self.registration_method.SetMetricSamplingStrategy(self.registration_method.RANDOM)
                self.registration_method.SetMetricSamplingPercentage(1)

                self.registration_method.SetInterpolator(sitk.sitkLinear)

                self.registration_method.SetOptimizerAsGradientDescent(learningRate=self.parameters.learningRate,
                                                                       numberOfIterations=self.parameters.numberOfIterations,
                                                                       convergenceMinimumValue=self.parameters.convergenceMinimumValue,
                                                                       convergenceWindowSize=self.parameters.convergenceWindowSize,
                                                                       estimateLearningRate=self.parameters.estimateLearningRate,
                                                                       maximumStepSizeInPhysicalUnits=self.parameters.maximumStepSizeInPhysicalUnits)

                # registration_method.SetOptimizerScalesFromIndexShift()
                self.registration_method.SetOptimizerScalesFromJacobian()

                # setup for the multi-resolution framework
                self.registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[1])
                self.registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[1])
                # self.registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

                # don't optimize in-place, we would possibly like to run this cell multiple times
                self.registration_method.SetInitialTransform(initial_transform, inPlace=False)

                # connect all of the observers so that we can perform plotting during registration
                # self.registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, updateDisplay)
                self.percentDone = 100 * slicesDone / totalnSlices
                self.registration_method.AddCommand(sitk.sitkIterationEvent, self.updateEvent)

                final_transform = self.registration_method.Execute(fixed_image, moving_image)

                print('Final metric value: {0}'.format(self.registration_method.GetMetricValue()))
                print('Optimizer\'s stopping condition, {0}'.format(
                    self.registration_method.GetOptimizerStopConditionDescription()))

                sliceTransform.append(final_transform)

                # Replaces the data with the registered slice
                if curAxis == 0:
                    d[curSlice, :, :] = sitk.GetArrayFromImage(sitk.Resample(
                        moving_image, final_transform, sitk.sitkLinear, 0.0,
                        moving_image.GetPixelIDValue())).astype(numpy.uint8)
                elif curAxis == 1:
                    d[:, curSlice, :] = sitk.GetArrayFromImage(sitk.Resample(
                        moving_image, final_transform, sitk.sitkLinear, 0.0,
                        moving_image.GetPixelIDValue())).astype(numpy.uint8)
                elif curAxis == 2:
                    d[:, :, curSlice] = sitk.GetArrayFromImage(sitk.Resample(
                        moving_image, final_transform, sitk.sitkLinear, 0.0,
                        moving_image.GetPixelIDValue())).astype(numpy.uint8)

                slicesDone += 1
                if self.cancelled:
                    return None

        transformobject.transform = [sliceTransform]

        self.percentDone = 0
        # Appends the transforms to the target project.trialData object
        target.transforms.append(transformobject)

        return transformobject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = 100 * (progress.iteration / self.parameters.numberOfIterations)
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100
        self.progress = progress.percentDone
        return progress

class registerHighResolutionScanXYZSlicesParameters(object):
    def __init__(self):
        self.learningRate = 1
        self.numberOfIterations = 300
        self.convergenceMinimumValue = 1e-6
        self.convergenceWindowSize = 20
        self.estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration
        self.maximumStepSizeInPhysicalUnits = 0.1

        self._paramType = {'learningRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'numberOfIterations': ['int', 1, 1e+6, 1],
                           'convergenceMinimumValue': ['doubleg', 1e-20, 1, 1e-1],
                           'convergenceWindowSize': ['int', 0, 1e+6, 10],
                           'estimateLearningRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                             sitk.ImageRegistrationMethod.Once,
                                                             sitk.ImageRegistrationMethod.Never],
                                                    ['Each iteration', 'Once', 'Never']],
                           'maximumStepSizeInPhysicalUnits': ['doubleg', 1e-20, 1000, 1e-1]}

class registerHighResolutionScanXYZSlicesTransform(transform.transform):
    def __init__(self, regMethod):
        super(registerHighResolutionScanXYZSlicesTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform()]

        # The transform's name
        self.name = 'registerHighResolutionScanXYZSlices'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):
        transformed_data = []

        print("Applying registerHighResolutionScanXYZSlicesTransform")
        nSlices = data[0].shape
        totalnSlices = sum(nSlices)

        for i, d in enumerate(data):
            frameData = d.copy(order='C')
            nDone = 0
            for curAxis in range(3):
                for curSlice in range(nSlices[curAxis]):
                    if curAxis == 0:
                        image = sitk.GetImageFromArray(frameData[curSlice, :, :].astype(numpy.double))
                    elif curAxis == 1:
                        image = sitk.GetImageFromArray(frameData[:, curSlice, :].astype(numpy.double))
                    elif curAxis == 2:
                        image = sitk.GetImageFromArray(frameData[:, :, curSlice].astype(numpy.double))

                    # Here we use transform[0] because the HRS is only a single time frame. However, when overlaying a trial with the HRS,
                    # we make it the same number of time frames as the data by copying it
                    rimage = sitk.Resample(image, self.transform[0][nDone], sitk.sitkLinear, 0.0,
                                           image.GetPixelIDValue())

                    if curAxis == 0:
                        frameData[curSlice, :, :] = sitk.GetArrayFromImage(rimage).astype(numpy.uint8)
                    elif curAxis == 1:
                        frameData[:, curSlice, :] = sitk.GetArrayFromImage(rimage).astype(numpy.uint8)
                    elif curAxis == 2:
                        frameData[:, :, curSlice] = sitk.GetArrayFromImage(rimage).astype(numpy.uint8)
                    nDone += 1

            transformed_data.append(frameData)

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerHighResolutionScanXYZSlices

