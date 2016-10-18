import SimpleITK as sitk
import tifffile
import matplotlib.pyplot as plt
import os
import numpy
import vtk
import registration_utilities as ru
import registration_callbacks as rc



def sitk_show(img, title=None, margin=0.05, dpi=40):
    nda = sitk.GetArrayFromImage(img)
    spacing = img.GetSpacing()
    figsize = (1 + margin) * nda.shape[0] / dpi, (1 + margin) * nda.shape[1] / dpi
    extent = (0, nda.shape[1] * spacing[1], nda.shape[0] * spacing[0], 0)
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([margin, margin, 1 - 2 * margin, 1 - 2 * margin])

    plt.set_cmap("gray")
    ax.imshow(nda, extent=extent, interpolation=None)

    if title:
        plt.title(title)

    plt.show()

basefolder = "C:/Users/Laurent.Geneva/Documents/Work/LHN/data/11-13-15/"
vtkfolder = "C:/Users/Laurent.Geneva/Documents/Work/LHN/data/11-13-15/VTK/"
file = "Image01.lsm"
scan = "scan256x160.lsm"
lsmfile = basefolder + file
scanfile = basefolder + scan

idxSlice = 25

with tifffile.TiffFile(lsmfile) as data:
    d = data.asarray()

with tifffile.TiffFile(scanfile) as data:
    dscan = data.asarray()

lx = d.shape[2]
ly = d.shape[3]
lz = d.shape[4]
lt = d.shape[1]
print("Data dimensions: {:d},{:d},{:d}".format(lx,ly,lz))
print("Scan dimensions: {:d},{:d},{:d}".format(dscan.shape[2],dscan.shape[3],dscan.shape[4]))

# d2 = numpy.empty((lx*ly*lz),dtype=numpy.uint8,order="C")
# i = 0
# for y in range(ly):
#     for x in range(lx):
#         for z in range(lz):
#             d2[i] = d[0,0,x,y,z]
#             i += 1

# d2.reshape(lz,ly,lx)

# removes the "background"
# d[d<64] = 0


img = [sitk.GetImageFromArray(d[0,i,:,:,:].astype(numpy.double)) for i in range(20)]
scanimg = sitk.GetImageFromArray(dscan[0,0,::-1,:,:].astype(numpy.double))
scanimg.SetSpacing([0.5,0.5,0.5])

# We must downsample the scan image to the same res as the others
imgdim = img[0].GetSize()
scandim = scanimg.GetSize()
print("Original image dimensions: ({:d},{:d},{:d})".format(scandim[0],scandim[1],scandim[2]))

resampled = sitk.Image(imgdim[0],imgdim[1],imgdim[2],img[0].GetPixelIDValue())
resampled.SetSpacing([1.0,1.0,1.0])
resampled.SetOrigin(scanimg.GetOrigin())
resampled.SetDirection(scanimg.GetDirection())

resampleddim = resampled.GetSize()
print("Resampled image dimensions: ({:d},{:d},{:d})".format(resampleddim[0],resampleddim[1],resampleddim[2]))

# Resample original image using identity transform and the BSpline interpolator.
resample = sitk.ResampleImageFilter()
resample.SetReferenceImage(resampled)
resample.SetInterpolator(sitk.sitkBSpline)
resample.SetTransform(sitk.Transform())
resampledscan = resample.Execute(scanimg)

resampleddim = resampledscan.GetSize()
print("Resampled image dimensions: ({:d},{:d},{:d})".format(resampleddim[0],resampleddim[1],resampleddim[2]))


# sitk_show(sitk.Tile(img[:, :, idxSlice], img2[:, :, idxSlice], (2, 1, 0)))

# imgT1Smooth = sitk.CurvatureFlow(image1=img,
#                                       timeStep=0.125,
#                                       numberOfIterations=5)
#
# imgT2Smooth = sitk.CurvatureFlow(image1=img2,
#                                       timeStep=0.125,
#                                       numberOfIterations=5)

pts = [ru.generate_random_pointset(img[i], 1000) for i in range(20)]

# sitk_show(sitk.Tile(imgT1Smooth[:, :, idxSlice], imgT2Smooth[:, :, idxSlice], (2, 1, 0)))


############ This is the registration part


