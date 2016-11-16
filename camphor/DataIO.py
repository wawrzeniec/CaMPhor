"""
CaMPhor_DataIO
Data I/O parent class for CaMPhor.
This class implements all functions for loading/saving data etc.
"""

import os
from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QApplication, QCursor
import tifffile
import vtk
import numpy
import pickle
import SimpleITK as sitk
import copy


def LSMLoad(target):
    """
    CaMPhor_DataIO.LSMLoad(target)

    Loads a .lsm file into memory
    The data is separated in one 3D array for each time step,
    and processed so that it can be displayed with vtkImageImport() without further processing

    :param target: name of the .lsm file to be loaded (absolute path)
    :return: loaded data as an list of 3-dimensional arrays, one for each time step

    """

    # 1. Loads the LSM file, using tifffile


    with tifffile.TiffFile(target) as data:
        d = data.asarray()
        imj = not (data.is_lsm)

    print(imj)
    print(d.shape)
    if(imj):
        # read the MB files from Keita
        if(len(d.shape) is 3):
            d2 = numpy.zeros((1,1,d.shape[0],d.shape[1],d.shape[2]),dtype=numpy.uint8)
            d2[0,0,:,:,:] = d
            d = numpy.transpose(d2,(0,1,4,3,2)).copy(order='C')
        elif(len(d.shape) is 5):
            d2 = numpy.zeros((1,d.shape[0],d.shape[1],d.shape[2],d.shape[3]))
            d2[0,:,:,:,:] = d[:,:,:,:,0] / 256
            d = numpy.transpose(d2, (0, 1, 4, 3, 2)).copy(order='C')
        elif (len(d.shape) is 4):
            d2 = numpy.zeros((1, d.shape[0], d.shape[1], d.shape[2], d.shape[3]))
            d2[0, :, :, :, :] = d
            d = numpy.transpose(d2, (0, 1, 4, 2, 3)).copy(order='C')
            # trick to fix inhomogeneity in size among files...
            # if d.shape[1] == 128:
            #     d = numpy.transpose(d2, (0, 1, 3, 4, 2)).copy(order='C')
            # else:
            #     d = numpy.transpose(d2, (0, 1, 2, 4, 3)).copy(order='C')
        else:
            print("Error: imageJ file with 4 dimensions - not implemented in dataIO.LMSLoad()")

    # Converts the data to uint8
    d = d.astype(numpy.uint8)

    lt = d.shape[1]

    # Separates the data into one array for each time point
    data = [d[0,i,:,:,:] for i in range(lt)]

    # Reverses the order of the data, and permutes the axes so that it is in the good format for VTK
    for i in range(lt):
        data[i] = data[i][::-1,::-1,::-1].transpose((0,2,1)).copy(order='C')

    lz,ly,lx = data[0].shape

    return data


def saveProject(fileName, camphor):
    if(fileName != '.'):
        project = camphor.project
        pd = QtGui.QProgressDialog(camphor)
        pd.setWindowTitle('Saving project ' + os.path.split(fileName)[1])
        pd.setModal(True)
        pd.show()

        np = serializeProject(project, progressDialog=pd)
        pd.setLabelText('Writing CPH file')
        with open(fileName, 'wb') as file:
            pickle.dump(np, file)
        pd.close()


def loadProject(fileName, camphor=None):
    if (fileName != '.'):
        if camphor is not None:
            pd = QtGui.QProgressDialog(camphor)
            pd.setWindowTitle('Loading project ' + os.path.split(fileName)[1])
            pd.setLabelText('Reading CPH file')
            pd.setModal(True)
            pd.show()
        else:
            pd = None

        with open(fileName, 'rb') as file:
            project = pickle.load(file)

        newProject = deserializeProject(project, progressDialog=pd)

        if pd is not None:
            pd.close()

        return newProject


def serializeProject(project, progressDialog=None):
    newProject = project.copy()

    # Calculates the total number of trials, to monitor progress
    nBrains = project.nBrains
    nTotal = 0
    for i in range(nBrains):
        nTotal += project.brain[i].nTrials
    nDone = 0

    for i in range(project.nBrains):
        tmp = serializeTransforms(project.brain[i].transforms)
        newProject.brain[i].transforms = tmp
        if project.brain[i].highResScan is not None:
            tmp = serializeTransforms(project.brain[i].highResScan.transforms)
            newProject.brain[i].highResScan.transforms = tmp
        for j in range(project.brain[i].nTrials):
            if progressDialog is not None:
                progressDialog.setLabelText('Serializing brain {:d}/trial {:d}'.format(i+1, j+1))
                progressDialog.setValue(nDone/nTotal*100)
            tmp = serializeTransforms(project.brain[i].trial[j].transforms)
            newProject.brain[i].trial[j].transforms = tmp
            nDone += 1
    return newProject

