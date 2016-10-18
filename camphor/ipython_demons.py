import sys
import os
# Adds the path otherwise it doesn't work
sys.path.insert(0, "C:\\Users\\chantal\\PycharmProjects\\CaMPhor")
sys.path.append('C:\\Users\\Chantal\\PycharmProjects\\CaMPhor\\camphor')
os.chdir('C:\\Users\\Chantal\\PycharmProjects\\CaMPhor')

from camphor import camphor
from PyQt4 import QtGui

import numpy as np
import imp
import SimpleITK as sitk
import time
import vtk


app = QtGui.QApplication(sys.argv)

# to reload if any changes have been made
# imp.reload(camphor); del self

self = camphor.camphor()

def generateCubeData(imageSize=50, nCubes=10, cubeSize=4, backgroundNoise=1, positionNoise=1, intensityNoise=1, nSlices=10):
    # 1. Generate center positions for cubes, avoiding overlap as much as possible

    maxnCubes = np.floor(imageSize**3/cubeSize**3/2)
    if(nCubes > maxnCubes):
        nCubes = maxnCubes
        print("generateCubeData::Warning::\nnCubes is too high, set to {:d}".format(nCubes))

    def genNextCenter(cubeCenter,n):
        maxIter = 1000

        nIter = 0
        while True:
            nIter += 1
            c = np.random.uniform(low=cubeSize,high=imageSize-cubeSize-1,size=(1,3))
            d = [np.sqrt(np.sum((cubeCenter[i,:] - c)**2)) for i in range(n)]
            if np.max(d) > cubeSize:
                break
            if(nIter > maxIter):
                print("genNextCenter: maximum number of iterations exceeded. Aborting.")
                break
        return c

    # Generates cube centers
    cubeCenter = np.zeros((nCubes, 3))
    cubeCenter[0,:] = np.random.uniform(low=cubeSize, high=imageSize - cubeSize - 1, size=(1, 3))
    for i in range(1,nCubes):
        cubeCenter[i,:] = genNextCenter(cubeCenter,i)

    cubeAmplitude = np.random.uniform(low=100,high=235,size=(nCubes,1)).astype(np.uint8)

    data = [np.random.normal(20, backgroundNoise, [imageSize, imageSize, imageSize]).astype(np.uint8) for i in range(nSlices)]
    for t in range(nSlices):
        pNoise = np.random.normal(0, positionNoise, (3)).astype(np.int)
        for i in range(nCubes):
            data[t][int(np.floor(cubeCenter[i, 0] - pNoise[0] - cubeSize / 2)):int(np.floor(cubeCenter[i, 0] - pNoise[0] + cubeSize / 2)),
                    int(np.floor(cubeCenter[i, 1] - pNoise[1] - cubeSize / 2)):int(np.floor(cubeCenter[i, 1] - pNoise[1] + cubeSize / 2)),
                    int(np.floor(cubeCenter[i, 2] - pNoise[2] - cubeSize / 2)):int(np.floor(cubeCenter[i, 2] - pNoise[2] + cubeSize / 2))] = cubeAmplitude[i] + np.random.normal(0, intensityNoise)

    return data


data = generateCubeData(nSlices = 5, positionNoise = 2)
self.vtkView.assignData(data)
self.rawData = data

if(not self.dataLoaded):
    origCam = vtk.vtkOpenGLCamera()
    origCam.DeepCopy(self.vtkView.renderer.GetActiveCamera())
    origCam2 = vtk.vtkOpenGLCamera()
    origCam2.DeepCopy(self.vtkView2.renderer.GetActiveCamera())
    self.dataLoaded = True

def resetView():
    self.vtkView.renderer.GetActiveCamera().DeepCopy(origCam)
    self.vtkView2.renderer.GetActiveCamera().DeepCopy(origCam2)
    self.vtkView.renwin.Render()
    self.vtkView2.renwin.Render()

# Registration part

