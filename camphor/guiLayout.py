from PyQt4 import QtGui, QtCore
from camphor import utils
from camphor.vtkView import vtkView
from camphor.projectView import projectView
from camphor.registration import regTools
from camphor.VOI import VOITools

def makeLayout(self):
    # Creates some Qt actions (menus, toolbar buttons, etc)
    self.openAction = QtGui.QAction('Open Imaging Data (view 1)', self)
    self.openAction.setIcon(utils.overlayIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton), '1'))
    self.openAction.setShortcut('Ctrl+O')
    self.openAction.setStatusTip('Read and display LSM or TIFF Data in view 1')
    self.openAction.triggered.connect(self.openFile1)  # connects openAction triggered signal to the openFile() slot

    self.openAction2 = QtGui.QAction('Open Imaging Data (view 2)', self)
    self.openAction2.setIcon(utils.overlayIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton), '2'))
    self.openAction2.setShortcut('Ctrl+P')
    self.openAction2.setStatusTip('Read and display LSM or TIFF Data in view 2')
    self.openAction2.triggered.connect(self.openFile2)  # connects openAction2 triggered signal to the openFile2() slot

    self.quitAction = QtGui.QAction('Quit', self)
    self.quitAction.setShortcut('Ctrl+Q')
    self.quitAction.setStatusTip('Quit')
    self.quitAction.triggered.connect(self.close)  # connects quitAction triggered signal to the close() slot

    self.loadProjectAction = QtGui.QAction('Load project', self)
    self.loadProjectAction.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogOpenButton))
    self.loadProjectAction.setShortcut('Ctrl+L')
    self.loadProjectAction.setStatusTip('Load CaMPhor project')
    self.loadProjectAction.triggered.connect(self.loadProject)

    self.saveProjectAction = QtGui.QAction('Save project', self)
    self.saveProjectAction.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogSaveButton))
    self.saveProjectAction.setShortcut('Ctrl+S')
    self.saveProjectAction.setStatusTip('Save project in python pickle format')
    self.saveProjectAction.triggered.connect(self.saveProject)

    # Creates the status bar
    self.statusBar = QtGui.QStatusBar()
    self.setStatusBar(self.statusBar)
    self.Output('Initializing...')

    # Creates the menu bar and adds items
    menubar = self.menuBar()
    self.fileMenu = menubar.addMenu('&File')
    self.fileMenu.addAction(self.openAction)
    self.fileMenu.addAction(self.openAction2)
    self.fileMenu.addSeparator()
    self.fileMenu.addAction(self.saveProjectAction)
    self.fileMenu.addSeparator()
    self.fileMenu.addAction(self.quitAction)

    # Creates a toolbar and adds actions
    self.toolbar = self.addToolBar('CamPhor toolbar')
    self.toolbar.addAction(self.openAction)
    self.toolbar.addAction(self.openAction2)
    self.toolbar.addSeparator()
    self.toolbar.addAction(self.loadProjectAction)
    self.toolbar.addAction(self.saveProjectAction)
    self.toolbar.setIconSize(QtCore.QSize(16,16))

    # Loads the resource file
    self.ini = utils.readConfig('camphor.ini')

    # Sets window size, position and title
    self.setGeometry(100, 100, 1200, 800)
    self.setWindowTitle(self.ini['APPNAME'])
    self.show()

    ### GUI layout
    # Creates the VTK rendering widget2
    self.vtkView = vtkView.vtkView(self, self.ini)
    self.vtkView2 = vtkView.vtkView(self, self.ini)

    # Project view
    self.projectView = projectView.projectView(parent=self)

    # Splitter
    self.splitter = QtGui.QSplitter()
    self.splitterLeftSide = QtGui.QWidget()
    self.splitterRightSide = QtGui.QWidget()
    self.splitter.addWidget(self.splitterLeftSide)
    self.splitter.addWidget(self.splitterRightSide)
    self.splitterLeftSideLayout = QtGui.QVBoxLayout()
    self.splitterLeftSide.setLayout(self.splitterLeftSideLayout)
    makeProjectToolbar(self)
    self.splitterLeftSideLayout.addWidget(self.projectToolBar)
    self.splitterLeftSideLayout.addWidget(self.projectView)

    # The registration tools widget
    self.regTools = regTools.regTools(parent=self)

    # The VOI extraction widget
    self.VOITools = VOITools.VOITools(parent=self)

    # Arranges the objects in a layout
    self.mainWidget = QtGui.QWidget()
    self.layout = QtGui.QHBoxLayout()
    self.vtklayout = QtGui.QVBoxLayout()
    self.vtklayout.addWidget(self.vtkView)
    self.vtklayout.addWidget(self.vtkView2)
    self.vtklayout.setContentsMargins(0, 0, 5, 0)
    self.splitterRightSide.setLayout(self.vtklayout)
    self.layout.addWidget(self.splitter)

    self.layout.setContentsMargins(0, 0, 0, 0)
    self.mainWidget.setLayout(self.layout)
    self.setCentralWidget(self.mainWidget)

    # Makes the "custom" dock area for VOI panels
    self.VOIAdjust = QtGui.QDockWidget()
    self.VOIAdjust.setWindowTitle("VOI Adjustment")
    self.VOIPanelDockArea = QtGui.QMainWindow()
    self.VOIAdjust.setWidget(self.VOIPanelDockArea)

    # Adds the dockable widgets
    self.setDockOptions(QtGui.QMainWindow.ForceTabbedDocks)
    self.update()
    self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.regTools)
    self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.VOITools)
    self.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.VOIAdjust)
    self.regTools.raise_()
    self.VOIPanelDockArea.setDockOptions(QtGui.QMainWindow.AllowNestedDocks)

    self.tabifyDockWidget(self.VOIAdjust, self.VOITools)
    self.tabifyDockWidget(self.VOITools, self.regTools)

    # Starts the rendering
    self.vtkView.start()
    self.vtkView2.start()