def serializeTransforms(transforms):
    newTransforms = []
    for it, t in enumerate(transforms):
        newTransforms.append(t.copy())
        if isinstance(t.transform, list):
            newTransform = []
            for im, m in enumerate(t.transform):
                if(isinstance(m,list)):
                    newTransform2 = []
                    for im2, m2 in enumerate(m):
                        sitk.WriteTransform(m2, 'tmp/tfmbuf.tfm')
                        with open('tmp/tfmbuf.tfm', 'r') as f:
                            newTransform2.append(f.read())
                    newTransform.append(newTransform2)
                else:
                    sitk.WriteTransform(m, 'tmp/tfmbuf.tfm')
                    with open('tmp/tfmbuf.tfm', 'r') as f:
                        newTransform.append(f.read())
            newTransforms[it].transform = newTransform
        else:
            sitk.WriteTransform(t.transform,'tmp/tfmbuf.tfm')
            with open('tmp/tfmbuf.tfm','r') as f:
                newTransforms[it].transform = f.read()
    return newTransforms

def deserializeProject(project, progressDialog=None):
    newProject = project.copy()

    # Calculates the total number of trials, to monitor progress
    nBrains = project.nBrains
    nTotal = 0
    for i in range(nBrains):
        nTotal += project.brain[i].nTrials
    nDone = 0

    for i in range(project.nBrains):
        newProject.brain[i].transforms = deserializeTransforms(project.brain[i].transforms)
        if hasattr(project.brain[i], 'highResScan'):
            if newProject.brain[i].highResScan is not None:
                newProject.brain[i].highResScan.transforms = deserializeTransforms(project.brain[i].highResScan.transforms)
        else:
            newProject.brain[i].highResScan = None
        for j in range(project.brain[i].nTrials):
            if progressDialog is not None:
                progressDialog.setLabelText('Deserializing brain {:d}/trial {:d}'.format(i+1, j+1))
                progressDialog.setValue(nDone/nTotal*100)
            newProject.brain[i].trial[j].transforms = deserializeTransforms(project.brain[i].trial[j].transforms)
            nDone += 1
    return newProject

def deserializeTransforms(transforms):
    newTransforms = []
    for it, t in enumerate(transforms):
        newTransforms.append(t.copy())
        if isinstance(t.transform, list):
            newTransform = []
            for im, m in enumerate(t.transform):
                if isinstance(m, list):
                    newTransform2 = []
                    for im2, m2 in enumerate(m):
                        with open('tmp/tfmbuf.tfm', 'w') as f:
                            f.write(m2)
                        newTransform2.append(sitk.ReadTransform('tmp/tfmbuf.tfm'))
                    newTransform.append(newTransform2)
                else:
                    with open('tmp/tfmbuf.tfm', 'w') as f:
                        f.write(m)
                    newTransform.append(sitk.ReadTransform('tmp/tfmbuf.tfm'))
            newTransforms[it].transform = newTransform
        else:
            with open('tmp/tfmbuf.tfm', 'w') as f:
                f.write(t.transform)
            newTransforms[it].transform = sitk.ReadTransform('tmp/tfmbuf.tfm')
    return newTransforms

def saveImageSeries(data, outputFile):
    s = data[0].shape
    nt = len(data)
    d = numpy.zeros([nt]+list(s))
    for i in range(nt):
        d[i,:,:,:] = data[i][::-1,::-1,::-1]
    tifffile.imsave(outputFile, numpy.transpose(d,[0,3,2,1]), metadata={'axes': 'TXYZ'})


def saveImageToVTI(data, outputFile):
    # Currently, saves only the first time point !

    imageData = vtk.vtkImageData()

    # Sets the vtkImageData object's dimensions to match the data
    lx,ly,lz = data[0].shape
    lt = len(data)
    imageData.SetDimensions(lx, ly, lz)

    # Allocates scalars of the UINT8 type (value=3)
    imageData.AllocateScalars(3, 1)

    writer = vtk.vtkXMLImageDataWriter()

    path, file = os.path.split(outputFile)
    if not os.path.exists(path):
        os.mkdir(path)

    # This function writes the data for one time step into the vtkImageData object,
    # and returns the vtkImageData object

    writer.SetFileName(outputFile)

    for z in range(lz):
        for y in range(ly):
            for x in range(lx):
                imageData.SetScalarComponentFromDouble(x, y, z, 0, data[0][x, y, z])

    # Writes the VTI files if requested
    writer.SetInputData(imageData)
    writer.Write()

def saveImageToMeta(data, outputFile):
    # Currently, saves only the first time point !

    imageData = vtk.vtkImageData()

    # Sets the vtkImageData object's dimensions to match the data
    lx,ly,lz = data[0].shape
    lt = len(data)
    imageData.SetDimensions(lx, ly, lz)

    # Allocates scalars of the UINT8 type (value=3)
    imageData.AllocateScalars(3, 1)

    writer = vtk.vtkMetaImageWriter()

    path, file = os.path.split(outputFile)
    if not os.path.exists(path):
        os.mkdir(path)

    # This function writes the data for one time step into the vtkImageData object,
    # and returns the vtkImageData object

    writer.SetFileName(outputFile)
    writer.SetRAWFileName(outputFile + '.raw')

    for z in range(lz):
        for y in range(ly):
            for x in range(lx):
                imageData.SetScalarComponentFromDouble(x, y, z, 0, data[0][x, y, z])

    # Writes the VTI files if requested
    writer.SetInputData(imageData)
    writer.Write()

def Output(text, dub):
    print(text)


