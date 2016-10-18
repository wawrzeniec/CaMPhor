## Free-form deformation
## https://github.com/InsightSoftwareConsortium/SimpleITK-Notebooks/blob/master/65_Registration_FFD.ipynb

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
lsmfile = basefolder + file

idxSlice = 25

with tifffile.TiffFile(lsmfile) as data:
    d = data.asarray()

lx = d.shape[2]
ly = d.shape[3]
lz = d.shape[4]
lt = d.shape[1]

# d2 = numpy.empty((lx*ly*lz),dtype=numpy.uint8,order="C")
# i = 0
# for y in range(ly):
#     for x in range(lx):
#         for z in range(lz):
#             d2[i] = d[0,0,x,y,z]
#             i += 1

# d2.reshape(lz,ly,lx)

img = sitk.GetImageFromArray(d[0,0,:,:,:].astype(numpy.double))
img2 = sitk.GetImageFromArray(d[0,1,:,:,:].astype(numpy.double))

# sitk_show(sitk.Tile(img[:, :, idxSlice], img2[:, :, idxSlice], (2, 1, 0)))

imgT1Smooth = sitk.CurvatureFlow(image1=img,
                                      timeStep=0.125,
                                      numberOfIterations=5)

imgT2Smooth = sitk.CurvatureFlow(image1=img2,
                                      timeStep=0.125,
                                      numberOfIterations=5)

fpoints = ru.generate_random_pointset(img, 1000)
mpoints = ru.generate_random_pointset(img2, 1000)


def bspline_intra_modal_registration(fixed_image, moving_image, fixed_image_mask=None, fixed_points=None,
                                     moving_points=None):
    registration_method = sitk.ImageRegistrationMethod()

    # Determine the number of Bspline control points using the physical spacing we want for the control grid.
    grid_physical_spacing = [50.0, 50.0, 50.0]  # A control point every 50mm
    image_physical_size = [size * spacing for size, spacing in zip(fixed_image.GetSize(), fixed_image.GetSpacing())]
    mesh_size = [int(image_size / grid_spacing + 0.5) \
                 for image_size, grid_spacing in zip(image_physical_size, grid_physical_spacing)]

    initial_transform = sitk.BSplineTransformInitializer(image1=fixed_image,
                                                         transformDomainMeshSize=mesh_size, order=3)
    registration_method.SetInitialTransform(initial_transform)

    registration_method.SetMetricAsMeanSquares()
    # Settings for metric sampling, usage of a mask is optional. When given a mask the sample points will be
    # generated inside that region. Also, this implicitly speeds things up as the mask is smaller than the
    # whole image.
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(0.01)
    if fixed_image_mask:
        registration_method.SetMetricFixedMask(fixed_image_mask)

    # Multi-resolution framework.
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    registration_method.SetInterpolator(sitk.sitkLinear)
    registration_method.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=100)

    # If corresponding points in the fixed and moving image are given then we display the similarity metric
    # and the TRE during the registration.
    if fixed_points and moving_points:
        registration_method.AddCommand(sitk.sitkStartEvent, rc.metric_and_reference_start_plot)
        registration_method.AddCommand(sitk.sitkEndEvent, rc.metric_and_reference_end_plot)
        registration_method.AddCommand(sitk.sitkIterationEvent,
                                       lambda: rc.metric_and_reference_plot_values(registration_method, fixed_points,
                                                                                   moving_points))

    return registration_method.Execute(fixed_image, moving_image)


############## Code for executing the registration
#%%timeit -r1 -n1

tx = bspline_intra_modal_registration(fixed_image = img,
                                      moving_image = img2,
                                      fixed_image_mask = None,
                                      fixed_points = fpoints,
                                      moving_points = mpoints
                                     )
initial_errors_mean, initial_errors_std, _, initial_errors_max, initial_errors = ru.registration_errors(sitk.Euler3DTransform(), fpoints, mpoints)
final_errors_mean, final_errors_std, _, final_errors_max, final_errors = ru.registration_errors(tx, fpoints, mpoints)

plt.hist(initial_errors, bins=20, alpha=0.5, label='before registration', color='blue')
plt.hist(final_errors, bins=20, alpha=0.5, label='after registration', color='green')
plt.legend()
plt.title('TRE histogram');
print('Initial alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(initial_errors_mean, initial_errors_std, initial_errors_max))
print('Final alignment errors in millimeters, mean(std): {:.2f}({:.2f}), max: {:.2f}'.format(final_errors_mean, final_errors_std, final_errors_max))