def makeProjectToolbar(self):
    self.projectToolBar = QtGui.QToolBar()

    self.addBrainAction = QtGui.QAction('Add New Brain', self)
    self.addBrainAction.setIcon(utils.createTextIcon(""))
    self.addBrainAction.setCheckable(False)
    self.addBrainAction.setShortcut('Ctrl+B')
    self.addBrainAction.setStatusTip('Add a new brain to the current project')
    self.addBrainAction.triggered.connect(self.addBrain)
    self.projectToolBar.addAction(self.addBrainAction)

    self.addTrialAction = QtGui.QAction('Add New Trial', self)
    self.addTrialAction.setIcon(utils.createTextIcon(""))
    self.addTrialAction.setCheckable(False)
    self.addTrialAction.setShortcut('Ctrl+T')
    self.addTrialAction.setStatusTip('Add a new trial to the current brain (Shift+Click to add high-resolution scan)')
    self.addTrialAction.triggered.connect(self.addTrial)
    self.projectToolBar.addAction(self.addTrialAction)

    c = self.projectToolBar.children()
    self.addBrainButton = c[3]
    self.addTrialButton = c[4]
    c[3].setObjectName('addBrain')
    c[4].setObjectName('addTrial')

    self.projectToolBar.setStyleSheet("""
                                        QToolButton {width: 16px; height: 16px;
                                        background-repeat: None;
                                        background-position: center;
                                        background-color: #6CF;
                                        border: 1px solid #24F; border-radius: 2px;}

                                        QToolButton#addBrain {width: 16px; height: 16px;
                                        image: url('res/icons/newBrain_16x16-01.png');}

                                        QToolButton#addTrial {width: 16px; height: 16px;
                                        image: url('res/icons/newTrial2_16x16-01.png');}

                                        QToolButton::hover {background: #CCC;}
                                        QToolButton::pressed {background: #ACF; border: 1px solid #ACF; border-radius: 2px;}
                                        """)

