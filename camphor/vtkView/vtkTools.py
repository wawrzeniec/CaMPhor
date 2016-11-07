import vtk
import copy
import numpy

# The qualitative colormap for displaying multiple sets of VOIs together
# Would be best to have an algorithmic representation but the matplotlib color maps
# don't seem to give very good results
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

class camphorDisplayObject(object):
    """
        class vtkTools.camphorDisplayObject

        This is the base class for displaying objects in camphor

        The class contains vtk objects for displaying a volume and a slice from the input data

        The volume can be displayed by directly adding its 'volume' and 'sliceActor' properties to a VTK renderer,
        or by connecting its 'output' and 'sliceOutput' properties via the GetOutputPort() method for further processing.

        """

    def __init__(self):
        # Objects for volume rendering
        self.volume = vtk.vtkVolume()
        self.volumeMapper = vtk.vtkSmartVolumeMapper()
        self.volumeProperty = vtk.vtkVolumeProperty()

        # Objects for slice rendering
        self.sliceActor = vtk.vtkImageActor()
        self.sliceMapper = vtk.vtkImageResliceMapper()
        self.sliceProperty = vtk.vtkImageProperty()

        # Objects for importing and reslicing the data
        self.importer = [vtk.vtkImageImport()]
        self.slice = [vtk.vtkImageResliceToColors()]

        # Objects that point to the output algorithms
        # These must be specified at run time by the implementing class
        self.output = None
        self.sliceOutput = None

        # Some properties of the data
        self.numberOfDataSets = 0
        self.numberOfTimeFrames = 0
        self.currentTimeFrame = 0
        self.dimensions = [0, 0, 0]


