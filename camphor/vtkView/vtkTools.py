import vtk

# The qualitative colormap for displaying multiple sets of VOIs together
_VOImap = [[0.50, 0.00, 0.00],
           [0.00, 0.50, 0.00],
           [0.00, 0.00, 0.50],
           [0.25, 0.25, 0.00],
           [0.00, 0.25, 0.25],
           [0.25, 0.00, 0.25],
           [0.35, 0.15, 0.00],
           [0.00, 0.35, 0.15],
           [0.00, 0.15, 0.35],
           [0.15, 0.35, 0.00],
           [0.00, 0.50, 0.00]]

class camphorBlendedVolume(object):
    def __init__(self):
        self.volume = vtk.vtkVolume()
        self.volumeMapper = vtk.vtkSmartVolumeMapper()
        self.volumeProperty = vtk.vtkVolumeProperty()

        self.sliceActor = vtk.vtkImageActor()
        self.sliceMapper = vtk.vtkImageResliceMapper()
        self.sliceProperty = vtk.vtkImageProperty()

        self.blender = vtk.vtkImageBlend()
        self.sliceBlender = vtk.vtkImageBlend()

        self.importer = []
        self.slice = []
        self.image = []
        
def mergeVOIs(data):
    """
    vtkTools.mergeVOIs(data)

    This function takes a list of VOI arrays (0-1 binary as numpy.uint8)
    and merges them in a single vtkImageData

    The merge is achieved by using vtkImageMapToColors and vtkBlend

    The function also reslices the resulting volume by slicing each individual data set using
    vtkImageResliceToColors and merging them using vtkImageBlend in 2D

    :param data: a list of VOI data arrays, as uint8 and containing only 0 and 1's
    :return: a camphorVolume object from which the resulting data can be displayed
    """

    lz, ly, lx = data[0].shape  # The shape of the data (VTK is inverted wrt numpy)
    
    numberOfDataSets = len(data)
    
    cV = camphorBlendedVolume()
    
    importer = [vtk.vtkImageImport() for i in range(numberOfDataSets)]
    image = [vtk.vtkImageMapToColors() for i in range(numberOfDataSets)]
    slice = [vtk.vtkImageResliceToColors() for i in range(numberOfDataSets)]

    for i in range(numberOfDataSets):
        importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
        importer[i].SetDataExtentToWholeExtent()
        importer[i].SetDataScalarTypeToUnsignedChar()
        importer[i].SetImportVoidPointer(data[i])
        importer[i].Modified()

    # Creates the colormap
    table = VOILookupTables(numberOfDataSets)

    # This map is for the RGB components - we render in independentComponents mode
    # so we assign each component a color transfer function and scalar opacity 
    opacityMap = vtk.vtkPiecewiseFunction()
    opacityMap.AddPoint(0, 0)
    opacityMap.AddPoint(1, 0.5)
    
    # This map is for the alpha component - we do not display it
    nullMap = vtk.vtkPiecewiseFunction()
    nullMap.AddPoint(0, 0)
    nullMap.AddPoint(1, 0)

    colorMaps = [vtk.vtkColorTransferFunction() for i in range(3)]
    for i in range(3):
        colorMaps[i].SetColorSpaceToRGB()
        colorMaps[i].AddRGBPoint(0, 0, 0, 0)
        colorMaps[i].AddRGBPoint(1, int(i == 0), int(i == 1), int(i == 2))

    # Matrix to initialize the slices reslice plane
    sagittal = vtk.vtkMatrix4x4()
    sagittal.DeepCopy((0, 1, 0, 0,
                       0, 0, 1, 127.5,
                       1, 0, 0, 0,
                       0, 0, 0, 1))

    # Initializes the slices
    for i in range(numberOfDataSets):
        slice[i].SetOutputDimensionality(2)
        slice[i].SetInterpolationModeToLinear()
        slice[i].SetResliceAxes(sagittal)
    
    # Sets the volume property's color and opacity maps
    cV.volumeProperty.IndependentComponentsOn()
    for i in range(3):
        cV.volumeProperty.SetColor(i, colorMaps[i])
        cV.volumeProperty.SetScalarOpacity(i, opacityMap)
    cV.volumeProperty.SetScalarOpacity(3, nullMap)

    # Creates color image from the VOI data
    for i in range(numberOfDataSets):
        image[i].SetLookupTable(table[i])
        image[i].SetInputConnection(importer[i].GetOutputPort())

    # Merges the image together
    cV.blender.RemoveAllInputConnections(0)
    cV.sliceBlender.RemoveAllInputConnections(0)
    cV.blender.SetBlendModeToNormal()
    cV.sliceBlender.SetBlendModeToNormal()

    for i in range(numberOfDataSets):
        cV.blender.AddInputConnection(image[i].GetOutputPort())
        slice[i].SetInputConnection(importer[i].GetOutputPort())
        # For some reason, if the first input is RGBA then subsequent inputs become dimmer and dimmer
        if i == 0:
            slice[i].SetOutputFormatToRGB()
        else:
            slice[i].SetOutputFormatToRGBA()
        slice[i].SetLookupTable(table[i])
        cV.sliceBlender.AddInputConnection(slice[i].GetOutputPort())
        cV.blender.SetOpacity(i, 0.5)
        cV.sliceBlender.SetOpacity(i, 0.5)
    
    # Connects the objects to their mapper
    cV.volumeMapper.SetInputConnection(cV.blender.GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.sliceBlender.GetOutputPort())

    # Adjusts the properties of the slice
    cV.sliceProperty.SetColorLevel(20)
    cV.sliceProperty.SetColorWindow(20)
    cV.sliceProperty.SetInterpolationTypeToNearest()

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

    cV.importer = importer
    cV.slice = slice
    cV.image = image
    
    return cV
    
def VOILookupTables(numberOfDataSets):
    """
    vtkTools.VOILookupTables(numberOfDataSets)

    This function returns an array of lookup tables for displaying VOIs
    The tables are designed so that data sets and their intersections can be
    easily visualized

    :param numberOfDataSets: the number of tables to be generated
    :return: a list of vtkLookupTable objects
    """

    table = [vtk.vtkLookupTable() for i in range(numberOfDataSets)]
    print("created vtk objects")

    for i in range(numberOfDataSets):
        table[i].SetValueRange(0, 255)
        table[i].SetRange(0, 255)
        table[i].SetAlphaRange(0, 255)
        table[i].SetNumberOfTableValues(256)
        table[i].Build()
        table[i].SetTableValue(0, [0, 0, 0, 0])

        for j in range(1, 256):
            if numberOfDataSets == 1:
                # One data set --> yellow
                table[i].SetTableValue(j, [1, 1, 0, 1])
            elif numberOfDataSets == 2:
                # Two data sets --> magenta and green
                table[i].SetTableValue(j, [int(i==0), int(i==1), int(i==0), 1])
            elif numberOfDataSets == 4:
                # Three data sets --> RGB
                table[i].SetTableValue(j, [int(i==0), int(i==1), int(i==2), 1])
            else:
                # More than three --> qualitative colormap
                table[i].SetTableValue(j, [_VOImap[i][0], _VOImap[i][1], _VOImap[i][2], 1])

    return table