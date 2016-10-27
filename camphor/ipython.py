import sys
import os
# Adds the path otherwise it doesn't work
sys.path.insert(0, "C:\\Users\\Laurent.Geneva\\PycharmProjects\\CaMPhor")
sys.path.append('C:\\Users\\Laurent.Geneva\\PycharmProjects\\CaMPhor\\camphor')
os.chdir('C:\\Users\\Laurent.Geneva\\PycharmProjects\\CaMPhor')

from camphor import camphorapp
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas # to turn interactive mode on (?)
from PyQt4 import QtGui

import numpy as np
import imp
import SimpleITK as sitk
import time
import vtk
import camphor.DataIO as DataIO
from matplotlib import cm
import numpy

app = QtGui.QApplication(sys.argv)
camphor = camphorapp.camphor()
self=camphor.vtkView

# to reload if any changes have been made
# imp.reload(camphor); del self



# Creates some data
# data1 = np.random.normal(20,0.001,[50,50,50]).astype(np.uint8)
# data2 = np.random.normal(20,0.001,[50,50,50]).astype(np.uint8)
# data1[10:20,10:20,10:20] = 128
# data2[15:25,15:25,15:25] = 200
#
# data1[30:40,30:40,30:40] = 128
# data2[35:45,35:45,35:45] = 200
#
# self.vtkView.assignData([data1])
# self.vtkView2.assignData([data2])

def generateCubeData(imageSize=50, nCubes=10, cubeSize=4, backgroundNoise=1, elasticNoise=1.0,positionNoise=1, intensityNoise=1, nSlices=10):
    # 1. Generate center positions for cubes, avoiding overlap as much as possible
    # imageSize can be either an int or a (1,3)-tuple

    maxnCubes = np.floor(np.prod(imageSize)/cubeSize**3/2)
    if(nCubes > maxnCubes):
        nCubes = maxnCubes
        print("generateCubeData::Warning::\nnCubes is too high, set to {:d}".format(nCubes))

    if(imageSize.__class__ == int):
        imageSize = tuple(imageSize for i in range(3))

    def genNextCenter(cubeCenter,n):
        maxIter = 1000

        nIter = 0
        while True:
            nIter += 1
            c = [np.random.uniform(low=cubeSize,high=imageSize[i]-cubeSize-1) for i in range(3)]
            d = [np.sqrt(np.sum((cubeCenter[i,:] - c)**2)) for i in range(n)]
            if np.max(d) > cubeSize:
                break
            if(nIter > maxIter):
                print("genNextCenter: maximum number of iterations exceeded. Aborting.")
                break
        return c

    # Generates cube centers
    cubeCenter = np.zeros((nCubes, 3))
    cubeCenter[0,:] = [np.random.uniform(low=cubeSize,high=imageSize[i]-cubeSize-1) for i in range(3)]
    for i in range(1,nCubes):
        cubeCenter[i,:] = genNextCenter(cubeCenter,i)

    cubeAmplitude = np.random.uniform(low=64,high=200,size=(nCubes,1)).astype(np.uint8)

    data = [np.maximum(0,np.random.normal(40, backgroundNoise, imageSize)).astype(np.uint8) for i in range(nSlices)]
    for t in range(nSlices):
        pNoise = np.random.normal(0, positionNoise, (3)).astype(np.int)
        for i in range(nCubes):
            #deformations
            pNoise += np.random.normal(0, elasticNoise, (3)).astype(np.int)
            data[t][int(np.floor(cubeCenter[i, 0] - pNoise[0] - cubeSize / 2)):int(np.floor(cubeCenter[i, 0] - pNoise[0] + cubeSize / 2)),
                    int(np.floor(cubeCenter[i, 1] - pNoise[1] - cubeSize / 2)):int(np.floor(cubeCenter[i, 1] - pNoise[1] + cubeSize / 2)),
                    int(np.floor(cubeCenter[i, 2] - pNoise[2] - cubeSize / 2)):int(np.floor(cubeCenter[i, 2] - pNoise[2] + cubeSize / 2))] = np.minimum(255,cubeAmplitude[i] + np.random.normal(0, intensityNoise))

    return data


data = generateCubeData(imageSize = (80,128,50), nSlices = 10, positionNoise = 0.5, nCubes = 50, backgroundNoise=5, intensityNoise=7.5, elasticNoise=0.5)
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
    if(not np.mod(iter,10)):
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
            time.sleep(0.1)


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

def showResult():
    # Displays all the registered data in vtkView2
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

##########################################################################
########################## rigid registration ###########################
##########################################################################

lRate = 2
niter = 300
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
    # registration_method.SetMetricAsCorrelation()
    registration_method.SetMetricAsANTSNeighborhoodCorrelation(5)
    # registration_method.SetMetricAsJointHistogramMutualInformation(numberOfHistogramBins=20,varianceForJointPDFSmoothing=1.5)
    # registration_method.SetMetricAsMeanSquares() # mean squares does not seem to work well at all

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

showResult()

##########################################################################
########################## demons registration ##########################
##########################################################################
# With cube data - generateCubeData(imageSize = (80,128,50), nSlices = 5, positionNoise = 0.5, nCubes = 50)
# I got extremely good results using: sigmaUpdate = 0.0, sigmaTotal = 0.5, diff=10, lRate=1, minconv=1e-6, niter=200, winSize=20, maxStep=1
#


lRate = 2
niter = 300
minconv = 1e-6
winSize = 20
maxStep = 1
sigmaUpdate = 0.0
sigmaTotal = 0.5
diff=10

transforms = []
for i in range(self.vtkView.nt):
    data1 = self.rawData[0]
    data2 = self.rawData[i]

    # Tries some kind of filtering to avoid losing the signals
    data1 = np.minimum(data1,64)
    data2 = np.minimum(data2, 64)

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
    initial_transform.SetSmoothingGaussianOnUpdate(varianceForUpdateField=sigmaUpdate, varianceForTotalField=sigmaTotal)

    registration_method.SetInitialTransform(initial_transform)

    registration_method.SetMetricAsDemons(diff)  # intensities are equal if the difference is less than 10HU

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

showResult()




################# SAVING THE TRANSFORMS ##################

## rigid


## demons
baseName = "DemonsReg_lRate={:.2f}_niter={:d}_minconv={:g}_winSize={:d}_maxStep={:g}_vars={:g}+{:g}_diff={:g}".format(lRate,niter,minconv,winSize,maxStep,sigmaUpdate,sigmaTotal,diff)
baseFolder = 'C:\\Users\\Laurent.Geneva\\Documents\\Work\\LHN\\data\\11-13-15\\.testregistration\\Image01.lsm'
for t in range(self.vtkView.nt):
    tf = "{:s}\\{:s}_tframe{:d}.tfm".format(baseFolder, baseName,t)
    transforms[t].WriteTransform(tf)