class camphorStack(camphorDisplayObject):
    """
    class vtkTools.camphorStack

    This is the class for rendering a fluorescence time series in camphor

    The class contains methods to display both the raw fluorescence and the dF/F

    """
    def __init__(self):
        super(camphorStack, self).__init__()

        # data objects
        self.data = []          # reference to the data array
        self.tdata = []         # reference to the transformed data
        self.transforms = []    # reference to the set of transforms
        self.DFata = []         # reference to the DF/F data array
        self.tDFdata = []       # reference to the transformed DF/F data

        # Display mode: raw fluorescence or dF/F
        self.displayMode = 0

        # Colormaps for this object
        self.table = vtk.vtkLookupTable()
        self.DFtable = vtk.vtkLookupTable()
        self.sliceTable = vtk.vtkLookupTable()
        self.DFsliceTable = vtk.vtkLookupTable()

        self.numberOfTimeFrames = 0
        self.currentTimeFrame = None

    def setDisplayMode(self, mode):
        """
        camphorStack.setDisplayMode(mode)

        Sets the display mode to raw fluorescence (mode=0) or deltaF/F (mode=1)

        :param mode:    the requested display mode
        :return:        nothing
        """

        if mode==0:
            self.importer[0].SetImportVoidPointer(self.data[self.currentTimeFrame])
            self.image[0].SetLookupTable(self.table)
            self.slice[0].SetLookupTable(self.sliceTable)

        elif mode==1:
            self.importer[0].SetImportVoidPointer(self.DFdata[self.currentTimeFrame])
            self.image[0].SetLookupTable(self.DFtable)
            self.slice[0].SetLookupTable(self.DFsliceTable)

        self.importer[0].Modified()
        self.slice[0].Update()
        self.displayMode = mode

    def setDisplayModeToRaw(self):
        """
        camphorStack.setDisplayModeToRaw()

        Sets the display mode to raw fluorescence (mode 0)

        :return: nothing
        """
        self.setDisplayMode(0)

    def setDisplayModeToDF(self):
        """
        camphorStack.setDisplayModeToDF()

        Sets the display mode to deltaF/F (mode 1)

        :return: nothing
        """
        self.setDisplayMode(1)

    def setColorMap(self, colormap):
        """
        camphorStack.setColorMap(colormap)

        This function sets the colormap of the object to the requested colormap.

        :param colormap:    A string identifying the colormap. Possible values are:
                            'standard':     blue-white-red colormap that works well to display raw fluorescence data
                            'diff':         blue-white-red colormap with zero opacity in the middle range, useful to display the difference of two data sets
                            'magenta'   :   simple magenta colormap (used for overlay)
                            'green':        simple green colormap (used for overlay)

        :return:            nothing

        """
        colorMap = vtk.vtkColorTransferFunction()
        opacityMap = vtk.vtkPiecewiseFunction()
        sliceOpacityMap = vtk.vtkPiecewiseFunction()
        DFcolorMap = vtk.vtkColorTransferFunction()
        DFopacityMap = vtk.vtkPiecewiseFunction()
        DFsliceOpacityMap = vtk.vtkPiecewiseFunction()

        if str.lower(colormap) == 'standard':
            opacityMap.AddPoint(0, 0)
            opacityMap.AddPoint(255, 0.5)

            sliceOpacityMap.AddPoint(0, 0.25)
            sliceOpacityMap.AddPoint(8, 0.5)
            sliceOpacityMap.AddPoint(16, 1)
            sliceOpacityMap.AddPoint(255, 1)

            colorMap.SetColorSpaceToRGB()
            colorMap.AddRGBPoint(0, 0.0, 0.0, 1.0)
            colorMap.AddRGBPoint(128, 1, 1, 1)
            colorMap.AddRGBPoint(255, 1.0, 0.0, 0.0)

            DFcolorMap.SetColorSpaceToRGB()
            DFcolorMap.AddRGBPoint(0, 0.0, 0.0, 1.0)
            DFcolorMap.AddRGBPoint(80, 1, 1, 1)
            DFcolorMap.AddRGBPoint(160, 1.0, 0.0, 0.0)

            DFopacityMap.AddPoint(0, 0)
            DFopacityMap.AddPoint(160, 0.5)

            DFsliceOpacityMap.AddPoint(0, 0.25)
            DFsliceOpacityMap.AddPoint(8, 0.5)
            DFsliceOpacityMap.AddPoint(16, 1)
            DFsliceOpacityMap.AddPoint(255, 1)

        elif str.lower(colormap) == 'diff':
            opacityMap.AddPoint(0, 0.5)
            opacityMap.AddPoint(128, 0.0)
            opacityMap.AddPoint(255, 0.5)

            sliceOpacityMap.AddPoint(0, 1)
            sliceOpacityMap.AddPoint(112, 1)
            sliceOpacityMap.AddPoint(120, 0.5)
            sliceOpacityMap.AddPoint(128, 0.25)
            sliceOpacityMap.AddPoint(136, 0.5)
            sliceOpacityMap.AddPoint(142, 1)
            sliceOpacityMap.AddPoint(255, 1)

            colorMap.SetColorSpaceToRGB()
            colorMap.AddRGBPoint(0, 0.0, 0.0, 1.0)
            colorMap.AddRGBPoint(128, 0.1, 0.1, 0.1)
            colorMap.AddRGBPoint(255, 1.0, 0.0, 0.0)

            DFopacityMap.AddPoint(0, 0.5)
            DFopacityMap.AddPoint(128, 0.0)
            DFopacityMap.AddPoint(255, 0.5)

            DFsliceOpacityMap.AddPoint(0, 1)
            DFsliceOpacityMap.AddPoint(112, 1)
            DFsliceOpacityMap.AddPoint(120, 0.5)
            DFsliceOpacityMap.AddPoint(128, 0.25)
            DFsliceOpacityMap.AddPoint(136, 0.5)
            DFsliceOpacityMap.AddPoint(142, 1)
            DFsliceOpacityMap.AddPoint(255, 1)

            DFcolorMap.SetColorSpaceToRGB()
            DFcolorMap.AddRGBPoint(0, 0.0, 0.0, 1.0)
            DFcolorMap.AddRGBPoint(128, 0.1, 0.1, 0.1)
            DFcolorMap.AddRGBPoint(255, 1.0, 0.0, 0.0)

        elif str.lower(colormap) == 'magenta':
            opacityMap.AddPoint(0, 0)
            opacityMap.AddPoint(255, 0.25)

            sliceOpacityMap.AddPoint(0, 0.25)
            sliceOpacityMap.AddPoint(8, 0.5)
            sliceOpacityMap.AddPoint(16, 1)
            sliceOpacityMap.AddPoint(255, 1)

            colorMap.SetColorSpaceToRGB()
            colorMap.AddRGBPoint(0, 1.0, 0.0, 1.0)
            colorMap.AddRGBPoint(255, 1.0, 0.0, 1.0)

            DFcolorMap.SetColorSpaceToRGB()
            DFcolorMap.AddRGBPoint(0, 1.0, 0.0, 1.0)
            DFcolorMap.AddRGBPoint(255, 1.0, 0.0, 1.0)

            DFopacityMap.AddPoint(0, 0)
            DFopacityMap.AddPoint(160, 0.25)

            DFsliceOpacityMap.AddPoint(0, 0.25)
            DFsliceOpacityMap.AddPoint(8, 0.5)
            DFsliceOpacityMap.AddPoint(16, 1)
            DFsliceOpacityMap.AddPoint(255, 1)

        elif str.lower(colormap) == 'green':
            opacityMap.AddPoint(0, 0)
            opacityMap.AddPoint(255, 0.25)

            sliceOpacityMap.AddPoint(0, 0.25)
            sliceOpacityMap.AddPoint(8, 0.5)
            sliceOpacityMap.AddPoint(16, 1)
            sliceOpacityMap.AddPoint(255, 1)

            colorMap.SetColorSpaceToRGB()
            colorMap.AddRGBPoint(0, 0.0, 1.0, 0.0)
            colorMap.AddRGBPoint(255, 0.0, 1.0, 0.0)

            DFcolorMap.SetColorSpaceToRGB()
            DFcolorMap.AddRGBPoint(0, 0.0, 1.0, 0.0)
            DFcolorMap.AddRGBPoint(255, 0.0, 1.0, 0.0)

            DFopacityMap.AddPoint(0, 0)
            DFopacityMap.AddPoint(160, 0.25)

            DFsliceOpacityMap.AddPoint(0, 0.25)
            DFsliceOpacityMap.AddPoint(8, 0.5)
            DFsliceOpacityMap.AddPoint(16, 1)
            DFsliceOpacityMap.AddPoint(255, 1)

        for i in range(256):
            self.table.SetTableValue(i, list(colorMap.GetColor(i)) + [opacityMap.GetValue(i)])
            self.sliceTable.SetTableValue(i, list(colorMap.GetColor(i)) + [sliceOpacityMap.GetValue(i)])
            self.DFtable.SetTableValue(i, list(DFcolorMap.GetColor(i)) + [DFopacityMap.GetValue(i)])
            self.DFsliceTable.SetTableValue(i, list(DFcolorMap.GetColor(i)) + [DFsliceOpacityMap.GetValue(i)])

    def setTimeFrame(self, t):
        """
        camphorStack.SetTimeFrame(t)

        sets the current time frame to the requested value

        :param t: integer specifying the requested time frame
        :return: true on success, false on error
        """

        if t > self.numberOfTimeFrames:
            if self.displayMode==0:
                self.importer[0].SetImportVoidPointer(self.data[-1])
            elif self.displayMode==1:
                self.importer[0].SetImportVoidPointer(self.DFdata[-1])
            self.importer[0].Modified()
            self.currentTimeFrame = self.numberOfTimeFrames
            return False
        else:
            if self.displayMode==0:
                self.importer[0].SetImportVoidPointer(self.data[t])
            elif self.displayMode==1:
                self.importer[0].SetImportVoidPointer(self.DFdata[t])
            self.importer[0].Modified()
            self.currentTimeFrame = t
            return True

    def calculateDF(self, baseline_endframe):
        """
        camphorStack.calculateDF()

        calculates the delta F/F data

        :return: nothing
        """

        baseline = numpy.zeros(self.tdata[0].shape)
        tbaseline = numpy.zeros(self.tdata[0].shape)

        for t in range(baseline_endframe):
            baseline += self.data[t]
            tbaseline += self.tdata[t]
        baseline /= baseline_endframe
        tbaseline /= baseline_endframe

        self.DFdata = [numpy.maximum(0, self.data[t] - baseline).astype(numpy.uint8) for t in
                       range(self.numberOfTimeFrames)]
        self.tDFdata = [numpy.maximum(0, self.tdata[t] - baseline).astype(numpy.uint8) for t in
                       range(self.numberOfTimeFrames)]