def updateDisplay():
    iter = registration_method.GetOptimizerIteration()
    print("iteration #{:d}: {:f} (learning rate = {:f})".format(iter, registration_method.GetMetricValue(),registration_method.GetOptimizerLearningRate()))
    if(iter > 0):
        current_transform = sitk.Transform(registration_method.GetInitialTransform())
        current_transform.SetParameters(registration_method.GetOptimizerPosition())
        current_transform.AddTransform(registration_method.GetMovingInitialTransform())
        current_transform.AddTransform(registration_method.GetFixedInitialTransform().GetInverse())

        registered_image = sitk.Resample(moving_image, fixed_image, current_transform, sitk.sitkLinear, 0.0,
                                     moving_image.GetPixelIDValue())
        registered_data = sitk.GetArrayFromImage(registered_image).astype(np.uint8)
        self.vtkView2.assignData([registered_data])
        self.vtkView2.renwin.Render()
        time.sleep(0.01)

def updateDisplayDemons(registration_method):
    iter = registration_method.GetElapsedIterations()
    print("iteration #{:d}: {:f})".format(iter, registration_method.GetMetric()))

def showFinal():
    registered_image = sitk.Resample(moving_image, fixed_image, final_transform, sitk.sitkLinear, 0.0,
                                 moving_image.GetPixelIDValue())
    registered_data = sitk.GetArrayFromImage(registered_image).astype(np.uint8)
    self.vtkView2.assignData([registered_data])

def showInitial():
    self.vtkView2.assignData([data2])

def showDiff():
    registered_image = sitk.Resample(moving_image, fixed_image, final_transform, sitk.sitkLinear, 0.0,
                                     moving_image.GetPixelIDValue())
    registered_data = sitk.GetArrayFromImage(registered_image)
    diff = np.abs(data1.astype(np.double) - registered_data).astype(np.uint8)
    self.vtkView2.assignData([diff])
    print(np.sum(diff**2))


def showDiff0():
    diff = np.abs(data1.astype(np.double) - data2.astype(np.double)).astype(np.uint8)
    self.vtkView2.assignData([diff])
    print(np.sum(diff ** 2))


def showMax():
    registered_image = sitk.Resample(moving_image, fixed_image, final_transform, sitk.sitkLinear, 0.0,
                                     moving_image.GetPixelIDValue())
    registered_data = sitk.GetArrayFromImage(registered_image).astype(np.uint8)
    self.vtkView2.assignData([np.maximum(data1,registered_data)])


##########################################################################
########################## rigid registration ###########################
##########################################################################

lRate = 1
niter = 50
minconv = 1e-6
winSize = 20
maxStep = 0.1

transforms = []
for i in range(self.vtkView.nt):
    data1 = self.rawData[0]
    data2 = self.rawData[i]
    # self.vtkView.assignData([data1])
    self.vtkView2.assignData([data2])

    fixed_image = sitk.GetImageFromArray(data1.astype(np.double))
    moving_image = sitk.GetImageFromArray(data2.astype(np.double))
    registered_data = data2

    initial_transform = sitk.CenteredTransformInitializer(fixed_image,
                                                          moving_image,
                                                          sitk.Euler3DTransform(),
                                                          sitk.CenteredTransformInitializerFilter.GEOMETRY)

    registration_method = sitk.ImageRegistrationMethod()

    #similarity metric settings
    # registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
    registration_method.SetMetricAsCorrelation()
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(1)

    registration_method.SetInterpolator(sitk.sitkLinear)

    registration_method.SetOptimizerAsGradientDescent(learningRate=lRate,
                                                      numberOfIterations=niter,
                                                      convergenceMinimumValue=minconv,
                                                      convergenceWindowSize=winSize,
                                                      estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration,
                                                      maximumStepSizeInPhysicalUnits = maxStep)

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
    registration_method.SetOptimizerScalesFromJacobian()


    #setup for the multi-resolution framework
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors = [1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[1])
    # registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    #don't optimize in-place, we would possibly like to run this cell multiple times
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    #connect all of the observers so that we can perform plotting during registration
    # registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, updateDisplay)
    registration_method.AddCommand(sitk.sitkIterationEvent, updateDisplay)

    final_transform = registration_method.Execute(sitk.Cast(fixed_image, sitk.sitkFloat32),
                                                  sitk.Cast(moving_image, sitk.sitkFloat32))

    print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
    print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))
    showFinal()

    transforms.append(final_transform)

##########################################################################
########################## demons registration ##########################
##########################################################################


transforms = []
for i in range(self.vtkView.nt):
    data1 = self.rawData[0]
    data2 = self.rawData[i]
    # self.vtkView.assignData([data1])
    self.vtkView2.assignData([data2])

    fixed_image = sitk.GetImageFromArray(data1.astype(np.double))
    moving_image = sitk.GetImageFromArray(data2.astype(np.double))
    registered_data = data2

    registration_method = sitk.ImageRegistrationMethod()

    # Create initial identity transformation.
    transform_to_displacment_field_filter = sitk.TransformToDisplacementFieldFilter()
    transform_to_displacment_field_filter.SetReferenceImage(fixed_image)
    # The image returned from the initial_transform_filter is transferred to the transform and cleared out.
    initial_transform = sitk.DisplacementFieldTransform(transform_to_displacment_field_filter.Execute(sitk.Transform()))

    # Regularization (update field - viscous, total field - elastic).
    initial_transform.SetSmoothingGaussianOnUpdate(varianceForUpdateField=0.0, varianceForTotalField=2.0)

    registration_method.SetInitialTransform(initial_transform)

    registration_method.SetMetricAsDemons(10)  # intensities are equal if the difference is less than 10HU

    # Multi-resolution framework.
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[0])

    registration_method.SetInterpolator(sitk.sitkLinear)
    # If you have time, run this code as is, otherwise switch to the gradient descent optimizer
    registration_method.SetOptimizerAsGradientDescent(learningRate=lRate,
                                                      numberOfIterations=niter,
                                                      convergenceMinimumValue=minconv,
                                                      convergenceWindowSize=winSize,
                                                      estimateLearningRate = sitk.ImageRegistrationMethod.EachIteration,
                                                      maximumStepSizeInPhysicalUnits = maxStep)
    registration_method.SetOptimizerScalesFromPhysicalShift()

    # If corresponding points in the fixed and moving image are given then we display the similarity metric
    # and the TRE during the registration.
    registration_method.AddCommand(sitk.sitkIterationEvent, updateDisplay)

    final_transform = registration_method.Execute(fixed_image, moving_image)

    print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
    print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))
    showFinal()

    transforms.append(final_transform)


##########################################################################
########################## other demons registrations ##########################
##########################################################################

def smooth_and_resample(image, shrink_factor, smoothing_sigma):
    smoothed_image = sitk.SmoothingRecursiveGaussian(image, smoothing_sigma)

    original_spacing = image.GetSpacing()
    original_size = image.GetSize()
    new_size = [int(sz / float(shrink_factor) + 0.5) for sz in original_size]
    new_spacing = [((original_sz - 1) * original_spc) / (new_sz - 1)
                   for original_sz, original_spc, new_sz in zip(original_size, original_spacing, new_size)]
    return sitk.Resample(smoothed_image, new_size, sitk.Transform(),
                         sitk.sitkLinear, image.GetOrigin(),
                         new_spacing, image.GetDirection(), 0.0,
                         image.GetPixelIDValue())