def demons_registration(fixed_image, moving_image, fixed_points=None, moving_points=None):
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
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[8, 4, 0])

    registration_method.SetInterpolator(sitk.sitkLinear)
    # If you have time, run this code as is, otherwise switch to the gradient descent optimizer
    # registration_method.SetOptimizerAsConjugateGradientLineSearch(learningRate=1.0, numberOfIterations=20,
    #                                                               convergenceMinimumValue=1e-6,
    #                                                               convergenceWindowSize=10)
    registration_method.SetOptimizerAsGradientDescent(learningRate=1.0, numberOfIterations=20, convergenceMinimumValue=1e-6, convergenceWindowSize=10)
    registration_method.SetOptimizerScalesFromPhysicalShift()

    # If corresponding points in the fixed and moving image are given then we display the similarity metric
    # and the TRE during the registration.
    if fixed_points and moving_points:
        registration_method.AddCommand(sitk.sitkStartEvent, rc.metric_and_reference_start_plot)
        registration_method.AddCommand(sitk.sitkEndEvent, rc.metric_and_reference_end_plot)
        registration_method.AddCommand(sitk.sitkIterationEvent,
                                       lambda: rc.metric_and_reference_plot_values(registration_method, fixed_points,
                                                                                   moving_points))

    return registration_method.Execute(fixed_image, moving_image)


def smooth_and_resample(image, shrink_factor, smoothing_sigma):
    """
    Args:
        image: The image we want to resample.
        shrink_factor: A number greater than one, such that the new image's size is original_size/shrink_factor.
        smoothing_sigma: Sigma for Gaussian smoothing, this is in physical (image spacing) units, not pixels.
    Return:
        Image which is a result of smoothing the input and then resampling it using the given sigma and shrink factor.
    """
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
    """
    Run the given registration algorithm in a multiscale fashion. The original scale should not be given as input as the
    original images are implicitly incorporated as the base of the pyramid.
    Args:
        registration_algorithm: Any registration algorithm that has an Execute(fixed_image, moving_image, displacement_field_image)
                                method.
        fixed_image: Resulting transformation maps points from this image's spatial domain to the moving image spatial domain.
        moving_image: Resulting transformation maps points from the fixed_image's spatial domain to this image's spatial domain.
        initial_transform: Any SimpleITK transform, used to initialize the displacement field.
        shrink_factors: Shrink factors relative to the original image's size.
        smoothing_sigmas: Amount of smoothing which is done prior to resmapling the image using the given shrink factor. These
                          are in physical (image spacing) units.
    Returns:
        SimpleITK.DisplacementFieldTransform
    """
    # Create image pyramid.
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
def iteration_callback(filter):
    print('\r{0}: {1:.2f}'.format(filter.GetElapsedIterations(), filter.GetMetric()), end='')

# Select a Demons filter and configure it.
# demons_filter =  sitk.DemonsRegistrationFilter()
# demons_filter =  sitk.DiffeomorphicDemonsRegistrationFilter()
# demons_filter =  sitk.FastSymmetricForcesDemonsRegistrationFilter()
demons_filter =  sitk.SymmetricForcesDemonsRegistrationFilter()

demons_filter.SetNumberOfIterations(100)
# Regularization (update field - viscous, total field - elastic).
demons_filter.SetSmoothDisplacementField(True)
demons_filter.SetStandardDeviations(1.0)
demons_filter.SetIntensityDifferenceThreshold(10)

# Add our simple callback to the registration filter.
demons_filter.AddCommand(sitk.sitkIterationEvent, lambda: iteration_callback(demons_filter))
# tx = [multiscale_demons(registration_algorithm=demons_filter, fixed_image=resampledscan, moving_image=img[i],
#                         shrink_factors=[4, 2], smoothing_sigmas=[8, 4]) for i in range(20)]


# rigid tranform
registration_method = sitk.ImageRegistrationMethod()
# registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
# registration_method.SetMetricAsANTSNeighborhoodCorrelation(10)
registration_method.SetMetricAsCorrelation()
    # SetMetricAsDemons(double intensityDifferenceThreshold=0.001)
    # SetMetricAsJointHistogramMutualInformation(unsigned int numberOfHistogramBins=20, double varianceForJointPDFSmoothing=1.5)
    # SetMetricAsMeanSquares()

registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
registration_method.SetMetricSamplingPercentage(0.01)
registration_method.SetInterpolator(sitk.sitkLinear)
registration_method.SetOptimizerAsGradientDescent(learningRate=0.1, numberOfIterations=10,
                                                  convergenceMinimumValue=1e-6, convergenceWindowSize=10)