class camphorBlendedStacks(camphorDisplayObject):
    """
    vtkTools.camphorBlendedStacks

    This class is for blending two stacks together

    """


    def __init__(self):
        super(camphorBlendedStacks, self).__init__()

        self.blender = vtk.vtkImageBlend()
        self.sliceBlender = vtk.vtkImageBlend()

        self.output = self.blender
        self.sliceOutput = self.sliceBlender

        self.stack = [camphorStack() for i in range(2)]

        # Display mode: raw fluorescence or dF/F
        self.displayMode = 0

        self.numberOfTimeFrames = 0
        self.currentTimeFrame = None

    def setTimeFrame(self, t):
        """
        camphorBlendedStacks.SetTimeFrame(t)

        Sets the time frame of the blended stack to the specified time frame
        """
        for s in self.stack:
            s.setTimeFrame(t)

    def setColorMap(self, colormap):
        """
        camphorBlendedStacks.setColorMap(colormap)

        This function sets the colormap of the object to the requested colormap.

        :param colormap:    A string identifying the colormap. Possible values are:
                            'overlay': magenta-green colormap

        :return:            nothing

        """

        if colormap=='overlay':
            self.stack[0].setColorMap(colormap='magenta')
            self.stack[1].setColorMap(colormap='green')
        else:
            self.stack[0].setColorMap(colormap='magenta')
            self.stack[1].setColorMap(colormap='green')


    def setDisplayMode(self, mode):
        """
        camphorBlendedStacks.setDisplayMode(mode)

        Sets the display mode to raw fluorescence (mode=0) or deltaF/F (mode=1)

        :param mode:    the requested display mode
        :return:        nothing
        """

        for s in self.stack:
            s.setDisplayMode(mode)

        self.displayMode = mode


    def setDisplayModeToRaw(self):
        """
        camphorStack.setDisplayModeToRaw()

        Sets the display mode to raw fluorescence (mode 0)

        :return: nothing
        """
        self.setDisplayMode(0)


    def setDisplayModeToDF(self):
        """
        camphorStack.setDisplayModeToDF()

        Sets the display mode to deltaF/F (mode 1)

        :return: nothing
        """
        self.setDisplayMode(1)


