from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO

"""
This filter calculates the baseline fluorescence of all trials, and for each trial,
registers each time frame to the trial's own baseline (intra-trial registration)

The filters uses a pre-registration in which each time frame is first registered to the first time frame of each trial.
Pre-registrating should in principle allow calculating an improved baseline for the subsequent registration.

"""
class registerToTrialBaseline2(camphorRegistrationMethod):
    def __init__(self):
        super(registerToTrialBaseline2, self).__init__()
        self._parameters = registerToTrialBaseline2Parameters()
        self.nDone = 0
        self.nTotal = 1
        self.curFrame = 0
        self.nFrames = 1

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
            nTrials = camphor.project.brain[b].nTrials
            for i in range(nTrials):
                # 1. Loads the data
                dataFile = camphor.project.brain[b].trial[i].dataFile
                data = DataIO.LSMLoad(dataFile)
                #Applies the existing transforms
                transforms = camphor.project.brain[b].trial[i].transforms
                for t in transforms:
                    if(t.active):
                        data = t.apply(data)

                # 2. Pre-registers
                self.message('Pre-registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b + 1, nBrains, i + 1, nTrials),
                             progress=100 * self.nDone / self.nTotal)
                preTransform = self.preRegisterImage(data)

                # Applies the pre-transforms in order to calculate the "improved" baseline
                data = preTransform.apply(data)

                # 2. calculate the mean baseline
                baseline = self.calculateBaseline(data, endframe=camphor.ini['baseline_endframe'])

                self.message('Registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b+1, nBrains, i+1, nTrials),
                             progress=100 * (self.nDone+0.5) / self.nTotal)
                # 3. Register each timeframe to the baseline
                transformlist.append(self.registerImage(baseline, data, camphor.project.brain[b].trial[i], preTransform))

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

    def registerImage(self, template, data, target, transformObject):

        # Creates the transform object
        nFrames = len(data)
        self.nFrames = nFrames

        fixed_image = sitk.GetImageFromArray(template.astype(numpy.double))
        for i, d in enumerate(data):
            self.curFrame = i

            moving_image = sitk.GetImageFromArray(d.astype(numpy.double))
            initial_transform = sitk.CenteredTransformInitializer(fixed_image,
                                                                  moving_image,
                                                                  sitk.Euler3DTransform(),
                                                                  sitk.CenteredTransformInitializerFilter.MOMENTS)

            self.registration_method = sitk.ImageRegistrationMethod()

            # similarity metric settings
            if self.parameters.objectiveFunction == 'MattesMutualInformation':
                self.registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
            elif self.parameters.objectiveFunction == 'Correlation':
                self.registration_method.SetMetricAsCorrelation()
            elif self.parameters.objectiveFunction == 'ANTSNeighborhoodCorrelation':
                self.registration_method.SetMetricAsANTSNeighborhoodCorrelation(5)
            elif self.parameters.objectiveFunction == 'JointHistogramMutualInformation':
                self.registration_method.SetMetricAsJointHistogramMutualInformation(numberOfHistogramBins=20,
                                                                                    varianceForJointPDFSmoothing=1.5)
            elif self.parameters.objectiveFunction == 'MeanSquares':
                self.registration_method.SetMetricAsMeanSquares()  # mean squares does not seem to work well at all

            self.registration_method.SetMetricSamplingStrategy(self.registration_method.RANDOM)
            self.registration_method.SetMetricSamplingPercentage(1)

            self.registration_method.SetInterpolator(sitk.sitkLinear)

            self.registration_method.SetOptimizerAsGradientDescent(learningRate=self.parameters.learningRate,
                                                              numberOfIterations=self.parameters.numberOfIterations,
                                                              convergenceMinimumValue=self.parameters.convergenceMinimumValue,
                                                              convergenceWindowSize=self.parameters.convergenceWindowSize,
                                                              estimateLearningRate=self.parameters.estimateLearningRate,
                                                              maximumStepSizeInPhysicalUnits=self.parameters.maximumStepSizeInPhysicalUnits)

            self.registration_method.SetOptimizerScalesFromIndexShift()
            #self.registration_method.SetOptimizerScalesFromJacobian()

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

            transformObject.transform[i].AddTransform(final_transform)

            if self.cancelled:
                return None

        # Appends the transforms to the target project.trialData object
        target.transforms.append(transformObject)

        return transformObject

    def preRegisterImage(self, data):

        # Creates the transform object
        nFrames = len(data)
        self.nFrames = nFrames
        transformObject = registerToTrialBaseline2Transform(nFrames=nFrames)

        fixed_image = sitk.GetImageFromArray(data[0].astype(numpy.double))
        for i, d in enumerate(data):
            self.curFrame = i

            moving_image = sitk.GetImageFromArray(d.astype(numpy.double))
            initial_transform = sitk.CenteredTransformInitializer(fixed_image,
                                                                  moving_image,
                                                                  sitk.Euler3DTransform(),
                                                                  sitk.CenteredTransformInitializerFilter.GEOMETRY)

            self.registration_method = sitk.ImageRegistrationMethod()

            # similarity metric settings
            if self.parameters.objectiveFunction == 'MattesMutualInformation':
                self.registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
            elif self.parameters.objectiveFunction == 'Correlation':
                self.registration_method.SetMetricAsCorrelation()
            elif self.parameters.objectiveFunction == 'ANTSNeighborhoodCorrelation':
                self.registration_method.SetMetricAsANTSNeighborhoodCorrelation(5)
            elif self.parameters.objectiveFunction == 'JointHistogramMutualInformation':
                self.registration_method.SetMetricAsJointHistogramMutualInformation(numberOfHistogramBins=20,varianceForJointPDFSmoothing=1.5)
            elif self.parameters.objectiveFunction == 'MeanSquares':
                self.registration_method.SetMetricAsMeanSquares() # mean squares does not seem to work well at all

            self.registration_method.SetMetricSamplingStrategy(self.registration_method.RANDOM)
            self.registration_method.SetMetricSamplingPercentage(1)

            self.registration_method.SetInterpolator(sitk.sitkLinear)

            self.registration_method.SetOptimizerAsGradientDescent(learningRate=self.parameters.learningRate,
                                                              numberOfIterations=self.parameters.numberOfIterations,
                                                              convergenceMinimumValue=self.parameters.convergenceMinimumValue,
                                                              convergenceWindowSize=self.parameters.convergenceWindowSize,
                                                              estimateLearningRate=self.parameters.estimateLearningRate,
                                                              maximumStepSizeInPhysicalUnits=self.parameters.maximumStepSizeInPhysicalUnits)

            self.registration_method.SetOptimizerScalesFromIndexShift()
            # self.registration_method.SetOptimizerScalesFromJacobian()

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

            transformObject.transform[i] = final_transform

            if self.cancelled:
                return None

        return transformObject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = 100 * (self.curFrame + progress.iteration / self.parameters.numberOfIterations) / self.nFrames
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100

        return progress