def multiscale_demons(registration_algorithm,
                      fixed_image, moving_image, initial_transform=None,
                      shrink_factors=None, smoothing_sigmas=None):

    fixed_images = [fixed_image]
    moving_images = [moving_image]
    if shrink_factors:
        for shrink_factor, smoothing_sigma in reversed(list(zip(shrink_factors, smoothing_sigmas))):
            fixed_images.append(smooth_and_resample(fixed_images[0], shrink_factor, smoothing_sigma))
            moving_images.append(smooth_and_resample(moving_images[0], shrink_factor, smoothing_sigma))

    # Create initial displacement field at lowest resolution.
    # Currently, the pixel type is required to be sitkVectorFloat64 because of a constraint imposed by the Demons filters.
    if initial_transform:
        initial_displacement_field = sitk.TransformToDisplacementField(initial_transform,
                                                                       sitk.sitkVectorFloat64,
                                                                       fixed_images[-1].GetSize(),
                                                                       fixed_images[-1].GetOrigin(),
                                                                       fixed_images[-1].GetSpacing(),
                                                                       fixed_images[-1].GetDirection())
    else:
        initial_displacement_field = sitk.Image(fixed_images[-1].GetWidth(),
                                                fixed_images[-1].GetHeight(),
                                                fixed_images[-1].GetDepth(),
                                                sitk.sitkVectorFloat64)
        initial_displacement_field.CopyInformation(fixed_images[-1])

    # Run the registration.
    initial_displacement_field = registration_algorithm.Execute(fixed_images[-1],
                                                                moving_images[-1],
                                                                initial_displacement_field)
    # Start at the top of the pyramid and work our way down.
    for f_image, m_image in reversed(list(zip(fixed_images[0:-1], moving_images[0:-1]))):
        initial_displacement_field = sitk.Resample(initial_displacement_field, f_image)
        initial_displacement_field = registration_algorithm.Execute(f_image, m_image, initial_displacement_field)
    return sitk.DisplacementFieldTransform(initial_displacement_field)

########### This is the code for the demons multiscale
# Define a simple callback which allows us to monitor the Demons filter's progress.
transforms = []
for i in range(self.vtkView.nt):
    data1 = self.rawData[0]
    data2 = self.rawData[i]
    # self.vtkView.assignData([data1])
    self.vtkView2.assignData([data2])

    fixed_image = sitk.GetImageFromArray(data1.astype(np.double))
    moving_image = sitk.GetImageFromArray(data2.astype(np.double))
    registered_data = data2
    # Select a Demons filter and configure it.
    # demons_filter =  sitk.DemonsRegistrationFilter()
    demons_filter =  sitk.DiffeomorphicDemonsRegistrationFilter()
    # demons_filter =  sitk.FastSymmetricForcesDemonsRegistrationFilter()
    # demons_filter =  sitk.SymmetricForcesDemonsRegistrationFilter()

    demons_filter.SetNumberOfIterations(niter)
    # Regularization (update field - viscous, total field - elastic).
    demons_filter.SetSmoothDisplacementField(True)
    demons_filter.SetStandardDeviations(0.1)
    # demons_filter.SetUpdateFieldStandardDeviations(0.1)
    demons_filter.SetIntensityDifferenceThreshold(0.01)

    # Add our simple callback to the registration filter.
    demons_filter.AddCommand(sitk.sitkIterationEvent, lambda: updateDisplayDemons(demons_filter))
    final_transform = multiscale_demons(registration_algorithm=demons_filter, fixed_image=fixed_image, moving_image=moving_image,
                             shrink_factors=[8,4,2], smoothing_sigmas=[4,2,1])

    print('Final metric value: {0}'.format(demons_filter.GetMetric()))
    showFinal()

    transforms.append(final_transform)


# Now displays all the registered data in vtkView2

registered_data = []

for i in range(len(self.rawData)):
    data1 = self.rawData[0]
    data2 = self.rawData[i]

    fixed_image = sitk.GetImageFromArray(data1.astype(np.double))
    moving_image = sitk.GetImageFromArray(data2.astype(np.double))
    ri = sitk.Resample(moving_image, fixed_image, transforms[i], sitk.sitkLinear, 0.0,
                                     moving_image.GetPixelIDValue())
    registered_data.append(sitk.GetArrayFromImage(ri).astype(np.uint8))

self.vtkView.assignData(self.rawData)
self.vtkView2.assignData(registered_data)