class camphorBlendedStackVOI(camphorDisplayObject):
    """
    vtkTools.camphorBlendedStackVOI

    This class is for displaying VOIs on top of a stack
    """

    def __init__(self):
        super(camphorBlendedStackVOI, self).__init__()

        self.blender = vtk.vtkImageBlend()
        self.sliceBlender = vtk.vtkImageBlend()

        self.output = self.blender
        self.sliceOutput = self.sliceBlender


class camphorBlendedVOIs(camphorDisplayObject):
    """
    class vtkTools.camphorBlendedVOIs

    This class is for displaying any number of sets of VOIs simultaneously

    """
    def __init__(self):
        super(camphorBlendedVOIs, self).__init__()

        # data objects
        self.data = []  # reference to the data array

        # Blenders
        self.blender = vtk.vtkImageBlend()
        self.sliceBlender = vtk.vtkImageBlend()

        # Other objects
        self.image = []
        self.append = vtk.vtkImageAppendComponents()
        self.luminance = vtk.vtkImageLuminance()

        # Output objects
        self.output = self.blender
        self.sliceOutput = self.append

class camphorVOIs(camphorDisplayObject):
    """
    class vtkTools.camphorVOIs

    This class is for displaying a single sets of VOIs

    """
    def __init__(self):
        super(camphorVOIs, self).__init__()

        # data objects
        self.data = []  # reference to the data array

        # Other objects
        self.image = [vtk.vtkImageMapToColors()]

        # Output objects
        self.output = self.image[0]
        self.sliceOutput = self.slice[0]

