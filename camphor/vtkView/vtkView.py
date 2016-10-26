from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
import vtk
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import time
from camphor import utils
import numpy
import copy
from matplotlib import cm

class vtkView(QtGui.QFrame):
    """
    class camphor.vtkView(QtGui.QFrame)

    This class implements the embedding of the VTK renderer into a QFrame
    To create a vtkView object into a QMainWindow widget ('self' below), use:

        # imports the class
        from camphor.vtkView import vtkView
        
        # Creates the vtkView object
        self.vtkView = vtkView.vtkView(self)

        # Puts the object inside a Qt layout
        self.mainWidget = QtGui.QWidget()
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.vtkView)
        self.mainWidget.setLayout(self.layout)
        self.setCentralWidget(self.mainWidget)

        # Starts the rendering
        self.vtkView.start()

    """

    def __init__(self, parent, ini, data = None):
        super(vtkView,self).__init__(parent)
        if data is None:
            self.data = [[]]
            self.nt = 0
            self.numberOfDataSets = 0
        else:
            self.data = [data]
            self.nt = len(self.data[0])
            self.numberOfDataSets = 1

        self.baseline = [None]
        self.currentdata = [[]]
        self.dFdata = [[]]
        self.camphor = parent

        self.colorMaps = {}
        self.opacityMaps = {}
        self.sliceColorMaps = {}
        self.sliceOpacityMaps = {}
        self.sliceLookupTables = {}

        self.VOIpanel = None

        self.ini = ini

        # Builds the colormaps
        self.makeColorMaps()
        self.colormap = 'Standard'

        # Setup VTK environment
        self.volume = None
        self.sliceVolume = None

        # Two VTK windows: one for the volume, and one for the slice view
        self.interactor = QVTKRenderWindowInteractor(self)
        self.sliceInteractor = QVTKRenderWindowInteractor(self)

        # Sliders to change the z- and t-positions
        self.zslider = QtGui.QSlider()
        self.zslider.setStyleSheet("""QSlider {background-color: none; width: 15px;}
                                   QSlider::handle {background: #36F; margin:2px 0;
                                        border: 1px solid #24F; border-radius: 2px;}
                                   QSlider::handle:hover {background-color: #24F;}""")
        self.tslider = QtGui.QSlider(Qt.Horizontal)
        self.tslider.setStyleSheet("""QSlider {background-color: none; height: 15px;}
                                    QSlider::handle {background-color: #36F; width:10px; height: 5px;
                                        border: 1px solid #24F; border-radius: 2px;}
                                   QSlider::handle:hover {background-color: #24F;}""")

        # Labels to indicate the current z- and t- positions
        self.zlabel = QtGui.QLabel()
        self.zlabel.setText("z:63")
        self.zlabel.setAlignment(Qt.AlignHCenter)
        self.zlabel.setStyleSheet("QLabel { background-color : none; color : #36F; font-size: 7pt; min-width:30px}")
        self.tlabel = QtGui.QLabel()
        self.tlabel.setText("t:0")
        self.tlabel.setStyleSheet("QLabel { background-color : none; color : #36F; font-size: 7pt; min-width:30px}")

        # Label to indicate the origin of the displayed data
        self.trialLabel = QtGui.QLabel()
        self.trialLabel.setText('[no trial loaded]')
        self.trialLabel.setStyleSheet("QLabel { background-color : none; color : #000; font-size: 7pt; min-width:100px}")
        self.trialLabel.setEnabled(False)

        # Buttons for play and loop
        self.playButton = QtGui.QToolButton()
        self.playButton.setStyleSheet("""
                                    QToolButton {width: 11px; height: 11px;
                                    image: url('res/icons/play_white.png');
                                    background-repeat: None;
                                    background-position: center;
                                    background-color: #36F;
                                    border: 1px solid #24F; border-radius: 2px;}

                                    QToolButton::hover {background: #CCC;}
                                    QToolButton::pressed {background: #ACF; border: 1px solid #ACF; border-radius: 2px;}
                                    """)
        self.repeatButton = QtGui.QToolButton()
        self.repeatButton.setCheckable(True)
        self.repeatButton.setStyleSheet("""
                                    QToolButton {width: 11px; height: 11px;
                                    image: url('res/icons/repeat_white.png');
                                    background-repeat: None;
                                    background-position: center;
                                    background-color: #36F;
                                    border: 1px solid #24F; border-radius: 2px;}

                                    QToolButton::hover {background: #CCC;}
                                    QToolButton::pressed {background: #ACF; border: 1px solid #ACF; }
                                    QToolButton::checked {background: #FCC; border: 1px solid #EAA; }
                                    """)
        self.playButton.pressed.connect(self.playMovie)
        self.playThread = playMovieThread()
        self.playThread.framedone.connect(self.playMovieUpdateGUI)

        # Layout for the sliders to add the buttons and labels
        self.zsliderLayout = QtGui.QVBoxLayout()
        self.zsliderLayout.addWidget(self.zlabel)
        self.zsliderLayout.addWidget(self.zslider, Qt.AlignRight)
        self.zsliderLayout.setAlignment(self.zslider, Qt.AlignHCenter)
        self.zsliderLayout.setAlignment(Qt.AlignCenter)

        self.tsliderLayout = QtGui.QHBoxLayout()
        self.tsliderLayout.addWidget(self.playButton)
        self.tsliderLayout.addWidget(self.repeatButton)
        self.tsliderLayout.addWidget(self.tlabel)
        self.tsliderLayout.addWidget(self.tslider)
        self.tsliderLayout.addWidget(self.trialLabel)

        # Layout for the VTK rendering windows to add a toolbar at the top
        self.renwinLayout = QtGui.QVBoxLayout()
        self.renwinToolbar = QtGui.QToolBar()
        self.renwinLayout.addWidget(self.renwinToolbar)
        self.renwinLayout.addWidget(self.interactor)

        self.slicerenwinLayout = QtGui.QVBoxLayout()
        self.slicerenwinToolbar = QtGui.QToolBar()
        self.slicerenwinLayout.addWidget(self.slicerenwinToolbar)
        self.slicerenwinLayout.addWidget(self.sliceInteractor)

        # Toolbar buttons/actions
        self.displayFAction = QtGui.QAction('Display Raw Fluorescence', self)
        self.displayFAction.setIcon(utils.createTextIcon(""))
        self.displayFAction.setCheckable(True)
        self.displayFAction.setChecked(True)
        self.displayFAction.setShortcut('Ctrl+F')
        self.displayFAction.setStatusTip('Display Raw Fluorescence')
        self.displayFAction.triggered.connect(self.displayF)
        self.renwinToolbar.addAction(self.displayFAction)

        self.displaydFAction = QtGui.QAction('Display dF/F Fluorescence', self)
        self.displaydFAction.setIcon(utils.createTextIcon(""))
        self.displaydFAction.setCheckable(True)
        self.displaydFAction.setChecked(False)
        self.displaydFAction.setShortcut('Ctrl+D')
        self.displaydFAction.setStatusTip('Display dF/F Fluorescence')
        self.displaydFAction.triggered.connect(self.displaydF)
        self.renwinToolbar.addAction(self.displaydFAction)

        c = self.renwinToolbar.children()
        self.displayFButton = c[3]
        self.displaydFButton = c[4]
        c[3].setObjectName('displayF')
        c[4].setObjectName('displaydF')

        self.renwinToolbar.setStyleSheet("""
                                            QToolButton {width: 10px; height: 10px;
                                            background-repeat: None;
                                            background-position: center;
                                            background-color: #6CF;
                                            border: 1px solid #24F; border-radius: 2px;}

                                            QToolButton#displayF {width: 10px; height: 10px;
                                            image: url('res/icons/F_white-01.png');}

                                            QToolButton#displaydF {width: 13px; height: 10px;
                                            image: url('res/icons/dF_white-01.png');}

                                            QToolButton::hover {background: #CCC;}
                                            QToolButton::pressed {background: #ACF; border: 1px solid #ACF; border-radius: 2px;}
                                            QToolButton#displayF::checked {image: url('res/icons/F_red-01.png');}
                                            QToolButton#displaydF::checked {image: url('res/icons/dF_red-01.png');}

                                            """)

        # Toolbar buttons/actions for plane view
        self.sliceXAction = QtGui.QAction('Slice along X-axis', self)
        self.sliceXAction.setIcon(utils.createTextIcon(""))
        self.sliceXAction.setCheckable(True)
        self.sliceXAction.setChecked(False)
        self.sliceXAction.setShortcut('Ctrl+X')
        self.sliceXAction.setStatusTip('Slice along X-axis')
        self.sliceXAction.triggered.connect(self.sliceX)
        self.slicerenwinToolbar.addAction(self.sliceXAction)

        self.sliceYAction = QtGui.QAction('Slice along Y-axis', self)
        self.sliceYAction.setIcon(utils.createTextIcon(""))
        self.sliceYAction.setCheckable(True)
        self.sliceYAction.setChecked(False)
        self.sliceYAction.setShortcut('Ctrl+Y')
        self.sliceYAction.setStatusTip('Slice along Y-axis')
        self.sliceYAction.triggered.connect(self.sliceY)
        self.slicerenwinToolbar.addAction(self.sliceYAction)

        self.sliceZAction = QtGui.QAction('Slice along Z-axis', self)
        self.sliceZAction.setIcon(utils.createTextIcon(""))
        self.sliceZAction.setCheckable(True)
        self.sliceZAction.setChecked(True)
        self.sliceZAction.setShortcut('Ctrl+Z')
        self.sliceZAction.setStatusTip('Slice along Z-axis')
        self.sliceZAction.triggered.connect(self.sliceZ)
        self.slicerenwinToolbar.addAction(self.sliceZAction)

        c = self.slicerenwinToolbar.children()
        self.sliceXButton = c[3]
        self.sliceYButton = c[4]
        self.sliceZButton = c[5]
        c[3].setObjectName('sliceX')
        c[4].setObjectName('sliceY')
        c[5].setObjectName('sliceZ')

        self.slicerenwinToolbar.setStyleSheet("""
                                                    QToolButton {width: 10px; height: 10px;
                                                    background-repeat: None;
                                                    background-position: center;
                                                    background-color: #6CF;
                                                    border: 1px solid #24F; border-radius: 2px;}

                                                    QToolButton#sliceX {width: 10px; height: 10px;
                                                    image: url('res/icons/X_white-01.png');}

                                                    QToolButton#sliceY {width: 10px; height: 10px;
                                                    image: url('res/icons/Y_white-01.png');}

                                                    QToolButton#sliceZ {width: 10px; height: 10px;
                                                    image: url('res/icons/Z_white-01.png');}

                                                    QToolButton::hover {background: #CCC;}
                                                    QToolButton::pressed {background: #ACF; border: 1px solid #ACF; border-radius: 2px;}
                                                    QToolButton#sliceX::checked {image: url('res/icons/X_red-01.png');}
                                                    QToolButton#sliceY::checked {image: url('res/icons/Y_red-01.png');}
                                                    QToolButton#sliceZ::checked {image: url('res/icons/Z_red-01.png');}

                                                    """)


        # The main grid layout
        self.layout = QtGui.QGridLayout()

        self.layout.addLayout(self.renwinLayout,0,0)
        self.layout.addLayout(self.zsliderLayout,0,1)
        self.layout.addLayout(self.slicerenwinLayout,0,2)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addLayout(self.tsliderLayout,1,0,1,3)
        self.setLayout(self.layout)

        # Adjusts slider properties
        self.zslider.setTickInterval(5)
        self.zslider.setPageStep(1)
        self.zslider.setMinimum(0)
        self.zslider.setMaximum(127)
        self.zslider.setValue(63)
        self.tslider.setTickInterval(1)
        self.tslider.setPageStep(1)
        self.tslider.setMinimum(0)
        self.tslider.setMaximum(19)
        self.tslider.setValue(0)
        self.zslider.setTickPosition(QtGui.QSlider.TicksRight)
        self.tslider.setTickPosition(QtGui.QSlider.TicksBelow)
        self.zslider.valueChanged.connect(self.setPlanePosition)
        self.tslider.valueChanged.connect(self.setTimeSlice)

        # Creates the VTK objects necessary for rendering
        self.renderer = vtk.vtkRenderer()
        self.sliceRenderer = vtk.vtkRenderer()
        self.renwin = self.interactor.GetRenderWindow()
        self.slicerenwin = self.sliceInteractor.GetRenderWindow()
        self.renwin.AddRenderer(self.renderer)
        self.slicerenwin.AddRenderer(self.sliceRenderer)
        self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.sliceInteractor.SetInteractorStyle(vtk.vtkInteractorStyleImage())
        self.interactor.AddObserver(vtk.vtkCommand.KeyPressEvent, self.runMovie)
        self.sliceInteractor.AddObserver(vtk.vtkCommand.KeyPressEvent, self.plotdF)
        self.renwin.SetInteractor(self.interactor)
        self.slicerenwin.SetInteractor(self.sliceInteractor)
        self.renderer.SetBackground(0.0,0.0,0.0)
        self.sliceRenderer.SetBackground(0.0, 0.0, 0.0)
        self.volumeMapper = vtk.vtkSmartVolumeMapper()

        # vtkImageImport to display data directly from a numpy array
        self.importer = [vtk.vtkImageImport() for i in range(2)]
        self.importer[0].SetDataScalarTypeToUnsignedChar()
        self.importer[1].SetDataScalarTypeToUnsignedChar()
        self.blender = vtk.vtkImageBlend() #AppendComponents()
        self.sliceBlender = vtk.vtkImageBlend()

        # Assigns color & opacity to the vtkVolumeProperty object which we will use for our volume rendering
        self.volumeProperty = vtk.vtkVolumeProperty()
        self.volumeProperty.SetScalarOpacity(self.opacityMaps['Standard'])
        self.volumeProperty.SetColor(self.colorMaps['Standard'])
        self.volumeProperty.ShadeOff()

        # Creates a plane to cut the volume into a slice
        # Also creates a cube to display the current slice in the volume window
        # (the plane itself is not very convenient because too thin)
        self.plane = vtk.vtkPlaneSource()
        self.cube = vtk.vtkCubeSource()
        self.plane.SetOrigin(-5,0,-5)
        self.plane.SetPoint1(-5,0,55)
        self.plane.SetPoint2(85,0,-5)
        self.planez = 63
        self.plane.Push(self.planez)
        self.cube.SetBounds(-5,85,62,63,-5,55)

        self.planeProp = vtk.vtkProperty()
        self.planeProp.SetColor(0.0,1.0,0.0)
        self.planeProp.SetOpacity(0.8)

        self.planeMapper = vtk.vtkPolyDataMapper()
        self.planeMapper.SetInputConnection(self.cube.GetOutputPort())
        self.planeActor = vtk.vtkActor()
        self.planeActor.SetMapper(self.planeMapper)
        self.planeActor.SetProperty(self.planeProp)

        self.renderer.AddActor(self.planeActor)

        # The vtkImageReslice object to do the actual volume cut
        # and display the result as 2D
        self.slice = [vtk.vtkImageResliceToColors() for i in range(2)]
        sagittal = vtk.vtkMatrix4x4()
        sagittal.DeepCopy((0, 1, 0, 0,
                           0, 0, 1, 125.5,
                           1, 0, 0, 0,
                           0, 0, 0, 1))
        for i in range(2):
            self.slice[i].SetLookupTable(self.sliceLookupTables['Standard'])
            self.slice[i].SetResliceAxes(sagittal)
            self.slice[i].SetOutputDimensionality(2)
            self.slice[i].SetInterpolationModeToLinear()
        self.curPlaneOrientation = 0

        self.sliceVolumeProperty = vtk.vtkVolumeProperty()
        self.sliceVolumeProperty.SetColor(self.sliceColorMaps['Standard'])
        self.sliceVolumeProperty.SetScalarOpacity(self.sliceOpacityMaps['Standard'])
        self.sliceVolumeProperty.ShadeOff()

        # VTK complains that this is deprecated, but idk what to use instead
        # self.sliceMapper = vtk.vtkVolumeTextureMapper2D()
        self.sliceMapper = vtk.vtkImageResliceMapper()

    def runMovie(self, interactor, event):
        """
        function vtkView.runMovie(self, interactor, event)

        [DEPRECATED - movie is now played using a separate thread, see vtkView.playMovie()]
        Callback for playing the time series as a movie in the VTK rendering window, in response to a key press or other event

        :param interactor:  the vtk interactor object (class QVTKRenderWindowInteractor)
        :param event:       events passed to the callback
        :return:            nothing

        """

        key = interactor.GetKeySym()
        print("key pressed: {:s}".format(key))
        if key == "s":
            for i in range(self.nt):
                self.tslider.setValue(i)
                self.tslider.repaint()

    def playMovie(self):
        """
        function vtkView.playMovie(self, interactor, event)

        Callback for playing the time series as a movie in the VTK rendering window, in response to clicking the play button
        This function uses a separate thread to keep the GUI responsive whil playing the movie

        :return:            nothing

        """

        self.playThread.setParams(self.nt, self.tslider, self.playButton, self.repeatButton)
        self.playThread.start()

    def assignData(self, d, colormap=None, transforms=[], dataType=numpy.uint8):
        """
        function vtkView.assignData(self, d)

        Sets the data to be displayed in the VTK rendering window
        The data must be a list of 3D arrays, each of which represents a time point in the recording

        :param d:       the data to be displayed, passed as an array of 3D numpy arrays
        :return: nothing
        """


        firstTime = (self.nt==0)    # If this is the first time data is assigned, we will need to create some objects
        self.nt = len(d)            # The number of time slices in the data
        lz ,ly ,lx = d[0].shape     # The shape of the data (VTK is inverted wrt numpy)
        print("Data dimensions: {:d} x {:d} x {:d}, {:d} time slices".format(lx,ly,lz,self.nt))

        self.numberOfDataSets = 1
        self.data = [d]
        self.tdata = [copy.deepcopy(d)]
        for t in transforms:
            if t.active:
                self.tdata[0] = t.apply(self.tdata[0])

        # Sets the importer to import the first frame of the supplied data
        self.importer[0].SetWholeExtent(0, lx-1, 0, ly-1, 0, lz-1)
        self.importer[0].SetDataExtentToWholeExtent()
        if dataType==numpy.uint8:
            self.importer[0].SetDataScalarTypeToUnsignedChar()
        elif dataType==numpy.uint16:
            self.importer[0].SetDataScalarTypeToUnsignedShort()
        elif dataType==numpy.int:
            self.importer[0].SetDataScalarTypeToInt()

        self.importer[0].SetImportVoidPointer(self.tdata[0][0])
        self.importer[0].Modified()
        self.currentdata = self.tdata

        if self.nt > 1:
            self.displaydFAction.setEnabled(True)
            self.calculatedF()
        else:
            self.displaydFAction.setEnabled(False)

        # Adjusts the colormap
        self.setColorMap(colormap)
        self.colormap = colormap    # To remember what was the colormap when we first displayed this object

        # Connects the importer to the volume mapper and to the slicer
        self.volumeMapper.SetInputConnection(self.importer[0].GetOutputPort())
        self.slice[0].SetInputConnection(self.importer[0].GetOutputPort())
        self.slice[0].Update()

        # Connects the slicer to its mapper
        self.sliceMapper.SetInputConnection(self.slice[0].GetOutputPort())

        if firstTime:
            # If this is the first time we add data, we create
            # a new volume object for the 3D rendering, and
            # another one for the 2D slice
            self.volume = vtk.vtkVolume()
            self.volume.SetMapper(self.volumeMapper)
            self.volume.SetProperty(self.volumeProperty)
            self.renderer.AddVolume(self.volume)

            self.sliceVolume = vtk.vtkImageActor() # vtk.vtkVolume()
            self.sliceVolume.SetMapper(self.sliceMapper)
            # self.sliceVolume.SetProperty(self.sliceVolumeProperty)
            # self.sliceRenderer.AddVolume(self.sliceVolume)
            self.sliceRenderer.AddActor(self.sliceVolume)

            # Displays the plane in the 3D view at the center of the sample
            self.initPlane(lx, ly, lz)

        # Adjusts slider max value to match the data size
        self.zslider.setValue(self.planez)
        self.tslider.setMaximum(self.nt-1)
        if(self.curPlaneOrientation==0):
            self.zslider.setMaximum(ly - 1) # for VTK, the vertical axis is y, although we call it z
        elif(self.curPlaneOrientation==1):
            self.zslider.setMaximum(lz - 1)  # for VTK, the vertical axis is y, although we call it z
        elif(self.curPlaneOrientation==2):
            self.zslider.setMaximum(lx - 1)  # for VTK, the vertical axis is y, although we call it z
        else:
            print('Error: bad value for vtkView.curPlaneOrientation ({:d})'.format(self.curPlaneOrientation))

        # Adjusts the position and orientation of the slicing plane
        self.setCubeDimensions()
        self.setTimeSlice()

        # Updates the view
        self.resetAll()
        self.renderAll(deletePanel=True)

    def initPlane(self,lx,ly,lz):
        """
        vtkView.initPlane(self,lx,ly,lz):

        This adjusts the plane position to be along the z axis,
        at the middle of the sample

        :param lx: x-dimension of the data
        :param ly: y-dimension of the data
        :param lz: z-dimension of the data

        :return: nothing
        """

        self.plane.SetOrigin(-5, 0, -5)
        self.plane.SetPoint1(-5, 0, lz + 5)
        self.plane.SetPoint2(lx + 5, 0, -5)
        self.planez = numpy.uint8(ly/2)
        self.plane.Push(self.planez)

        self.cube.SetBounds(-5, lx + 5, self.planez-0.5, self.planez+0.5, -5, lz + 5)

    def setPlanePosition(self, z=None):
        """
        vtkView.setPlanePosition(self, z = None):

        Callback for the z-slider
        This adjusts the height of the plane in the 3D view to match
        the position of the z-slider, and updates the cut in the 2D view
        It also adjusts the display in the label above the slider

        :param z: (optional) value of the z coordinate
        :return:
        """
        if z is None:
            z = self.zslider.value()

        # This plane is not used in the current version, but we keep updating it anyway
        self.plane.Push(z-self.planez)
        self.planez = z

        if self.curPlaneOrientation == 0:
            # Updates the slicer
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 1, 0, 0,
                               0, 0, 1, z,
                               1, 0, 0, 0,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Updates the plane (cube) in the 3D view
            center = self.cube.GetCenter()
            self.cube.SetCenter(center[0],z,center[2])

            # Adjusts label text
            self.zlabel.setText("z:{:d}".format(z))

        elif self.curPlaneOrientation == 1:
            # Updates the slicer
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 1, 0, 0,
                               1, 0, 0, 0,
                               0, 0, 1, z,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Updates the plane (cube) in the 3D view
            center = self.cube.GetCenter()
            self.cube.SetCenter(center[0], center[1], z)

            # Adjusts label text
            self.zlabel.setText("y:{:d}".format(z))

        elif self.curPlaneOrientation == 2:
            # Updates the slicer
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 0, 1, z,
                               0, 1, 0, 0,
                               1, 0, 0, 0,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Updates the plane (cube) in the 3D view
            center = self.cube.GetCenter()
            self.cube.SetCenter(z, center[1], center[2])

            # Adjusts label text
            self.zlabel.setText("x:{:d}".format(z))

        # Updates the view
        self.renderAll()

    def setPlaneOrientation(self, orientation, coordinate=None):
        """
        Sets the orientation of the slicing plane
        If the requested orientation is different from the current orientation,
        the slicing plane will be rotated as requested and set at the data's middle along that axis

        :param orientation: 0 (z), 1(y) or 2(x)
        :param coordinate: coordinate of the plane along the slicing dimension
        :return: nothing
        """

        self.curPlaneOrientation = orientation
        lz, ly, lx = self.data[0][0].shape

        if orientation == 0:
            # Updates the slicer
            if coordinate is None:
                z = numpy.uint8(ly / 2)
            else:
                z = coordinate
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 1, 0, 0,
                               0, 0, 1, z,
                               1, 0, 0, 0,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Updates the plane
            self.plane.SetOrigin(-5, z, -5)
            self.plane.SetPoint1(-5, z, lz + 5)
            self.plane.SetPoint2(lx + 5, z, -5)
            self.planez = z

            # Updates the cube
            self.cube.SetBounds(-5, lx + 5, self.planez-0.5, self.planez+0.5, -5, lz + 5)

            # Adjusts label text
            self.zlabel.setText("z:{:d}".format(z))

            # Adjusts slider max values
            self.zslider.setMaximum(ly-1)
            self.zslider.setValue(z)

        elif orientation == 1:
            # Updates the slicer
            if coordinate is None:
                z = numpy.uint8(lz / 2)
            else:
                z = coordinate
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 1, 0, 0,
                               0, 0, 1, 0,
                               1, 0, 0, z,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Updates the plane
            self.plane.SetOrigin(-5, -5, z)
            self.plane.SetPoint1(-5, ly + 5, z)
            self.plane.SetPoint2(lx + 5, -5, z)
            self.planez = z

            # Updates the cube
            self.cube.SetBounds(-5, lx + 5, -5, ly + 5, self.planez-0.5, self.planez+0.5)

            # Adjusts label text
            self.zlabel.setText("y:{:d}".format(z))

            # Adjusts slider max values
            self.zslider.setMaximum(lz-1)
            self.zslider.setValue(z)

        elif orientation == 2:
            # Updates the slicer
            if coordinate is None:
                z = numpy.uint8(lx / 2)
            else:
                z = coordinate
            sagittal = vtk.vtkMatrix4x4()
            sagittal.DeepCopy((0, 1, 0, z,
                               0, 0, 1, 0,
                               1, 0, 0, 0,
                               0, 0, 0, 1))
            for i in range(self.numberOfDataSets):
                self.slice[i].SetResliceAxes(sagittal)
                self.slice[i].Update()

            # Adjusts the plane
            self.plane.SetOrigin(z, -5, -5)
            self.plane.SetPoint1(z, ly + 5, -5)
            self.plane.SetPoint2(z, -5, lz + 5)
            self.planez = z

            # Adjusts the cube
            self.cube.SetBounds(self.planez-0.5, self.planez+0.5, -5, ly + 5, -5, lz + 5)

            # Adjusts label text
            self.zlabel.setText("x:{:d}".format(z))

            # Adjusts slider max values
            self.zslider.setMaximum(lx-1)
            self.zslider.setValue(z)

        for i in range(self.numberOfDataSets):
            self.slice[i].Update()

        # Updates the view
        self.renwin.Render()
        self.slicerenwin.Render()

    def setCubeDimensions(self):
        lz, ly, lx = self.data[0][0].shape

        if self.curPlaneOrientation == 0:
            self.cube.SetBounds(-5, lx + 5, self.planez - 0.5, self.planez + 0.5, -5, lz + 5)
        elif self.curPlaneOrientation == 1:
            self.cube.SetBounds(-5, lx + 5, -5, ly + 5, self.planez - 0.5, self.planez + 0.5)
        elif self.curPlaneOrientation == 2:
            self.cube.SetBounds(self.planez - 0.5, self.planez + 0.5, -5, ly + 5, -5, lz + 5)

    def setTimeSlice(self):
        """
        vtkView.setTimeSlice()

        Callback to the t-slider
        This adjusts the displayed data in the 2D and 3D views,
        as well as the text of the label

        :return: nothing
        """

        t = self.tslider.value()
        if(t < self.nt):
            for i in range(self.numberOfDataSets):
                self.importer[i].SetImportVoidPointer(self.currentdata[i][t])
                self.importer[i].Modified()
                self.slice[i].Update()

        self.tlabel.setText("t:{:d}".format(t))

        self.renwin.Render()
        self.slicerenwin.Render()

    def displayF(self):
        self.displayFAction.setChecked(True)
        self.displaydFAction.setChecked(False)

        lz, ly, lx = self.tdata[0][0].shape

        if self.numberOfDataSets == 1:
            self.setColorMap(self.colormap)

        # Sets the importer to point to the right array
        t = self.tslider.value()
        self.currentdata = self.tdata
        for i in range(self.numberOfDataSets):
            self.importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
            self.importer[i].SetDataExtentToWholeExtent()
            self.importer[i].SetImportVoidPointer(self.tdata[i][t])
            self.importer[i].Modified()
            self.slice[i].Update()

        # updates the display
        self.renwin.Render()
        self.slicerenwin.Render()

    def displaydF(self):
        self.displayFAction.setChecked(False)
        self.displaydFAction.setChecked(True)

        lz, ly, lx = self.dFdata[0][0].shape

        if self.numberOfDataSets == 1:
            self.setColorMap('Standard')

        # Sets the importer to point to the right array
        self.currentdata = self.dFdata
        t = self.tslider.value()
        for i in range(self.numberOfDataSets):
            self.importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
            self.importer[i].SetDataExtentToWholeExtent()
            self.importer[i].SetImportVoidPointer(self.dFdata[i][t])
            self.importer[i].Modified()
            self.slice[i].Update()

        # updates the display
        self.renwin.Render()
        self.slicerenwin.Render()

    def sliceX(self):
        self.sliceXAction.setChecked(True)
        self.sliceYAction.setChecked(False)
        self.sliceZAction.setChecked(False)
        self.setPlaneOrientation(2)

    def sliceY(self):
        self.sliceXAction.setChecked(False)
        self.sliceYAction.setChecked(True)
        self.sliceZAction.setChecked(False)
        self.setPlaneOrientation(1)

    def sliceZ(self):
        self.sliceXAction.setChecked(False)
        self.sliceYAction.setChecked(False)
        self.sliceZAction.setChecked(True)
        self.setPlaneOrientation(0)

    def playMovieUpdateGUI(self, i):
        pass
        # self.renwin.Render()
        # self.slicerenwin.Render()
        # self.tslider.repaint()
        # self.zslider.repaint()

    def showDiff(self, data1, data2, transforms1=(), transforms2=()):
        self.calculateDiff(data1=data1,data2=data2,transforms1=transforms1,transforms2=transforms2)
        self.colormap = 'Diff'
        self.assignData(self.tdata[0], colormap='Diff')

    def showtDiff(self, data, transforms=()):
        self.calculatetDiff(data=data,transforms=transforms)
        self.colormap = 'Diff'
        self.assignData(self.tdata[0], colormap='Diff')

    def overlay(self, data1, data2, transforms1=(), transforms2=(), colormap=None, dataType=numpy.uint8):
        """
                function vtkView.overlay(self, data1, data2, transforms1=(), transforms2=(), colormap=None, dataType=numpy.uint8)

                Overlays two data sets in the rendering window
                Each data set must be a list of 3D arrays, each of which represents a time point in the recording

                :param data1:       the first data set, passed as an array of 3D numpy arrays
                :param data2:       the second data set, passed as an array of 3D numpy arrays
                :param transforms1: a list of transforms to be applied to the first data set
                :param transforms2: a list of transforms to be applied to the second data set
                :return: nothing
                """

        firstTime = (self.nt == 0)  # If this is the first time data is assigned, we will need to create some objects

        self.nt = len(data1)  # The number of time slices in the data
        lz, ly, lx = data1[0].shape  # The shape of the data (VTK is inverted wrt numpy)
        print("Data dimensions: {:d} x {:d} x {:d}, {:d} time slices".format(lx, ly, lz, self.nt))
        if colormap is None:
            colormap = 'Overlay'


        self.numberOfDataSets = 2
        self.data = [copy.deepcopy(data1), copy.deepcopy(data2)]
        self.tdata = [data1, data2]
        for t in transforms1:
            if t.active:
                self.tdata[0] = t.apply(self.tdata[0])

        for t in transforms2:
            if t.active:
                self.tdata[0] = t.apply(self.tdata[1])

        # Sets the importer to import the first frame of the supplied data

        for i in range(self.numberOfDataSets):
            self.importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
            self.importer[i].SetDataExtentToWholeExtent()
            if dataType == numpy.uint8:
                self.importer[i].SetDataScalarTypeToUnsignedChar()
            elif dataType == numpy.uint16:
                self.importer[i].SetDataScalarTypeToUnsignedShort()
            elif dataType == numpy.int:
                self.importer[i].SetDataScalarTypeToInt()
            elif dataType == numpy.float:
                self.importer[i].SetDataScalarTypeToFloat()
            elif dataType == numpy.float:
                self.importer[i].SetDataScalarTypeToDouble()

        self.currentdata = self.tdata

        # Imports the data
        for i in range(self.numberOfDataSets):
            self.importer[i].SetImportVoidPointer(self.tdata[i][0])
            self.importer[i].Modified()


        if self.nt > 1:
            self.displaydFAction.setEnabled(True)
            self.calculatedF()
        else:
            self.displaydFAction.setEnabled(False)

        # Adjusts the colormap
        self.setColorMap(colormap)
        self.colormap = colormap  # To remember what was the colormap when we first displayed this object

        # Connects the importer to the volume mapper and to the slicer
        self.blender.RemoveAllInputConnections(0)
        self.sliceBlender.RemoveAllInputConnections(0)
        self.volumeMapper.SetInputConnection(self.blender.GetOutputPort())
        for i in range(self.numberOfDataSets):
            self.blender.AddInputConnection(self.importer[i].GetOutputPort())
            self.slice[i].SetInputConnection(self.importer[i].GetOutputPort())
            self.sliceBlender.AddInputConnection(self.slice[i].GetOutputPort())

        self.sliceBlender.SetBlendModeToNormal()
        # self.sliceBlender.SetOpacity(0, .5)
        self.sliceBlender.SetOpacity(1, 0.5)

        # Connects the slicer to its mapper
        self.sliceMapper.SetInputConnection(self.sliceBlender.GetOutputPort())

        if firstTime:
            # If this is the first time we add data, we create
            # a new volume object for the 3D rendering, and
            # another one for the 2D slice
            self.volume = vtk.vtkVolume()
            self.volume.SetMapper(self.volumeMapper)
            self.volume.SetProperty(self.volumeProperty)
            self.renderer.AddVolume(self.volume)

            self.sliceVolume = vtk.vtkImageActor() #vtk.vtkVolume()
            self.sliceVolume.SetMapper(self.sliceMapper)
            # self.sliceVolume.SetProperty(self.sliceVolumeProperty)
            # self.sliceRenderer.AddVolume(self.sliceVolume)
            self.sliceRenderer.AddActor(self.sliceVolume)

            # Displays the plane in the 3D view at the center of the sample
            self.initPlane(lx, ly, lz)

        # Adjusts slider max value to match the data size
        self.zslider.setValue(self.planez)
        self.tslider.setMaximum(self.nt - 1)
        if (self.curPlaneOrientation == 0):
            self.zslider.setMaximum(ly - 1)  # for VTK, the vertical axis is y, although we call it z
        elif (self.curPlaneOrientation == 1):
            self.zslider.setMaximum(lz - 1)  # for VTK, the vertical axis is y, although we call it z
        elif (self.curPlaneOrientation == 2):
            self.zslider.setMaximum(lx - 1)  # for VTK, the vertical axis is y, although we call it z
        else:
            print('Error: bad value for vtkView.curPlaneOrientation ({:d})'.format(self.curPlaneOrientation))

        # Adjusts the position and orientation of the slicing plane
        self.setCubeDimensions()
        self.setTimeSlice()

        # Updates the view
        self.resetAll()
        self.renderAll(deletePanel=True)

        self.colormap = colormap



    def overlayVOIs(self, data):
        """
                function vtkView.overlayVOIs(self, data)

                Overlays any number of VOI images in the VTK view
                data is a list of 3D binary arrays (uint8, scaled 0-255) where each member is a set of VOIs

                :param data:    the VOI data
                :return: nothing
                """

        firstTime = (self.nt == 0)  # If this is the first time data is assigned, we will need to create some objects

        self.nt = 1
        self.data = [[d] for d in data] # often used to check the shape of the data
        self.currentdata = self.data

        lz, ly, lx = data[0].shape  # The shape of the data (VTK is inverted wrt numpy)
        print("Data dimensions: {:d} x {:d} x {:d}, {:d} time slices".format(lx, ly, lz, self.nt))

        self.numberOfDataSets = len(data)
        print("number of datasets: {:d}".format(self.numberOfDataSets))
        # In the case where we have more than 2 data sets,
        # we cannot rely on the vtkView member objects, thus
        # we create arrays of VTK objects to import an overlay the data

        print("creating importers, imageMapToColors and slices...")
        self.importer = [vtk.vtkImageImport() for i in range(self.numberOfDataSets)]
        images = [vtk.vtkImageMapToColors() for i in range(self.numberOfDataSets)]
        self.slice = [vtk.vtkImageResliceToColors() for i in range(self.numberOfDataSets)]
        for i in range(self.numberOfDataSets):
            self.importer[i].SetWholeExtent(0, lx - 1, 0, ly - 1, 0, lz - 1)
            self.importer[i].SetDataExtentToWholeExtent()
            self.importer[i].SetDataScalarTypeToUnsignedChar()
            self.importer[i].SetImportVoidPointer(data[i])
            self.importer[i].Modified()
        print("done.")

        self.displaydFAction.setEnabled(False)

        # Creates the colormap
        print("creating color maps and lookup tables...")
        t = cm.ScalarMappable(None, "nipy_spectral") #"Set1")
        r = t.to_rgba(range(self.numberOfDataSets))
        print("Retrieved colormap")

        table = [vtk.vtkLookupTable() for i in range(self.numberOfDataSets)]
        print("created vtk objects")

        for i in range(self.numberOfDataSets):
            table[i].SetRange(0, 1)
            table[i].SetAlphaRange(0,1)
            table[i].SetTableValue(0, [0,0,0,0])
            # table[i].SetTableValue(1, numpy.append(r[i,0:3],1))
            table[i].SetTableValue(1, [int(i==0),int(i==1),int(i==2),1])
            table[i].Build()

        opacityMap = vtk.vtkPiecewiseFunction()
        opacityMap.AddPoint(0,0)
        opacityMap.AddPoint(1, 0.25)

        colorMaps = [vtk.vtkColorTransferFunction() for i in range(3)]
        for i in range(3):
            colorMaps[i].SetColorSpaceToRGB()
            colorMaps[i].AddRGBPoint(0, 0, 0, 0)
            # colorMaps[i].AddRGBPoint(1, r[i,0], r[i,1], r[1,2])
            colorMaps[i].AddRGBPoint(1, int(i==0), int(i==1), int(i==2))

        print("done")

        sagittal = vtk.vtkMatrix4x4()
        sagittal.DeepCopy((0, 1, 0, 0,
                           0, 0, 1, 127.5,
                           1, 0, 0, 0,
                           0, 0, 0, 1))

        for i in range(self.numberOfDataSets):
            self.slice[i].SetOutputDimensionality(2)
            self.slice[i].SetInterpolationModeToLinear()
            self.slice[i].SetResliceAxes(sagittal)

        for i in range(3):
            self.volumeProperty.SetColor(i, colorMaps[i])
            self.volumeProperty.SetScalarOpacity(i, opacityMap)
        self.volumeProperty.SetScalarOpacity(3, opacityMap)

        print("Creating color images...")
        for i in range(self.numberOfDataSets):
            images[i].SetInputConnection(self.importer[i].GetOutputPort())
            images[i].SetLookupTable(table[i])
            # images[i].PassAlphaToOutputOn()

        # Connects the importer to the volume mapper and to the slicer
        self.blender.RemoveAllInputConnections(0)
        self.sliceBlender.RemoveAllInputConnections(0)
        self.blender.SetBlendModeToNormal()
        self.sliceBlender.SetBlendModeToNormal()

        print("adding connections to blenders....")
        for i in range(self.numberOfDataSets):
            print("component {:d}".format(i))
            self.blender.AddInputConnection(images[i].GetOutputPort())
            self.slice[i].SetInputConnection(self.importer[i].GetOutputPort())
            self.slice[i].SetLookupTable(table[i])
            self.sliceBlender.AddInputConnection(self.slice[i].GetOutputPort())
            self.blender.SetOpacity(i, 0.5)
            self.sliceBlender.SetOpacity(i, 0.5)
        print("done")

        print("Number of connections: {:d}".format(self.blender.GetNumberOfInputs ()))

        # Connects the objects to their mapper
        print("Connecting to mappers...")
        print("volume")
        self.volumeMapper.SetInputConnection(self.blender.GetOutputPort())
        print("slice")
        self.sliceMapper.SetInputConnection(self.sliceBlender.GetOutputPort())
        print("done")

        # firstTime = True
        if firstTime:
            # If this is the first time we add data, we create
            # a new volume object for the 3D rendering, and
            # another one for the 2D slice
            self.volume = vtk.vtkVolume()
            self.volume.SetMapper(self.volumeMapper)
            self.volume.SetProperty(self.volumeProperty)
            self.renderer.AddVolume(self.volume)

            self.sliceVolume = vtk.vtkImageActor() #vtk.vtkVolume()
            self.sliceVolume.SetMapper(self.sliceMapper)
            self.sliceRenderer.AddActor(self.sliceVolume)

            # Displays the plane in the 3D view at the center of the sample
            self.initPlane(lx, ly, lz)

        # Adjusts slider max value to match the data size
        self.zslider.setValue(self.planez)
        self.tslider.setMaximum(self.nt - 1)
        if (self.curPlaneOrientation == 0):
            self.zslider.setMaximum(ly - 1)  # for VTK, the vertical axis is y, although we call it z
        elif (self.curPlaneOrientation == 1):
            self.zslider.setMaximum(lz - 1)  # for VTK, the vertical axis is y, although we call it z
        elif (self.curPlaneOrientation == 2):
            self.zslider.setMaximum(lx - 1)  # for VTK, the vertical axis is y, although we call it z
        else:
            print('Error: bad value for vtkView.curPlaneOrientation ({:d})'.format(self.curPlaneOrientation))

        # Adjusts the position and orientation of the slicing plane
        self.setCubeDimensions()

        # Updates the view
        self.resetAll()
        self.renderAll(deletePanel=True)

    def resetAll(self):
        self.renderer.ResetCamera()
        self.sliceRenderer.ResetCamera()

    def renderAll(self, deletePanel=False):
        self.renwin.Render()
        self.slicerenwin.Render()
        if deletePanel:
            if self.VOIpanel is not None:
                print('Deleting panel(s)')
                if isinstance(self.VOIpanel, list):
                    for p in self.VOIpanel:
                        p.close()
                else:
                    self.VOIpanel.close()
                self.VOIpanel = None

    def plotdF(self, interactor, event):
        """
        camphor.vtkView.plotdF(self,interactor,event):
        callback function for the slice display.
        When pressing the key 'p', the F activity is averaged over a 3x3x3 volume
        around the location of the mouse pointer, and the resulting time series is
        appended to the variable pltdata1 (for view 1) and pltdata2 (for view 2)
        it can then be accessed from the ipython console and plotted to examine the
        response of manually-selected cell bodies (or VOIs)

        :param interactor:
        :param event:
        :return:
        """
        key = interactor.GetKeySym()
        pos = interactor.GetEventPosition()

        print("key pressed: {:s}".format(key))
        if key == "p":
            picker = vtk.vtkPropPicker()
            picker.Pick(pos[0], pos[1], 0, self.sliceRenderer)
            pos = picker.GetPickPosition()
            print(pos)

            # take a 2x2x2 voxel and plot the average F
            if self.camphor.vtkView is self:
                odata = self.camphor.vtkView2.tdata[0]
            else:
                odata = self.camphor.vtkView.tdata[0]

            if self.curPlaneOrientation == 0:
                z = self.planez
                x = numpy.round(pos[0]).astype(numpy.int)
                y = numpy.round(pos[1]).astype(numpy.int)
                print(x)
                f1 = [numpy.mean(self.tdata1[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
                f2 = [numpy.mean(odata[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
            elif self.curPlaneOrientation == 1:
                x = self.planez
                z = numpy.round(pos[0]).astype(numpy.int)
                y = numpy.round(pos[1]).astype(numpy.int)
                f1 = [numpy.mean(self.tdata1[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
                f2 = [numpy.mean(odata[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
            elif self.curPlaneOrientation == 2:
                y = self.planez
                x = numpy.round(pos[0]).astype(numpy.int)
                z = numpy.round(pos[1]).astype(numpy.int)
                f1 = [numpy.mean(self.tdata1[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
                f2 = [numpy.mean(odata[i][x - 1:x + 1, z - 1:z + 1, y - 1:y + 1]) for i in range(self.nt)]
            else:
                f1 = None
                f2 = None

            if self.camphor.vtkView is self:
                self.camphor.pltdata[0].append(f1)
                self.camphor.pltdata[1].append(f2)
            else:
                self.camphor.pltdata[0].append(f2)
                self.camphor.pltdata[1].append(f1)
            print('Appended to pltdata')

            self.camphor.VOIlist.append([x, z, y])

        elif key == 'd':
            print('Erased pltdata')
            self.camphor.pltdata = [[] for i in range(self.numberOfDataSets)]

        elif key=="v":
            picker = vtk.vtkPropPicker()
            picker.Pick(pos[0], pos[1], 0, self.sliceRenderer)
            pos = picker.GetPickPosition()
            print('Click position: ({:d},{:d})'.format(numpy.round(pos[0]),numpy.round(pos[1])))


    ##########################
    ### ANALYSIS FUNCTIONS ###
    ##########################

    def calculatedF(self):
        # Calculates the baseline fluorescence
        # For later convenience, we do NOT cast is to uint8

        self.baseline = [numpy.zeros(self.tdata[i][0].shape) for i in range(self.numberOfDataSets)]
        self.dFdata = [self.tdata[i].copy() for i in range(self.numberOfDataSets)]
        for i in range(self.numberOfDataSets):
            for t in range(self.ini['baseline_endframe']):
                self.baseline[i] += self.tdata[i][t]
            self.baseline[i] /= self.ini['baseline_endframe']

        self.dFdata = [[numpy.maximum(0, self.data[i][t] - self.baseline[i]).astype(numpy.uint8) for t in range(self.nt)]
                       for i in range(self.numberOfDataSets)]


    def calculateDiff(self, data1, data2, transforms1=(), transforms2=()):
        # Calculates the difference in fluorescence between two sets of data
        # This requires the two data sets to have, of course, the same dimensions

        self.data = [[numpy.uint8((data1[i].astype(numpy.double) - data2[i].astype(numpy.double))/2 + 128) for i in range(len(data1))]]
        for t in transforms1:
            if t.active:
                data1 = t.apply(data1)
        for t in transforms2:
            if t.active:
                data2 = t.apply(data2)
        self.tdata = [[numpy.uint8((data1[i].astype(numpy.double) - data2[i].astype(numpy.double))/2 + 128) for i in range(len(data1))]]

    def calculatetDiff(self, data, transforms=()):
        # Calculates the difference in fluorescence between neighboring time frames

        self.data = [[numpy.uint8((data[i+1].astype(numpy.double) - data[i].astype(numpy.double)) / 2 + 128)
                     for i in range(len(data)-1)]]

        for t in transforms:
            if t.active:
                data = t.apply(data)

        self.tdata = [[numpy.uint8((data[i+1].astype(numpy.double) - data[i].astype(numpy.double))/2 + 128)
                      for i in range(len(data)-1)]]

    def setColorMap(self, colormap=None):
        if colormap is None:
            colormap = 'Standard'
        print(colormap)

        if isinstance(self.opacityMaps[colormap], list):
            for i in range(len(self.opacityMaps[colormap])):
                self.volumeProperty.SetScalarOpacity(i,self.opacityMaps[colormap][i])
        else:
            self.volumeProperty.SetScalarOpacity(self.opacityMaps[colormap])

        # if isinstance(self.sliceOpacityMaps[colormap], list):
        #     for i in range(len(self.sliceOpacityMaps[colormap])):
        #         self.sliceVolumeProperty.SetScalarOpacity(i,self.sliceOpacityMaps[colormap][i])
        # else:
        #     self.sliceVolumeProperty.SetScalarOpacity(self.sliceOpacityMaps[colormap])

        if isinstance(self.colorMaps[colormap], list):
            for i in range(len(self.colorMaps[colormap])):
                self.volumeProperty.SetColor(i,self.colorMaps[colormap][i])
        else:
            self.volumeProperty.SetColor(self.colorMaps[colormap])


        if isinstance(self.sliceColorMaps[colormap], list):
            self.slice[0].SetLookupTable(self.sliceLookupTables[colormap][0])
            self.slice[1].SetLookupTable(self.sliceLookupTables[colormap][1])
        else:
            self.slice[0].SetLookupTable(self.sliceLookupTables[colormap])

    def makeColorMaps(self):
        self.colorMaps = {}
        self.opacityMaps = {}
        self.sliceColorMaps = {}
        self.sliceOpacityMaps = {}

        # Create transfer mapping scalar value to opacity.
        opacityFunction = vtk.vtkPiecewiseFunction()
        opacityFunction.AddPoint(0, 0)
        opacityFunction.AddPoint(255, 0.25)
        self.opacityMaps['Standard'] = opacityFunction

        overlayOpacityFunction = vtk.vtkPiecewiseFunction()
        overlayOpacityFunction.AddPoint(0,0)
        overlayOpacityFunction.AddPoint(255,0.25)
        self.opacityMaps['Overlay'] = [overlayOpacityFunction, overlayOpacityFunction]

        # Opacity function for vizualizing difference
        diffOpacityFunction = vtk.vtkPiecewiseFunction()
        diffOpacityFunction.AddPoint(0, 0.5)
        diffOpacityFunction.AddPoint(128, 0.0)
        diffOpacityFunction.AddPoint(255, 0.5)
        self.opacityMaps['Diff'] = diffOpacityFunction

        # This one is for the slice view
        sliceOpacityFunction = vtk.vtkPiecewiseFunction()
        sliceOpacityFunction.AddPoint(0, 0.25)
        sliceOpacityFunction.AddPoint(8, 0.5)
        sliceOpacityFunction.AddPoint(16, 1)
        sliceOpacityFunction.AddPoint(255, 1)
        self.sliceOpacityMaps['Standard'] = sliceOpacityFunction

        overlaySliceOpacityFunction = vtk.vtkPiecewiseFunction()
        overlaySliceOpacityFunction.AddPoint(0, 0.25)
        overlaySliceOpacityFunction.AddPoint(8, 0.5)
        overlaySliceOpacityFunction.AddPoint(16, 1)
        overlaySliceOpacityFunction.AddPoint(255, 1)
        self.sliceOpacityMaps['Overlay'] = [overlaySliceOpacityFunction, overlaySliceOpacityFunction]

        sliceDiffOpacityFunction = vtk.vtkPiecewiseFunction()
        sliceDiffOpacityFunction.AddPoint(0, 1)
        sliceDiffOpacityFunction.AddPoint(112, 1)
        sliceDiffOpacityFunction.AddPoint(120, 0.5)
        sliceDiffOpacityFunction.AddPoint(128, 0.25)
        sliceDiffOpacityFunction.AddPoint(136, 0.5)
        sliceDiffOpacityFunction.AddPoint(142, 1)
        sliceDiffOpacityFunction.AddPoint(255, 1)
        self.sliceOpacityMaps['Diff'] = sliceDiffOpacityFunction

        # Create transfer mapping scalar value to color.
        colorFunction = vtk.vtkColorTransferFunction()
        colorFunction.SetColorSpaceToRGB()

        # Normal blue-white-red colormap
        colorFunction.AddRGBPoint(0, 0.0, 0.0, 1.0)
        colorFunction.AddRGBPoint(128, 1, 1, 1)
        colorFunction.AddRGBPoint(255, 1.0, 0.0, 0.0)
        self.colorMaps['Standard'] = colorFunction
        self.sliceColorMaps['Standard'] = colorFunction

        # Interesting blue-green-white-red colormap
        # self.colorFunction.AddRGBPoint(0, 0.0, 0.0, 1.0)
        # self.colorFunction.AddRGBPoint(85, 0, 1, 0)
        # self.colorFunction.AddRGBPoint(170, 1, 1, 1)
        # self.colorFunction.AddRGBPoint(255, 1.0, 0.0, 0.0)

        # Color map for vizualizing differences
        diffColorFunction = vtk.vtkColorTransferFunction()
        diffColorFunction.SetColorSpaceToRGB()
        diffColorFunction.AddRGBPoint(0, 0.0, 0.0, 1.0)
        diffColorFunction.AddRGBPoint(128, 0.1, 0.1, 0.1)
        diffColorFunction.AddRGBPoint(255, 1.0, 0.0, 0.0)
        self.colorMaps['Diff'] = diffColorFunction
        self.sliceColorMaps['Diff'] = diffColorFunction

        # Color maps for overlays
        o1 = vtk.vtkColorTransferFunction()
        o1.SetColorSpaceToRGB()
        o2 = vtk.vtkColorTransferFunction()
        o2.SetColorSpaceToRGB()
        o1.AddRGBPoint(0, 0.0, 0.0, 0.0)
        o1.AddRGBPoint(1, 0.1, 0.0, 0.1)
        o1.AddRGBPoint(255, 1.0, 0.0, 1.0)
        o2.AddRGBPoint(0, 0.0, 0.0, 0.0)
        o2.AddRGBPoint(1, 0.0, 0.1, 0.0)
        o2.AddRGBPoint(255, 0.0, 1.0, 0.0)
        self.colorMaps['Overlay'] = [o1,o2]
        self.sliceColorMaps['Overlay'] = [o1,o2]

        o1 = vtk.vtkColorTransferFunction()
        o1.SetColorSpaceToRGB()
        o2 = vtk.vtkColorTransferFunction()
        o2.SetColorSpaceToRGB()
        o1.AddRGBPoint(0, 0.0, 0.0, 0.0)
        o1.AddRGBPoint(1, 0.1, 0.0, 0.1)
        o1.AddRGBPoint(128, 1.0, 0.0, 1.0)
        o2.AddRGBPoint(0, 0.0, 0.0, 0.0)
        o2.AddRGBPoint(1, 0.0, 0.1, 0.0)
        o2.AddRGBPoint(128, 0.0, 1.0, 0.0)


        # Lookup tables
        t = vtk.vtkLookupTable()
        t.SetRange(0, 255)
        for i in range(256):
            a = self.sliceOpacityMaps['Standard'].GetValue(i)
            t.SetTableValue(i, list(self.colorMaps['Standard'].GetColor(i)) + [a])
        self.sliceLookupTables['Standard'] = t

        t = vtk.vtkLookupTable()
        t.SetRange(0, 255)
        for i in range(256):
            a = self.sliceOpacityMaps['Diff'].GetValue(i)
            t.SetTableValue(i, list(self.colorMaps['Diff'].GetColor(i)) + [a])
        self.sliceLookupTables['Diff'] = t

        t1 = vtk.vtkLookupTable()
        t2 = vtk.vtkLookupTable()
        t1.SetRange(0, 255)
        t2.SetRange(0, 255)
        for i in range(256):
            a = self.sliceOpacityMaps['Overlay'][0].GetValue(i)
            t1.SetTableValue(i, list(self.sliceColorMaps['Overlay'][0].GetColor(i)) + [a])
            t2.SetTableValue(i, list(self.sliceColorMaps['Overlay'][1].GetColor(i)) + [a])
        self.sliceLookupTables['Overlay'] = [t1,t2]

        t1 = vtk.vtkLookupTable()
        t2 = vtk.vtkLookupTable()
        t1.SetRange(0, 255)
        t2.SetRange(0, 255)
        for i in range(256):
            a = self.sliceOpacityMaps['Standard'].GetValue(i)
            t1.SetTableValue(i, list(self.sliceColorMaps['Standard'].GetColor(i)) + [a])
            t2.SetTableValue(i, list(self.sliceColorMaps['Overlay'][0].GetColor(i)) + [a])
        self.sliceLookupTables['OverlayVOI'] = [t1, t2]

        self.colorMaps['OverlayVOI'] = [self.colorMaps['Standard'], self.colorMaps['Overlay'][0]]
        self.opacityMaps['OverlayVOI'] = [self.opacityMaps['Standard'], self.opacityMaps['Overlay'][0]]
        self.sliceColorMaps['OverlayVOI'] = [self.sliceColorMaps['Standard'], self.sliceColorMaps['Overlay'][0]]
        self.sliceOpacityMaps['OverlayVOI'] = [self.sliceOpacityMaps['Standard'], self.sliceOpacityMaps['Overlay'][0]]

        t1 = vtk.vtkLookupTable()
        t2 = vtk.vtkLookupTable()
        t1.SetRange(0, 255)
        t2.SetRange(0, 255)
        for i in range(256):
            a = self.sliceOpacityMaps['Standard'].GetValue(i)
            t1.SetTableValue(i, list(self.sliceColorMaps['Standard'].GetColor(i)) + [a])
            t2.SetTableValue(i, list(self.sliceColorMaps['Overlay'][0].GetColor(i)) + [a])
        self.sliceLookupTables['OverlayHRS'] = [t2, t1]

        self.colorMaps['OverlayHRS'] = [self.colorMaps['Overlay'][0], self.colorMaps['Standard']]
        self.opacityMaps['OverlayHRS'] = [self.opacityMaps['Overlay'][0], self.opacityMaps['Standard']]
        self.sliceColorMaps['OverlayHRS'] = [self.sliceColorMaps['Overlay'][0], self.sliceColorMaps['Standard']]
        self.sliceOpacityMaps['OverlayHRS'] = [self.sliceOpacityMaps['Overlay'][0], self.sliceOpacityMaps['Standard']]

    ##########################
    ###  USER INTERACTION  ###
    ##########################
    def start(self):
        """
        function vtkView.start(self)

        Starts the vtk interactor object.
        It is necessary to call this function once after constructing a VTKView object.

        :return:    nothing
        """

        self.interactor.Initialize()
        self.interactor.Start()
        self.sliceInteractor.Initialize()
        self.sliceInteractor.Start()

###### END OF class vtkView(QtGui.QFrame)

class playMovieThread(QtCore.QThread):
    """
    class playMovieThread(QtCore.QThread)

    This class implements the thread that will play the movie in the VTK rendering window

    Call setParams() once to set the parameters before starting the thread.

    """

    framedone = QtCore.pyqtSignal(object)  # signal to tell the GUI we have finished displaying one slice

    def __init__(self):
        QtCore.QThread.__init__(self)

    def setParams(self, nt, tslider, playButton, repeatButton):
        """
        setParams(nt, tslider, playButton, repeatButton)

        sets the number of time slices (nt) and passes references to the GUI objects necessary
        for run()

        At the moment, playButton is not needed, but we could implement a button
        that changes to "stop" during the playback
        """

        self.nt = nt
        self.tslider = tslider
        self.playButton = playButton
        self.repeatButton = repeatButton

    def run(self):
        """
        This is the main function of the thread, called using playMovieThread.start()
        It plays the movie by periodically incrementing the value of the t-slider
        The movie is played in loop as long as the repeat button is toggled

        :return:
        """


        repeat = True
        while repeat:
            for i in range(self.nt):
                self.tslider.setValue(i)
                self.framedone.emit(i)
                time.sleep(0.05)
            repeat = self.repeatButton.isChecked()

####### END OF CLASS playMovieThread