class registerToTrialBaseline2Parameters(object):
    def __init__(self):
        self.learningRate = 1
        self.numberOfIterations = 300
        self.convergenceMinimumValue = 1e-6
        self.convergenceWindowSize = 20
        self.estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration
        self.maximumStepSizeInPhysicalUnits = 0.01
        self.objectiveFunction = 'MattesMutualInformation'

        self._paramType = {'learningRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'numberOfIterations': ['int', 1, 1e+6, 1],
                           'convergenceMinimumValue': ['doubleg', 1e-20, 1, 1e-1],
                           'convergenceWindowSize': ['int', 0, 1e+6, 10],
                           'estimateLearningRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                             sitk.ImageRegistrationMethod.Once,
                                                             sitk.ImageRegistrationMethod.Never],
                                                    ['Each iteration', 'Once', 'Never']],
                           'maximumStepSizeInPhysicalUnits': ['doubleg', 1e-20, 1000, 1e-1],
                           'objectiveFunction': ['list', ['MattesMutualInformation',
                                                          'Correlation',
                                                          'ANTSNeighborhoodCorrelation',
                                                          'JointHistogramMutualInformation',
                                                          'MeanSquares'],
                                                 ['Mattes Mutual Information',
                                                  'Correlation',
                                                  'ANTS Neighborhood Correlation',
                                                  'Joint Histogram Mutual Information',
                                                  'MeanSquares']]}

class registerToTrialBaseline2Transform(transform.transform):
    def __init__(self, nFrames=0):
        super(registerToTrialBaseline2Transform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TIMESLICEWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform() for i in range(nFrames)]

        # The transform's name
        self.name = 'registerToTrialBaseline2'

    def apply(self, data):
        transformed_data = []

        print("Applying registerToTrialBaseline2Transform")
        for i,d in enumerate(data):
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform[i], sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerToTrialBaseline2