def makeVOIs(data):
    """
    vtkTools.makeVOIs(data)

    Creates a camphorVOIs object from the supplied VOI data

    :param data:    the VOI data (3D array)
    :return:        a camphorVOIs object that can be used to display the data
    """

    lz, ly, lx = data.shape  # The shape of the data (VTK is inverted wrt numpy)

    numberOfDataSets = 1

    cV = camphorVOIs()
    cV.data = data

    cV.importer = [vtk.vtkImageImport()]
    cV.image = [vtk.vtkImageMapToColors()]
    cV.slice = [vtk.vtkImageResliceToColors()]

    cV.importer[0].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
    cV.importer[0].SetDataExtentToWholeExtent()
    cV.importer[0].SetDataScalarTypeToUnsignedChar()
    cV.importer[0].SetImportVoidPointer(data)
    cV.importer[0].Modified()

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
    cV.slice[0].SetOutputDimensionality(2)
    cV.slice[0].SetInterpolationModeToLinear()
    cV.slice[0].SetResliceAxes(sagittal)
    cV.slice[0].SetInputConnection(cV.importer[0].GetOutputPort())
    cV.slice[0].SetLookupTable(table[0])

    # Sets the volume property's color and opacity maps
    cV.volumeProperty.IndependentComponentsOn()
    for i in range(3):
        cV.volumeProperty.SetColor(i, colorMaps[i])
        cV.volumeProperty.SetScalarOpacity(i, opacityMap)
    cV.volumeProperty.SetScalarOpacity(3, nullMap)

    # Creates color image from the VOI data
    cV.image[0].SetLookupTable(table[0])
    cV.image[0].SetInputConnection(cV.importer[0].GetOutputPort())

    # Connects the objects to their mapper
    cV.volumeMapper.SetInputConnection(cV.image[0].GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.slice[0].GetOutputPort())

    # Adjusts the properties of the slice
    cV.sliceProperty.SetColorLevel(20)
    cV.sliceProperty.SetColorWindow(20)
    cV.sliceProperty.SetInterpolationTypeToNearest()

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

    cV.numberOfDataSets = numberOfDataSets
    cV.numberOfTimeFrames = 1
    cV.dimensions = [lx, ly, lz]

    return cV

