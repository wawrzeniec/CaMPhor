from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO

"""
This filter calculates the baseline fluorescence of all trials, and for each trial,
register the baseline to a target template. The same transformation is then applied to all the time frames.

The target template is the baseline of the first brain
"""

class registerBaselineDemons(camphorRegistrationMethod):
    def __init__(self):
        super(registerBaselineDemons, self).__init__()
        self._parameters = registerBaselineDemonsParameters()
        self.nDone = 0
        self.nTotal = 1

    @property
    def parameters(self):
        return self._parameters

    def execute(self, camphor):
        # Only first brain, for now
        brain = range(camphor.project.nBrains)
        brain = [0]

        # Determines the total number of trials to do
        nBrains = len(brain)
        self.nTotal = 0
        for b in brain:
            self.nTotal += camphor.project.brain[b].nTrials

        transformlist = []
        self.nDone = 0

        for b in brain:
            # 1. calculate the mean baseline
            self.message('Calculating baseline', progress=0)
            baseline = self.calculateBaseline(camphor, b)

            # template = numpy.mean(baseline, axis=3)
            template = baseline[:,:,:,0]

            # 2. For each trial, register the baseline to the mean
            nTrials = camphor.project.brain[b].nTrials
            for i in range(nTrials):
                self.message('Registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b+1, nBrains, i+1, nTrials),
                             progress=100 * self.nDone / self.nTotal)
                transformlist.append(self.registerImage(template, baseline[:,:,:,i], camphor.project.brain[b].trial[i]))
                self.nDone += 1

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

        self.message('Registration completed', progress=100)
        return transformlist

    def calculateBaseline(self, camphor, brain):
        camphor.openFileFromProject(brain=brain, trial=0, view=0)
        lx, ly, lz = camphor.rawData[0].shape
        data = camphor.rawData

        nTrials = camphor.project.brain[brain].nTrials
        baseline = numpy.zeros([lx, ly, lz, nTrials])
        for t in range(nTrials):
            if(t>0):
                camphor.openFileFromProject(brain=brain, trial=t, view=0)
                data = camphor.rawData
            transforms = camphor.project.brain[brain].trial[t].transforms
            for trans in transforms:
                if trans.active:
                    data = trans.apply(data)
            for i in range(camphor.ini['baseline_endframe']):
                baseline[:, :, :, t] += data[i]
            baseline[:, :, :, t] /= camphor.ini['baseline_endframe']

        return baseline

    def registerImage(self, template, data, target, mask=None):
        # Creates the transform object
        transformObject = registerBaselineDemonsTransform(self)

        fixed_image = sitk.GetImageFromArray(template.astype(numpy.double))
        moving_image = sitk.GetImageFromArray(data.astype(numpy.double))

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
        self.registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[1])
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

class registerBaselineDemonsParameters(object):
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

class registerBaselineDemonsTransform(transform.transform):
    def __init__(self, regMethod):
        super(registerBaselineDemonsTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = sitk.Euler3DTransform()

        # The transform's name
        self.name = 'registerBaselineDemons'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):
        transformed_data = []

        print("Applying registerBaselineDemonsTransform")
        for d in data:
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform, sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerBaselineDemons

