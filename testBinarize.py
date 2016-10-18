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

fpts = ru.generate_random_pointset(img, 100)
mpts = ru.generate_random_pointset(img2, 100)

### VTK display part

dataImporter = vtk.vtkImageImport()
dataImporter.SetDataScalarTypeToUnsignedChar()
dataImporter.SetNumberOfScalarComponents(1)
d = d[0,:,::-1,::-1,::-1].transpose((0,1,3,2)).copy(order="C")
d[d>64] = 0

lx = d.shape[3]
ly = d.shape[2]
lz = d.shape[1]
dataImporter.SetImportVoidPointer(d[0,:,:,:])
dataImporter.SetDataExtent(0, lx-1, 0, ly-1, 0, lz-1)
dataImporter.SetWholeExtent(0, lx-1, 0, ly-1, 0, lz-1)
# print(dataImporter.GetOutput())

# flip = vtk.vtkImageFlip()
# flip.SetInputConnection(dataImporter.GetOutputPort())
# flip.SetFilteredAxis(1)

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
            dataImporter.SetImportVoidPointer(d[i, :, :, :])
            window.Render()

interactor.AddObserver(vtk.vtkCommand.KeyPressEvent, runMovie)


interactor.Start()