def makeStack(data, transforms = [], colormap='standard', baseline_endframe = 2):
    """
    vtkTools.makeVolume(data, transforms=[], colormap="standard")

    This function creates the VTK objects necessary to display data as a volume

    :param data:        list of 3D numpy arrays representing a volume time-series
    :param transforms:  (optional) list of transforms
    :param colormap:    a string identifying the colormap to be used ('standard', 'overlay', etc.)
                        The colormap can be adjusted later by calling the setColorMap() method of the returned
                        camphorStack object. Refer to this function for the list of available colormaps
    :param baseline_endframe:
                        Indicates the last frame number for the computation of the baseline response

    :return:            a camphorStack object from which the resulting data can be displayed


    """

    if not isinstance(data,list):
        data = [data]

    lz, ly, lx = data[0].shape

    cV = camphorStack()

    cV.numberOfTimeFrames = len(data)
    cV.currentTimeFrame = 0

    cV.data = copy.deepcopy(data)
    cV.tdata = data
    for t in transforms:
        if t.active:
            cV.tdata = t.apply(cV.tdata)

    if cV.numberOfTimeFrames > baseline_endframe:
        cV.calculateDF(baseline_endframe)

    cV.dimensions = [lx, ly, lz]

    cV.importer = [vtk.vtkImageImport()]
    cV.image = [vtk.vtkImageMapToColors()]
    cV.slice = [vtk.vtkImageResliceToColors()]

    # Sets up the importer
    cV.importer[0].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
    cV.importer[0].SetDataExtentToWholeExtent()

    dataType = data[0].dtype
    if dataType == numpy.uint8:
        cV.importer[0].SetDataScalarTypeToUnsignedChar()
    elif dataType == numpy.uint16:
        cV.importer[0].SetDataScalarTypeToUnsignedShort()
    elif dataType == numpy.int:
        cV.importer[0].SetDataScalarTypeToInt()
    elif dataType == numpy.float:
        cV.importer[0].SetDataScalarTypeToFloat()
    elif dataType == numpy.float:
        cV.importer[0].SetDataScalarTypeToDouble()

    cV.table.SetRange(0, 255)
    cV.sliceTable.SetRange(0, 255)
    cV.DFtable.SetRange(0, 255)
    cV.DFsliceTable.SetRange(0, 255)
    if colormap is None:
        colormap = 'standard'
    cV.setColorMap(colormap)
    cV.setDisplayModeToRaw()

    cV.image[0].SetInputConnection(cV.importer[0].GetOutputPort())

    # Initializes the slice
    sagittal = vtk.vtkMatrix4x4()
    sagittal.DeepCopy((0, 1, 0, 0,
                       0, 0, 1, 127.5,
                       1, 0, 0, 0,
                       0, 0, 0, 1))

    cV.slice[0].SetOutputDimensionality(2)
    cV.slice[0].SetInterpolationModeToLinear()
    cV.slice[0].SetResliceAxes(sagittal)
    cV.slice[0].SetInputConnection(cV.importer[0].GetOutputPort())

    cV.volumeMapper.SetInputConnection(cV.image[0].GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.slice[0].GetOutputPort())

    # Turns off independent components in order to render channels 1-4 as RGBA
    opacityMap = vtk.vtkPiecewiseFunction()
    opacityMap.AddPoint(0, 0)
    opacityMap.AddPoint(255, 1)

    cV.volumeProperty.IndependentComponentsOff()
    cV.volumeProperty.SetScalarOpacity(0, opacityMap)

    # Adjusts the properties of the slice
    cV.sliceProperty.SetInterpolationTypeToNearest()

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

    cV.numberOfDataSets = 1
    cV.currentTimeFrame = 0
    cV.dimensions = [lx, ly, lz]

    # the output
    cV.output = cV.image[0]
    cV.sliceOutput = cV.slice[0]

    return cV