registration_method.SetOptimizerScalesFromPhysicalShift()
registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
registration_method.AddCommand(sitk.sitkIterationEvent, lambda: dispinf(registration_method))

def dispinf(filter):
    print('\r{0}: {1:.2f}'.format(registration_method.GetProgress(), filter.GetMetricValue()), end='')

def runreg(registration_method, fixed_image, moving_image):
    transform = sitk.CenteredTransformInitializer(fixed_image, moving_image, sitk.Euler3DTransform(),
                                  sitk.CenteredTransformInitializerFilter.MOMENTS) #GEOMETRY or MOMENTS
    registration_method.SetInitialTransform(transform)
    registration_method.Execute(fixed_image, moving_image)
    return transform

# resampledscan = img[0]
tx = [runreg(registration_method, resampledscan, img[i]) for i in range(20)]

# Compare the initial and final TREs.
# initial_errors_mean, initial_errors_std, _, initial_errors_max, initial_errors = ru.registration_errors(sitk.Euler3DTransform(), pts[0], pts[1])
# final_errors_mean, final_errors_std, _, final_errors_max, final_errors = ru.registration_errors(tx, pts[0], pts[1])
#
# plt.hist(initial_errors, bins=20, alpha=0.5, label='before registration', color='blue')
# plt.hist(final_errors, bins=20, alpha=0.5, label='after registration', color='green')
# plt.legend()
# plt.title('TRE histogram');
# print('\nInitial alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(initial_errors_mean, initial_errors_std, initial_errors_max))
# print('Final alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(final_errors_mean, final_errors_std, final_errors_max))


########### This is the code for the non-multiscale demons algorithm
#%%timeit -r1 -n1
# Uncomment the line above if you want to time the running of this cell.

