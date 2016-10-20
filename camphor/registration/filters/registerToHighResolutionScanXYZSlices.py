from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO

"""
This filter registers the high-resolution scan to the average trial data
It first calculates the average of all pre-stimulus time frames for all trials,
averages over all trials, up-samples the result and then registers the high-resolution
scan to this data.
"""
class registerToHighResolutionScanXYZSlices(camphorRegistrationMethod):
    def __init__(self):
        super(registerToHighResolutionScanXYZSlices, self).__init__()
        self._parameters = registerToHighResolutionScanXYZSlicesParameters()
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

        for b in brain:
            # Loads the high-res scan
            camphor.openFileFromProject(brain=b, trial=-1, view=0)
            template = [camphor.rawData[i].copy(order='C') for i in range(len(camphor.rawData))]
            transforms = camphor.project.brain[b].highResScan.transforms
            for t in transforms:
                if (t.active):
                    data = t.apply(data)

            nTrials = camphor.project.brain[b].nTrials
            for i in range(nTrials):
                # 1. Loads the data
                camphor.openFileFromProject(brain=b,trial=i,view=0)
                data = [camphor.rawData[i].copy(order='C') for i in range(len(camphor.rawData))]
                #Applies the existing transforms
                transforms = camphor.project.brain[b].trial[i].transforms
                for t in transforms:
                    if(t.active):
                        data = t.apply(data)

                self.message('Registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b + 1, nBrains, i + 1, nTrials),
                             progress=100 * self.nDone / self.nTotal)
                # 3. Register each timeframe to the baseline
                transformlist.append(self.registerImage(template[0], data, camphor.project.brain[b].trial[i]))

                self.nDone += 1

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

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

        nFrames = len(data)
        self.nFrames = nFrames

        # Creates the transform object
        transformobject = registerToHighResolutionScanXYZSlicesTransform(nFrames=nFrames)

        nSlices = template.shape
        totalnSlices = sum(nSlices)

        slicesDone = 0
        for i, d in enumerate(data):
            sliceTransform = []

            # Resamples
            fixed_image = sitk.GetImageFromArray(template.astype(numpy.double)) # template is passed as double already so no need to cast
            moving_image = sitk.GetImageFromArray(d.astype(numpy.double))

            print(fixed_image.GetSize())
            lxf, lyf, lzf = fixed_image.GetSize()
            lxm, lym, lzm = moving_image.GetSize()
            moving_image.SetSpacing((lxf/lxm,lyf/lym,lzf/lzm))

            # First we need to resample the data to match the dimensions of the template
            resampled_image = sitk.Image(fixed_image.GetSize(), fixed_image.GetPixelIDValue())
            resampled_image.SetSpacing((1,1,1))
            resampled_image.SetOrigin(fixed_image.GetOrigin())
            resampled_image.SetDirection(fixed_image.GetDirection())

            # Resample original image using identity transform and the BSpline interpolator.
            resample = sitk.ResampleImageFilter()
            resample.SetReferenceImage(resampled_image)
            resample.SetInterpolator(sitk.sitkBSpline)
            resample.SetTransform(sitk.Transform())
            resampled_image = resample.Execute(moving_image)

            d = sitk.GetArrayFromImage(resampled_image)

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
                    self.percentDone = 100 * slicesDone / (nFrames * totalnSlices)
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

            transformobject.transform[i] = sliceTransform

        self.percentDone = 0
        # Appends the transforms to the target project.trialData object
        target.transforms.append(transformobject)

        return transformobject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = self.percentDone
        progress.totalPercentDone = (self.nDone + self.percentDone/100)/self.nTotal*100
        return progress


class registerToHighResolutionScanXYZSlicesParameters(object):
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

class registerToHighResolutionScanXYZSlicesTransform(transform.transform):
    def __init__(self, nFrames=0):
        super(registerToHighResolutionScanXYZSlicesTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform() for i in range(nFrames)]

        # The transform's name
        self.name = 'registerToHighResolutionScanXYZSlices'

    def apply(self, data):
        transformed_data = []

        print("Applying registerToHighResolutionScanXYZSlicesTransform")
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

                    rimage = sitk.Resample(image, self.transform[i][nDone], sitk.sitkLinear, 0.0,
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
filter = registerToHighResolutionScanXYZSlices

