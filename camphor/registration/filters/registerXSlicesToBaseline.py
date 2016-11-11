"""
This filter calculates the baseline fluorescence of all trials, and for each trial,
registers each x-slice of each time frame to the corresponding x-slice of the trial's own baseline
(slice-wise intra-trial registration)
"""

from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO


class registerXSlicesToBaseline(camphorRegistrationMethod):
    def __init__(self):
        super(registerXSlicesToBaseline, self).__init__()
        self._parameters = registerXSlicesToBaselineParameters()
        self.percentDone = 0
        self.nDone = 0
        self.nTotal = 0

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

                # 2. calculate the mean baseline
                baseline = self.calculateBaseline(data, endframe=camphor.ini['baseline_endframe']).astype(numpy.uint8)

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
        transformobject = registerXSlicesToBaselineTransform(self, nFrames=nFrames)

        nSlices = template.shape[0]

        for i, d in enumerate(data):
            sliceTransform = []
            for curSlice in range(nSlices):
                fixed_image = sitk.GetImageFromArray(template[curSlice,:,].astype(numpy.double))
                moving_image = sitk.GetImageFromArray(d[curSlice,:,:].astype(numpy.double))
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
                self.percentDone = 100*(i * nSlices + curSlice + 1) / (nFrames * nSlices)
                self.registration_method.AddCommand(sitk.sitkIterationEvent, self.updateEvent)

                final_transform = self.registration_method.Execute(fixed_image, moving_image)

                print('Final metric value: {0}'.format(self.registration_method.GetMetricValue()))
                print('Optimizer\'s stopping condition, {0}'.format(self.registration_method.GetOptimizerStopConditionDescription()))

                sliceTransform.append(final_transform)

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
        progress.totalPercentDone = (self.nDone + self.percentDone / 100) / self.nTotal * 100

        return progress

class registerXSlicesToBaselineParameters(object):
    def __init__(self):
        self.learningRate = 1
        self.numberOfIterations = 300
        self.convergenceMinimumValue = 1e-6
        self.convergenceWindowSize = 20
        self.estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration
        self.maximumStepSizeInPhysicalUnits = 0.01

        self._paramType = {'learningRate': ['doubleg', 1e-20, 1000, 1e-1],
                           'numberOfIterations': ['int', 1, 1e+6, 1],
                           'convergenceMinimumValue': ['doubleg', 1e-20, 1, 1e-1],
                           'convergenceWindowSize': ['int', 0, 1e+6, 10],
                           'estimateLearningRate': ['list', [sitk.ImageRegistrationMethod.EachIteration,
                                                             sitk.ImageRegistrationMethod.Once,
                                                             sitk.ImageRegistrationMethod.Never],
                                                    ['Each iteration', 'Once', 'Never']],
                           'maximumStepSizeInPhysicalUnits': ['doubleg', 1e-20, 1000, 1e-1]}

class registerXSlicesToBaselineTransform(transform.transform):
    def __init__(self, regMethod, nFrames=0):
        super(registerXSlicesToBaselineTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TIMESLICEWISE

        # Default transform = identity
        self.transform = [[sitk.Euler3DTransform()] for i in range(nFrames)]

        # The transform's name
        self.name = 'registerXSlicesToBaseline'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):

        transformed_data = []

        print("Applying registerXSlicesToBaselineTransform")
        nslices = data[0].shape[0]

        for i, d in enumerate(data):
            frameData = numpy.zeros(d.shape)
            for curSlice in range(nslices):
                image = sitk.GetImageFromArray(d[curSlice,:,:].astype(numpy.double))
                rimage = sitk.Resample(image, self.transform[i][curSlice], sitk.sitkLinear, 0.0, image.GetPixelIDValue())
                frameData[curSlice,:,] = sitk.GetArrayFromImage(rimage)

            transformed_data.append(frameData.astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = registerXSlicesToBaseline

