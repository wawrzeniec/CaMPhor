from camphor.registration.camphorRegistrationMethod import camphorRegistrationMethod, camphorRegistrationProgress
import SimpleITK as sitk
import numpy
from camphor.registration import transform
import camphor.DataIO as DataIO
from camphor import utils
from scipy import stats
from scipy import ndimage

"""
This filter calculates the baseline fluorescence of all trials, and for each trial,
registers each time frame to the trial's own baseline (intra-trial registration)

The filters uses a pre-registration in which each time frame is first registered to the first time frame of each trial.
Pre-registrating should in principle allow calculating an improved baseline for the subsequent registration.

"""
class preRegisterDemons(camphorRegistrationMethod):
    def __init__(self):
        super(preRegisterDemons, self).__init__()
        self._parameters = preRegisterDemonsParameters()
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
            for iTrial in range(nTrials): ##### !!!!!!! Only 2nd trial!!1
                # 1. Loads the data
                dataFile = camphor.project.brain[b].trial[iTrial].dataFile
                data = DataIO.LSMLoad(dataFile)
                #Applies the existing transforms
                transforms = camphor.project.brain[b].trial[iTrial].transforms
                for t in transforms:
                    if(t.active):
                        data = t.apply(data)

                # downscales the data
                # f = utils.calculatedF(data)
                #
                # w = numpy.stack(f)
                # s = numpy.std(w, 0)
                # sm = numpy.median(s)
                #
                # mask = s > 0.5*sm

                mask = None

                # c = [ndimage.gaussian_filter(d, 5, order=0) for d in data]
                # cf = utils.calculatedF(c)
                # mask = cf[0]>5
                # for i in range(1,len(cf)):
                #     mask = numpy.logical_or(mask,cf[i]>5)
                # mask = 1-mask
                # data = c

                # 2. Pre-registers
                self.message('Pre-registering brain {:d}/{:d}, trial {:d}/{:d}'.format(b + 1, nBrains, iTrial + 1, nTrials),
                             progress=100 * self.nDone / self.nTotal)
                transformlist.append(self.preRegisterImage(data, camphor.project.brain[b].trial[iTrial], mask=mask))

                self.nDone += 1

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

        self.message('Registration completed', progress=100)
        return transformlist

    def preRegisterImage(self, data, target, mask=None):

        # Creates the transform object
        nFrames = len(data)
        self.nFrames = nFrames
        transformObject = preRegisterDemonsTransform(self, nFrames=nFrames)

        ## Here use the mean as teh template!!!!!
        w = numpy.stack(data)
        m = numpy.mean(w, 0)
        fixed_image = sitk.GetImageFromArray(m.astype(numpy.double))
        # fixed_image = sitk.GetImageFromArray(data[0].astype(numpy.double))
        for i, d in enumerate(data):
            self.curFrame = i

            moving_image = sitk.GetImageFromArray(d.astype(numpy.double))

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

            self.registration_method.SetMetricAsDemons(self.parameters.iThresh)  # intensities are equal if the difference is less than 10HU

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
            #self.registration_method.SetOptimizerScalesFromJacobian()
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
            print('Optimizer\'s stopping condition, {0}'.format(self.registration_method.GetOptimizerStopConditionDescription()))

            transformObject.transform[i] = final_transform

            if self.cancelled:
                return None

        target.transforms.append(transformObject)

        return transformObject

    def getProgress(self):
        progress = camphorRegistrationProgress()
        progress.iteration = self.registration_method.GetOptimizerIteration()
        progress.objectiveFunctionValue = self.registration_method.GetMetricValue()
        progress.percentDone = 100 * (self.curFrame + progress.iteration / self.parameters.nIter) / self.nFrames
        progress.totalPercentDone = (self.nDone + progress.percentDone / 100) / self.nTotal * 100

        return progress

class preRegisterDemonsParameters(object):
    def __init__(self):
        self.lRate = 1
        self.nIter = 300
        self.convThresh = 1e-6
        self.convWin = 5
        self.estLRate = sitk.ImageRegistrationMethod.EachIteration
        self.maxStep = 1
        self.iThresh = 1
        self.sigmaU = 0.0
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

class preRegisterDemonsTransform(transform.transform):
    def __init__(self, regMethod, nFrames=0):
        super(preRegisterDemonsTransform, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TIMESLICEWISE

        # Default transform = identity
        self.transform = [sitk.Euler3DTransform() for i in range(nFrames)]

        # The transform's name
        self.name = 'preRegisterDemons'

        # The camphorRegistrationMethod object that created this transform (to keep track of parameters)
        self.registrationMethod = regMethod.__class__
        self.registrationParameters = regMethod.parameters

    def apply(self, data):
        transformed_data = []

        print("Applying preRegisterDemonsTransform")
        for i,d in enumerate(data):
            image = sitk.GetImageFromArray(d.astype(numpy.double))
            rimage = sitk.Resample(image, self.transform[i], sitk.sitkLinear, 0.0, image.GetPixelIDValue())
            transformed_data.append(sitk.GetArrayFromImage(rimage).astype(numpy.uint8))

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = preRegisterDemons

