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
class registerHRSDemons(camphorRegistrationMethod):
    def __init__(self):
        super(registerHRSDemons, self).__init__()
        self._parameters = registerHRSDemonsParameters()
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

    def registerImage(self, template, data, target, mask=None):

        # Creates the transform object
        transformObject = registerHRSDemonsTransform(self)

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

        fixed_image = resampled_template

        ## Then registers using the demons algorithm
        self.registration_method = sitk.ImageRegistrationMethod()

        if mask is not None:
            maskImage = sitk.GetImageFromArray(mask.astype(numpy.double))
            self.registration_method.SetMetricFixedMask(maskImage)

        # Create initial identity transformation.
        transform_to_displacment_field_filter = sitk.TransformToDisplacementFieldFilter()
        transform_to_displacment_field_filter.SetReferenceImage(fixed_image)
        # The image returned from the initial_transform_filter is transferred to the transform and cleared out.
        initial_transform = sitk.DisplacementFieldTransform(
            transform_to_displacment_field_filter.Execute(sitk.Transform()))

        # Regularization (update field - viscous, total field - elastic).
        initial_transform.SetSmoothingGaussianOnUpdate(varianceForUpdateField=self.parameters.sigmaU,
                                                       varianceForTotalField=self.parameters.sigmaTot)

        self.registration_method.SetInitialTransform(initial_transform)

        self.registration_method.SetMetricAsDemons(
            self.parameters.iThresh)  # intensities are equal if the difference is less than 10HU

        # Multi-resolution framework.
        self.registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[8])
        self.registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2])

        self.registration_method.SetInterpolator(sitk.sitkLinear)

        self.registration_method.SetOptimizerAsGradientDescent(learningRate=self.parameters.lRate,
                                                               numberOfIterations=self.parameters.nIter,
                                                               convergenceMinimumValue=self.parameters.convThresh,
                                                               convergenceWindowSize=self.parameters.convWin,
                                                               estimateLearningRate=self.parameters.estLRate,
                                                               maximumStepSizeInPhysicalUnits=self.parameters.maxStep)

        self.registration_method.SetOptimizerScalesFromIndexShift()
        # self.registration_method.SetOptimizerScalesFromJacobian()
        # self.registration_method.SetOptimizerScalesFromPhysicalShift()

        # setup for the multi-resolution framework
        self.registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[1])
        self.registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[0])
        # self.registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        # connect all of the observers so that we can perform plotting during registration
        # self.registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, updateDisplay)
        self.registration_method.AddCommand(sitk.sitkIterationEvent, self.updateEvent)

        print("Starting demons registration")
        final_transform = self.registration_method.Execute(fixed_image, moving_image)

        print('Final metric value: {0}'.format(self.registration_method.GetMetricValue()))
        print('Optimizer\'s stopping condition, {0}'.format(
            self.registration_method.GetOptimizerStopConditionDescription()))

        transformObject.transform = final_transform

        if self.cancelled:
            return None

        target.transforms.append(transformObject)

        return transformObject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = progress.iteration/self.parameters.nIter*100
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100

        return progress

class registerHRSDemonsParameters(object):
    def __init__(self):
        self.lRate = 1
        self.nIter = 300
        self.convThresh = 1e-6
        self.convWin = 5
        self.estLRate = sitk.ImageRegistrationMethod.EachIteration
        self.maxStep = 1
        self.iThresh = 1
        self.sigmaU = 2.0
        self.sigmaTot = 2.0

        self._paramType = {'lRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'nIter': ['int', 1, 1e+6, 1],
                           'convThresh': ['doubleg', 1e-20, 1, 1e-1],
                           'convWin': ['int', 0, 1e+6, 10],
                           'estLRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                 sitk.ImageRegistrationMethod.Once,
                                                 sitk.ImageRegistrationMethod.Never],
                                        ['Each iteration', 'Once', 'Never']],
                           'maxStep': ['doubleg', 1e-20, 1000, 1e-1],
                           'iThresh': ['int', 1, 255, 1],
                           'sigmaU': ['doubleg', 0, 100, 1e-2],
                           'sigmaTot': ['doubleg', 0, 100, 1e-2]}

class registerHRSDemonsTransform(transform.transform):
    def __init__(self, regMethod):
        super(registerHRSDemonsTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform()]

        # The transform's name
        self.name = 'registerHRSDemons'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):
        transformed_data = []

        print("Applying registerHRSDemonsTransform")
        for i,d in enumerate(data):
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform, sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerHRSDemons

