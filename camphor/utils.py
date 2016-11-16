"""
CaMPhor utils module

This module contains a few function used in CaMPhor, packed in a module for convenience

"""

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4 import QtCore
import struct
import numpy


def readConfig(fileName):
    """
    utils.readConfig(fileName)

    Reads the specified config file and returns a dictionary with the values of the parameters in the file

    The file must be formatted as a simple list of KEY=VALUE pairs, separated by a newline
    Anything to the left of the first = sign is a KEY, and the rest is assigned to the VALUE
    VALUES are always returned as strings

    :return: A dictionary with the KEY-VALUE pairs foudn in the target file
    """

    with open(fileName,'r') as f:
        config = {}
        for line in f:
            if line[0] != '#':
                ieq = line.find('=')
                if ieq > -1:
                    icol = line[:ieq].find(':')
                    if icol > -1:
                        key = line[:icol]
                        dataType = line[icol+1:ieq]
                    else:
                        key = line[:ieq]
                        dataType='string'

                    value = line[ieq + 1:-1]
                    if dataType == 'int':
                        value = int(value)
                    elif dataType == float:
                        value = float(value)

                    config[key] = value

    return config


def overlayIcon(icon, text):
    """
    utils.overlayIcon(text)

    This function overlays text on the provided icon and returns a new QIcon object

    :param text: The text to be overlaid on the icon
    :return:

    """

    aSizes = icon.availableSizes()

    pix = []
    newIcon = QtGui.QIcon()
    for i, s in enumerate(aSizes):
        pix.append(icon.pixmap(s))
        painter = QtGui.QPainter(pix[i])
        painter.setCompositionMode(painter.CompositionMode_Overlay)
        fSize = s.height()/2
        font = QtGui.QFont("Arial", fSize, 75) # font weight 75 is bold
        painter.setFont(font)
        painter.setBrush(QtGui.QColor(0, 0, 0))
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(s.width()-fSize,s.height(),text)
        painter.end()
        newIcon.addPixmap(pix[i])

    return newIcon

def createTextIcon(text):
    """
    utils.createTextIcon(text)

    This function creates an icon with the specified text

    :param text: The text to be drawn on the icon
    :return:

    """

    aSizes = [QtCore.QSize(i,i) for i in (16,32,64)]

    pix = []
    newIcon = QtGui.QIcon()
    for i, s in enumerate(aSizes):
        pix.append(QtGui.QPixmap(s))
        pix[i].fill(QtGui.QColor(0,0,0,1))
        painter = QtGui.QPainter(pix[i])
        painter.setCompositionMode(painter.CompositionMode_DestinationOver)
        fSize = s.height()*0.9
        font = QtGui.QFont("Arial", fSize, 75) # font weight 75 is bold
        painter.setFont(font)
        painter.setBrush(QtGui.QColor(0, 0, 0))
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(0,0,s.width(),s.height(),Qt.AlignHCenter|Qt.AlignVCenter, text)
        painter.end()
        newIcon.addPixmap(pix[i])

    return newIcon