def mergeVOIs(data):
    """
    vtkTools.mergeVOIs(data)

    This function takes a list of VOI arrays (0-1 binary as numpy.uint8)
    and merges them in a single vtkImageData

    The merge is achieved by using vtkImageMapToColors and vtkBlend

    The function also reslices the resulting volume by slicing each individual data set using
    vtkImageResliceToColors and merging them using vtkImageBlend in 2D

    :param data: a list of VOI data arrays, as uint8 and containing only 0 and 1's
    :return: a camphorBlendedVOIs object from which the resulting data can be displayed

    NOTE:   For some reason, blending images doesn't work as expected if the first image is RGBA
            For this reason, we have to set it to RGB, which renders the black color (absence of VOIs) opaque,
            because the output of the vtkImageBlend will have only 3 components. To get around this, we use
            vtkImageAppendComponent to append the alpha channel, which we take to be the image's luminance
            calculated with the vtk.vtkImageLuminance() filter.

    """

    lz, ly, lx = data[0].shape  # The shape of the data (VTK is inverted wrt numpy)
    
    numberOfDataSets = len(data)
    
    cV = camphorBlendedVOIs()
    cV.data = data

    cV.importer = [vtk.vtkImageImport() for i in range(numberOfDataSets)]
    cV.image = [vtk.vtkImageMapToColors() for i in range(numberOfDataSets)]
    cV.slice = [vtk.vtkImageResliceToColors() for i in range(numberOfDataSets)]

    for i in range(numberOfDataSets):
        cV.importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
        cV.importer[i].SetDataExtentToWholeExtent()
        cV.importer[i].SetDataScalarTypeToUnsignedChar()
        cV.importer[i].SetImportVoidPointer(data[i])
        cV.importer[i].Modified()

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
        cV.slice[i].SetOutputDimensionality(2)
        cV.slice[i].SetInterpolationModeToLinear()
        cV.slice[i].SetResliceAxes(sagittal)
    
    # Sets the volume property's color and opacity maps
    cV.volumeProperty.IndependentComponentsOn()
    for i in range(3):
        cV.volumeProperty.SetColor(i, colorMaps[i])
        cV.volumeProperty.SetScalarOpacity(i, opacityMap)
    cV.volumeProperty.SetScalarOpacity(3, nullMap)

    # Creates color image from the VOI data
    for i in range(numberOfDataSets):
        cV.image[i].SetLookupTable(table[i])
        cV.image[i].SetInputConnection(cV.importer[i].GetOutputPort())

    # Merges the image together
    cV.blender.RemoveAllInputConnections(0)
    cV.sliceBlender.RemoveAllInputConnections(0)
    cV.blender.SetBlendModeToNormal()
    cV.sliceBlender.SetBlendModeToNormal()

    for i in range(numberOfDataSets):
        cV.blender.AddInputConnection(cV.image[i].GetOutputPort())
        cV.slice[i].SetInputConnection(cV.importer[i].GetOutputPort())
        # For some reason, if the first input is RGBA then subsequent inputs become dimmer and dimmer
        if i == 0:
            cV.slice[i].SetOutputFormatToRGB()
        else:
            cV.slice[i].SetOutputFormatToRGBA()
        cV.slice[i].SetLookupTable(table[i])
        cV.sliceBlender.AddInputConnection(cV.slice[i].GetOutputPort())
        cV.blender.SetOpacity(i, 0.5)
        cV.sliceBlender.SetOpacity(i, 0.5)

    # Adds the alpha channel to the sliceBlender output
    cV.luminance.SetInputConnection(cV.sliceBlender.GetOutputPort())
    cV.append.AddInputConnection(cV.sliceBlender.GetOutputPort())
    cV.append.AddInputConnection(cV.luminance.GetOutputPort())

    # Connects the objects to their mapper
    cV.volumeMapper.SetInputConnection(cV.blender.GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.append.GetOutputPort())

    # Adjusts the properties of the slice
    cV.sliceProperty.SetColorLevel(20)
    cV.sliceProperty.SetColorWindow(20)
    cV.sliceProperty.SetInterpolationTypeToNearest()

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

    cV.numberOfDataSets = numberOfDataSets
    cV.numberOfTimeFrames = 1
    cV.dimensions = [lx, ly, lz]
    
    return cV