# Select the fixed and moving images, valid entries are in [0,9]
if(0):
    fixed_image_index = 0
    moving_image_index = 7


    tx = demons_registration(fixed_image = img, moving_image = img2, fixed_points=fpts, moving_points=mpts)
    initial_errors_mean, initial_errors_std, _, initial_errors_max, initial_errors = ru.registration_errors(sitk.Euler3DTransform(), fpts, mpts)
    final_errors_mean, final_errors_std, _, final_errors_max, final_errors = ru.registration_errors(tx, fpts, mpts)

    plt.hist(initial_errors, bins=20, alpha=0.5, label='before registration', color='blue')
    plt.hist(final_errors, bins=20, alpha=0.5, label='after registration', color='green')
    plt.legend()
    plt.title('TRE histogram');
    print('Initial alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(initial_errors_mean, initial_errors_std, initial_errors_max))
    print('Final alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(final_errors_mean, final_errors_std, final_errors_max))

############ This is the VTK part
# class getData:
#     def load(i):
#         if i == 0:
#             filename = "C:/Users/Laurent.Geneva/Documents/Work/LHN/data/11-13-15/.vtk/Image01.lsm.image." + str(i) + ".vti"
#         else:
#             filename = "C:/Users/Laurent.Geneva/Documents/Work/LHN/data/11-13-15/.vtk/Image01.lsm.image." + str(i) + ".vti"
#         reader = vtk.vtkXMLImageDataReader()
#         reader.SetFileName(filename)
#         reader.Update()
#         return (reader.GetOutput())
#
# data = [getData.load(i) for i in range(19)]
#
# print(data[0])


### Now we resample all the images onto the fixed image grid
resample = sitk.ResampleImageFilter()
resample.SetReferenceImage(resampledscan)

# SimpleITK supports several interpolation options, we go with the simplest that gives reasonable results.
resample.SetInterpolator(sitk.sitkLinear)
newimg = []
for i in range(20):
    resample.SetTransform(tx[i])
    newimg.append(resample.Execute(img[i]))

dataImporter = vtk.vtkImageImport()
dataImporter.SetDataScalarTypeToUnsignedChar()
dataImporter.SetNumberOfScalarComponents(1)
# d = d[0,:,::-1,::-1,::-1].transpose((0,1,3,2)).copy(order="C")
# lx = d.shape[3]
# ly = d.shape[2]
# lz = d.shape[1]
# dataImporter.SetImportVoidPointer(d[0,:,:,:])
# dataImporter.SetDataExtent(0, lx-1, 0, ly-1, 0, lz-1)
# dataImporter.SetWholeExtent(0, lx-1, 0, ly-1, 0, lz-1)

newd = [sitk.GetArrayFromImage(newimg[i]) for i in range(20)]
d = [sitk.GetArrayFromImage(img[i]) for i in range(20)]
r = sitk.GetArrayFromImage(resampledscan)

# # subtracts the background
# for i in range(19,0,-1):
#     newd[i] = (newd[i] - newd[0])/2 + 128
# newd[0] -= newd[0]
# print("min/max: {:f}/{:f}".format(numpy.min(newd[1]),numpy.max(newd[1])))

# Re-arranges the data for the VTK display
for i in range(20):
    newd[i] = newd[i][::-1, ::-1, ::-1].astype(numpy.uint8).transpose((0, 2, 1)).copy(order="C")
    d[i] = d[i][::-1, ::-1, ::-1].astype(numpy.uint8).transpose((0, 2, 1)).copy(order="C")
r = r[::-1, ::-1, ::-1].astype(numpy.uint8).transpose((0, 2, 1)).copy(order="C")

lx = newd[0].shape[2]
ly = newd[0].shape[1]
lz = newd[0].shape[0]
print("\n{:d},{:d},{:d}".format(lx,ly,lz))

# newd = d # visualize the original data instead

dataImporter.SetImportVoidPointer(newd[0])
dataImporter.SetDataExtent(0, lx-1, 0, ly-1, 0, lz-1)
dataImporter.SetWholeExtent(0, lx-1, 0, ly-1, 0, lz-1)

volumeMapper = vtk.vtkSmartVolumeMapper()
volumeMapper.SetInputConnection(dataImporter.GetOutputPort())
# volumeMapper.SetInputConnection(flip.GetOutputPort())
nt = 20


# Create transfer mapping scalar value to opacity.
opacityFunction = vtk.vtkPiecewiseFunction()
opacityFunction.AddPoint(0, 0)
opacityFunction.AddPoint(255, 0.25)

compositeOpacity = vtk.vtkPiecewiseFunction()
compositeOpacity.AddPoint(0.0,0.0)
compositeOpacity.AddPoint(80,0.1)
compositeOpacity.AddPoint(81,0.0)
compositeOpacity.AddPoint(255,0.25)

# Create transfer mapping scalar value to color.
colorFunction = vtk.vtkColorTransferFunction()
colorFunction.SetColorSpaceToRGB()
colorFunction.AddRGBPoint(0, 0.0, 0.0, 1.0)
colorFunction.AddRGBPoint(128, 1, 1, 1)
colorFunction.AddRGBPoint(255, 1.0, 0.0, 0.0)

# for bg-sutracted data
# colorFunction.AddRGBPoint(0, 0.0, 1.0, 0.0)
# colorFunction.AddRGBPoint(128, 0.0, 0.0, 1.0)
# colorFunction.AddRGBPoint(192, 1, 1, 1)
# colorFunction.AddRGBPoint(255, 1.0, 0.0, 0.0)

volumeProperty = vtk.vtkVolumeProperty()
volumeProperty.SetScalarOpacity(opacityFunction)
volumeProperty.SetColor(colorFunction)
volumeProperty.ShadeOff()

volume = vtk.vtkVolume()
volume.SetMapper(volumeMapper)
volume.SetProperty(volumeProperty)

# create a rendering window and renderer
renderer = vtk.vtkRenderer()
renderer.SetBackground(0, 0, 0)

window = vtk.vtkRenderWindow()
window.SetSize(512, 512)
window.AddRenderer(renderer)

interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(window)
interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
style = vtk.vtkInteractorStyleSwitch()
style.SetCurrentStyleToMultiTouchCamera()
tc = vtk.vtkInteractorStyleTrackballCamera()
tc.OnRightButtonDown = tc.OnMiddleButtonDown
tc.OnRightButtonUp = tc.OnMiddleButtonUp
tc.Pan()


renderer.AddVolume(volume)

window.Render()

def runMovie(interactor,event):
    key = interactor.GetKeySym()
    print("key pressed: {:s}".format(key))
    if key == "s":
        for i in range(nt):
            dataImporter.SetImportVoidPointer(newd[i])
            window.Render()

interactor.AddObserver(vtk.vtkCommand.KeyPressEvent, runMovie)


interactor.Start()