def LSMInfo(fileName):
    """
    utils.LSMInfo(fileName)
    Returns info about the specified LSM file
        - dimX
        - dimY
        - dimZ
        - dimC
        - dimT
        - voxXsize
        - voxYsize
        - voxZsize
        - specScan

    :param fileName: the name of the LSM file to be read for into
    :return: a dictionary with the fields specified above
    """

    with open(fileName, 'rb') as f:
        byteOrder = f.read(2).decode()
        if (byteOrder == 'II'):
            byteOrder = '<'
        elif (byteOrder=='MM'):
            byteOrder = '>'
        else:
            print('This is not a correct TIFF file (byte-order invalid)')
            return

        tiffID = struct.unpack('{:s}h'.format(byteOrder),f.read(2))[0]
        if tiffID != 42:
            print('This is not a correct TIFF file (tiffID not equal to 42)');
            return

        f.seek(4, 0)
        ifdPos = q = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        f.seek(ifdPos, 0)

        IFDIdx=0
        IFD = []
        while ifdPos != 0:
              f.seek(ifdPos, 0)
              numEntries = struct.unpack('{:s}H'.format(byteOrder),f.read(2))[0]
              entryPos = ifdPos+2
              f.seek(ifdPos+12*numEntries+2, 0)
              ifdPos = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]

              IFD.append(numpy.zeros([4,numEntries],dtype=numpy.uint32))
              for ii in range(numEntries):
                  f.seek(entryPos+12*ii, 0)
                  IFD[IFDIdx][0,ii] = struct.unpack('{:s}H'.format(byteOrder),f.read(2))[0]
                  IFD[IFDIdx][1,ii] = struct.unpack('{:s}H'.format(byteOrder),f.read(2))[0]
                  IFD[IFDIdx][2,ii] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
                  IFD[IFDIdx][3,ii] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]

              IFDIdx += 1

        # Reads the info
        info = {}

        if IFD[0][2,IFD[0][0,:]==258]==1:
                info['bitDepth'] = int(IFD[0][3,IFD[0][0,:]==258])
        else:
            f.seek(IFD[0][4,IFD[0][0,:]==258],0)
            info['bitDepth'] =  struct.unpack('{:s}H'.format(byteOrder),f.read(2))[0]

        offsetLSMinfo = int(IFD[0][3,IFD[0][0,:]==34412]+8)
        f.seek(offsetLSMinfo, 0)
        info['dimX'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        info['dimY'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        info['dimZ'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        info['dimC'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        info['dimT'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]
        f.seek(12, 1)
        info['voxSizeX'] = struct.unpack('{:s}d'.format(byteOrder),f.read(8))[0]
        info['voxSizeY'] = struct.unpack('{:s}d'.format(byteOrder),f.read(8))[0]
        info['voxSizeZ'] = struct.unpack('{:s}d'.format(byteOrder),f.read(8))[0]
        f.seek(26, 1)
        info['specScan'] = struct.unpack('{:s}I'.format(byteOrder),f.read(4))[0]

        return info

def VTKdisplay(data):
    """
    utils.VTKdisplay(data)

    display the specified data as a volume in a VTK window
    if the data is given as a list of numpy arrays, pressing the "s" key in the VTK window
    will play a "movie" displaying all the arrays in the list in order

    :param data: a numpy array, a list of numpy array, or a SimpleITK.Image
    :return: nothing

    """
    if (data.__class__ is sitk.SimpleITK.Image):
        data = sitk.GetArrayFromImage(data)

    if ((data.__class__ is list) and (data[0].__class__ is sitk.SimpleITK.Image)):
        data = [sitk.GetArrayFromImage(data[i]) for i in range(len(data))]

    if not (data.__class__ is list):
        data = [data]

    nt = len(data)

    for i in range(nt):
        data[i] = data[i][::-1, ::-1, ::-1].asdataType(numpy.uint8).transpose((0, 2, 1)).copy(order="C")

    importer = vtk.vtkImageImport()
    importer.SetDataScalarTypeToUnsignedChar()

    volumeMapper = vtk.vtkSmartVolumeMapper()

    opacityFunction = vtk.vtkPiecewiseFunction()
    opacityFunction.AddPoint(0, 0)
    opacityFunction.AddPoint(255, 0.1)

    # Create transfer mapping scalar value to color.
    colorFunction = vtk.vtkColorTransferFunction()
    colorFunction.SetColorSpaceToRGB()
    colorFunction.AddRGBPoint(0, 0.0, 0.0, 1.0)
    colorFunction.AddRGBPoint(128, 0.0, 1.0, 0.0)
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

    lz, ly, lx = data[0].shape  # The shape of the data (VTK is inverted wrt numpy)
    print("Data dimensions: {:d}, {:d}, {:d}".format(lx, ly, lz))

    # Sets the importer to import the first frame of the supplied data
    importer.SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
    importer.SetDataExtentToWholeExtent()
    importer.SetImportVoidPointer(data[0])

    # Connects the importer to the volume mapper and to the slicer
    volumeMapper.SetInputConnection(importer.GetOutputPort())

    volume.SetMapper(volumeMapper)
    volume.SetProperty(volumeProperty)
    renderer.AddVolume(volume)

    renderer.AddVolume(volume)

    window.Render()


    def runMovie(interactor, event):
        key = interactor.GetKeySym()
        print("key pressed: {:s}".format(key))
        if key == "s":
            for i in range(nt):
                importer.SetImportVoidPointer(data[i])
                # data[i].Modified()
                window.Render()
                time.sleep(0.05)

        volumeMapper.SetInputData(data[0])
        window.Render()

    interactor.AddObserver(vtk.vtkCommand.KeyPressEvent, runMovie)

    interactor.Start()

def applyReg(data, transform, reference):

    if not isinstance(data, list):
        data = [data]
        transform = [transform]

    nt = len(data)

    resample = sitk.ResampleImageFilter()
    resample.SetReferenceImage(reference)

    resample.SetInterpolator(sitk.sitkLinear)
    newdata = []

    for i in range(nt):
        resample.SetTransform(transform[i])
        newdata.append(resample.Execute(data[i]))

    newd = [sitk.GetArrayFromImage(newdata[i]) for i in range(nt)]

    # Re-arranges the data for the VTK display
    # for i in range(nt):
    #     newd[i] = newd[i][::-1, ::-1, ::-1].asdataType(numpy.uint8).transpose((0, 2, 1)).copy(order="C")

    return newd

def calculatedF(data, endframe=2):
    baseline = numpy.zeros(data[0].shape)

    for t in range(endframe):
        baseline += data[t]
    baseline /= endframe

    return [numpy.maximum(0, d - baseline).astype(numpy.uint8) for d in data]