def overlayVOIsonStack(stack, VOI):
    """
    [deprecated - now we use camphorStack and camphorVOIs (or camphorBlendedVOIs) and display the two props in the same renderer,
    instead of blending them. This also allows to set interpolation type, opacity, etc easily for the two props]

    vtkTools.overlayVOIsonStack(stack, VOI)

    This function overlays a camphorVOIs (or camphorBlendedVOIs) object on top of a camphorStack object

    :param stack:   the stack object
    :param VOI:     the VOI object
    :return:        a camphorBlendedStackVOI object from which the data can be rendered
    """

    cV = camphorBlendedStackVOI()

    cV.stack = stack
    cV.VOI = VOI

    if isinstance(VOI.slice, list):
        cV.slice = [stack.slice] + VOI.slice
    else:
        cV.slice = [stack.slice] + [VOI.slice]

    # Merges the image together
    cV.blender.RemoveAllInputConnections(0)
    cV.sliceBlender.RemoveAllInputConnections(0)
    cV.blender.SetBlendModeToNormal()
    cV.sliceBlender.SetBlendModeToNormal()

    cV.blender.AddInputConnection(stack.output.GetOutputPort())
    cV.blender.AddInputConnection(VOI.output.GetOutputPort())
    cV.sliceBlender.AddInputConnection(stack.sliceOutput.GetOutputPort())
    cV.sliceBlender.AddInputConnection(VOI.sliceOutput.GetOutputPort())
    # for s in cV.slice:
    #     s.SetOutputFormatToRGBA()

    for i in range(len(cV.slice)):
        cV.blender.SetOpacity(i, 0.5)
        cV.sliceBlender.SetOpacity(i, 0.5)

    # Connects the objects to their mapper
    cV.volumeMapper.SetInputConnection(cV.blender.GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.sliceBlender.GetOutputPort())

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.sliceProperty.SetColorLevel(128)
    cV.sliceProperty.SetColorWindow(255)
    cV.sliceProperty.SetInterpolationTypeToNearest()
    #
    # sProp = VOI.sliceProperty
    # sProp.SetColorLevel(128)
    # sProp.SetColorWindow(255)
    # sProp.SetInterpolationTypeToNearest()

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

    return cV

def mergeStacks(stacks):
    """
    vtkTools.mergeStacks(stacks)

    This function merges two camphorStack objects together.
    It can in principle blend any number of stacks, but the colormaps are yet undefined for n>2
    It probably does not make much sense to try to blend more than 2 stacks

    :param stacks:  array of camphorStack objects
    :return:        a camphorBlendedStacks object, for which the internal methods of camphorStack objects are overloaded
    """

    cV = camphorBlendedStacks()

    cV.stack = stacks
    cV.setColorMap(colormap='overlay')
    cV.numberOfDataSets = len(stacks)

    cV.numberOfTimeFrames = stacks[0].numberOfTimeFrames
    cV.slice = stacks[0].slice
    for i in range(1,cV.numberOfDataSets):
        cV.numberOfTimeFrames = min(cV.numberOfTimeFrames, stacks[i].numberOfTimeFrames)
        cV.slice += stacks[i].slice

    cV.blender.RemoveAllInputConnections(0)
    cV.sliceBlender.RemoveAllInputConnections(0)

    for i in range(cV.numberOfDataSets):
        cV.blender.AddInputConnection(cV.stack[i].image[0].GetOutputPort())
        cV.sliceBlender.AddInputConnection(cV.stack[i].slice[0].GetOutputPort())
        cV.blender.SetOpacity(i, 0.5)
        cV.sliceBlender.SetOpacity(i, 0.5)


    # Connects the objects to their mapper
    cV.volumeMapper.SetInputConnection(cV.blender.GetOutputPort())
    cV.sliceMapper.SetInputConnection(cV.sliceBlender.GetOutputPort())

    opacityMap = vtk.vtkPiecewiseFunction()
    opacityMap.AddPoint(0, 0)
    opacityMap.AddPoint(255, 1)

    # Turns off independent components in order to render RGBA images
    cV.volumeProperty.IndependentComponentsOff()
    cV.volumeProperty.SetScalarOpacity(0, opacityMap)

    cV.volume.SetMapper(cV.volumeMapper)
    cV.sliceActor.SetMapper(cV.sliceMapper)

    cV.sliceProperty.SetColorLevel(128)
    cV.sliceProperty.SetColorWindow(255)
    cV.sliceProperty.SetInterpolationTypeToNearest()

    cV.volume.SetProperty(cV.volumeProperty)
    cV.sliceActor.SetProperty(cV.sliceProperty)

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
            elif numberOfDataSets == 3:
                # Three data sets --> RGB
                table[i].SetTableValue(j, [int(i==0), int(i==1), int(i==2), 1])
            else:
                # More than three --> qualitative colormap
                table[i].SetTableValue(j, [_VOImap[i][0], _VOImap[i][1], _VOImap[i][2], 1])

    return table