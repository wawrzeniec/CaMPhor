from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO

"""
This filter calculates the baseline fluorescence of all trials, and for each trial,
registers each time frame to the trial's own baseline (intra-trial registration)
"""
class registerToTrialBaseline(camphorRegistrationMethod):
    def __init__(self):
        super(registerToTrialBaseline, self).__init__()
        self._parameters = registerToTrialBaselineParameters()
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
            for i in [2]: #range(nTrials): ### |||||||||||| only trial 2 !!!!!!!!
                # 1. Loads the data
                dataFile = camphor.project.brain[b].trial[i].dataFile
                data = DataIO.LSMLoad(dataFile)
                #Applies the existing transforms
                transforms = camphor.project.brain[b].trial[i].transforms
                for t in transforms:
                    if(t.active):
                        data = t.apply(data)

                # 2. calculate the mean baseline
                baseline = self.calculateBaseline(data, endframe=camphor.ini['baseline_endframe'])

                self.message('Registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b+1, nBrains, i+1, nTrials),
                             progress=100 * self.nDone / self.nTotal)
                # 3. Register each timeframe to the baseline
                transformlist.append(self.registerImage(baseline, data, camphor.project.brain[b].trial[i]))

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

        # Creates the transform object
        nFrames = len(data)
        self.nFrames = nFrames
        transformobject = registerToTrialBaselineTransform(self, nFrames=nFrames)

        fixed_image = sitk.GetImageFromArray(template.astype(numpy.double))
        for i, d in enumerate(data):
            self.curFrame = i

            moving_image = sitk.GetImageFromArray(d.astype(numpy.double))
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

            self.registration_method.SetOptimizerAsGradientDescent(learnRate=self.parameters.learnRate,
                                                              nIter=self.parameters.nIter,
                                                              convMinValue=self.parameters.convMinValue,
                                                              convWinSize=self.parameters.convWinSize,
                                                              estimateLRate=self.parameters.estimateLRate,
                                                              maxStepSize=self.parameters.maxStepSize)

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

            transformobject.transform[i] = final_transform

            if self.cancelled:
                return None

        # Appends the transforms to the target project.trialData object
        target.transforms.append(transformobject)

        return transformobject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = 100 * (self.curFrame + progress.iteration / self.parameters.nIter) / self.nFrames
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100

        return progress

class registerToTrialBaselineParameters(object):
    def __init__(self):
        self.learnRate = 1
        self.nIter = 300
        self.convMinValue = 1e-6
        self.convWinSize = 20
        self.estimateLRate = sitk.ImageRegistrationMethod.EachIteration
        self.maxStepSize = 0.01

        self._paramType = {'learnRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'nIter': ['int', 1, 1e+6, 1],
                           'convMinValue': ['doubleg', 1e-20, 1, 1e-1],
                           'convWinSize': ['int', 0, 1e+6, 10],
                           'estimateLRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                             sitk.ImageRegistrationMethod.Once,
                                                             sitk.ImageRegistrationMethod.Never],
                                                    ['Each iteration', 'Once', 'Never']],
                           'maxStepSize': ['doubleg', 1e-20, 1000, 1e-1]}

class registerToTrialBaselineTransform(transform.transform):
    def __init__(self, regMethod, nFrames=0):
        super(registerToTrialBaselineTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TIMESLICEWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform() for i in range(nFrames)]

        # The transform's name
        self.name = 'registerToTrialBaseline'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):
        transformed_data = []

        print("Applying registerToTrialBaselineTransform")
        for i,d in enumerate(data):
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform[i], sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerToTrialBaseline

