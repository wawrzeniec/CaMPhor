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

class registerBaseline(camphorRegistrationMethod):
    def __init__(self):
        super(registerBaseline, self).__init__()
        self._parameters = registerBaselineParameters()
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

            # Displays the mean baseline in vtkView
            camphor.vtkView.assignData([template.astype(numpy.uint8)])

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

        nTrials = camphor.project.brain[brain].nTrials
        baseline = numpy.zeros([lx, ly, lz, nTrials])
        for t in range(nTrials):
            if(t>0):
                camphor.openFileFromProject(brain=brain, trial=t, view=0)
            for i in range(camphor.ini['baseline_endframe']):
                baseline[:, :, :, t] += camphor.rawData[i]
            baseline[:, :, :, t] /= camphor.ini['baseline_endframe']

        return baseline

    def registerImage(self, template, data, target):
        fixed_image = sitk.GetImageFromArray(template)
        moving_image = sitk.GetImageFromArray(data)

        initial_transform = sitk.CenteredTransformInitializer(fixed_image,
                                                              moving_image,
                                                              sitk.Euler3DTransform(),
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

        # registration_method.SetOptimizerAsConjugateGradientLineSearch 	(learningRate=lRate,
        #         numberOfIterations = niter,
        #         convergenceMinimumValue = minconv,
        #         convergenceWindowSize = winSize,
        #         lineSearchLowerLimit = 0,
        #         lineSearchUpperLimit = 5.0,
        #         lineSearchEpsilon = 0.01,
        #         lineSearchMaximumIterations = 20,
        #         estimateLearningRate = sitk.ImageRegistrationMethod.Once,
        #         maximumStepSizeInPhysicalUnits = 0.0
        #         )

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
        self.registration_method.AddCommand(sitk.sitkIterationEvent, self.updateEvent)

        final_transform = self.registration_method.Execute(fixed_image, moving_image)

        print('Final metric value: {0}'.format(self.registration_method.GetMetricValue()))
        print('Optimizer\'s stopping condition, {0}'.format(self.registration_method.GetOptimizerStopConditionDescription()))

        transformobject = registerBaselineTransform()
        transformobject.transform = final_transform

        print(target)
        target.transforms.append(transformobject)

        return transformobject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = progress.iteration/self.parameters.numberOfIterations*100
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100

        return progress

class registerBaselineParameters(object):
    def __init__(self):
        self.learningRate = 2
        self.numberOfIterations = 300
        self.convergenceMinimumValue = 1e-6
        self.convergenceWindowSize = 20
        self.estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration
        self.maximumStepSizeInPhysicalUnits = 0.1

        self._paramType = {'learningRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'numberOfIterations': ['int', 1, 1e+6, 1],
                           'convergenceMinimumValue': ['doubleg', 1e-20, 10, 1e-6],
                           'convergenceWindowSize': ['int', 0, 1e+6, 10],
                           'estimateLearningRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                             sitk.ImageRegistrationMethod.Once,
                                                             sitk.ImageRegistrationMethod.Never],
                                                    ['Each iteration', 'Once', 'Never']],
                           'maximumStepSizeInPhysicalUnits': ['doubleg', 1e-20, 1000, 1e-1]}

class registerBaselineTransform(transform.transform):
    def __init__(self):
        super(registerBaselineTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = sitk.Euler3DTransform()

        # The transform's name
        self.name = 'registerBaseline'

    def apply(self, data):
        transformed_data = []

        print("Applying registerBaselineTransform")
        for d in data:
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform, sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerBaseline

