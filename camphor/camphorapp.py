import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from camphor import utils, guiLayout
import camphor.DataIO as DataIO
from camphor.camphorProject import camphorProject
import os
import datetime
import numpy
import SimpleITK as sitk
from vtk import vtkObject

class camphor(QtGui.QMainWindow):
    """
    camphorapp.camphor

    This is the main CaMPhor application class.
    The class implements the GUI and its basic functionalities.
    """
    def __init__(self):
        super(camphor, self).__init__()
        self.initUI()
        self.dataLoaded = False
        self.dataLoaded2 = False
        self.fileName = ''
        self.fileName2 = ''
        self.project = camphorProject.camphorProject()
        self.pltdata1 = []
        self.pltdata2 = []
        self.VOIlist = []

        # (for developing phase) loads a default project at startup
        if ('STARTUPPROJECT' in self.ini):
            if os.path.exists(self.ini['STARTUPPROJECT']):
                self.loadProject(fileName=self.ini['STARTUPPROJECT'])
            else:
                print('Default startup project [{:s}] not found.'.format(self.ini['STARTUPPROJECT']))

    def initUI(self):
        # Here we create the GUI; the code is in a separate module
        vtkObject.GlobalWarningDisplayOff() # disables the VTK output window
        guiLayout.makeLayout(self)

        # Displays ready in the status ar
        self.Output('Ready.',2000)

    def openFile(self, dub=None, file=None, view=0, transforms=(), flip=False):
        """
        camphor.openFile()

        This function summons a file dialog and calls the LSMLoad() function from the dataIO module to load the LSM data
        :return:
        """

        if file is None:
            fname = os.path.normpath(QtGui.QFileDialog.getOpenFileName(self, 'Open file',
                                                  os.path.normpath(self.ini['LOADDIR']),'*.lsm;*.tif'))
        else:
            fname = file

        self.Output("Opening {:s}".format(fname))
        if fname != ".":
            if view==0:
                self.rawData = DataIO.LSMLoad(fname)
                if flip:
                    self.rawData = [self.rawData[i][::-1,:,:] for i in range(len(self.rawData))]
                self.dataLoaded = True
                self.fileName = fname
            elif view==1:
                self.rawData1 = DataIO.LSMLoad(fname)
                if flip:
                    self.rawData1 = [self.rawData1[i][::-1,:,:] for i in range(len(self.rawData1))]
                self.dataLoaded1 = True
                self.fileName = fname
                # Renders the loaded data in the VTK plugin
                self.vtkView.assignData(self.rawData1, transforms=transforms)

                # Adjusts the window's title
                if self.dataLoaded2:
                    self.setWindowTitle(
                        "{:s} - {:s} - {:s}".format(self.ini['APPNAME'], os.path.basename(self.fileName),
                                                    os.path.basename(self.fileName2)))
                else:
                    self.setWindowTitle("{:s} - {:s}".format(self.ini['APPNAME'], os.path.basename(self.fileName)))
            elif view==2:
                self.rawData2 = DataIO.LSMLoad(fname)
                if flip:
                    self.rawData2 = [self.rawData2[i][::-1,:,:] for i in range(len(self.rawData2))]
                self.dataLoaded2 = True
                self.fileName2 = fname

                # Renders the loaded data in the VTK plugin
                self.vtkView2.assignData(self.rawData2, transforms=transforms)

                # Adjusts the window's title
                if self.dataLoaded:
                    self.setWindowTitle(
                        "{:s} - {:s} - {:s}".format(self.ini['APPNAME'], os.path.basename(self.fileName),
                                                    os.path.basename(self.fileName2)))
                else:
                    self.setWindowTitle("{:s} - {:s}".format(self.ini['APPNAME'], os.path.basename(self.fileName2)))
            else:
                print("Error: view {:d} requested".format(view))

    def openFile1(self, dub=None, file=None, transforms=()):
        self.openFile(file=file,view=1, transforms=transforms)

    def openFile2(self, dub=None, file=None, transforms=()):
        self.openFile(file=file, view=2, transforms=transforms)

    def openFileFromProject(self, dub=None, brain=None, trial=None, view=1):
        """
        camphor.openFileFromProject

        opens a data file from the current project, specified by the brain and trial indexes, in the specified view

        :return:
        """

        if brain is None:
            return

        if trial==-1:
            # This points to the high-resolution scan
            dataFile = self.project.brain[brain].highResScan.dataFile
            transforms = self.project.brain[brain].highResScan.transforms
            trialName = self.project.brain[brain].highResScan.name
        else:
            dataFile = self.project.brain[brain].trial[trial].dataFile
            transforms = self.project.brain[brain].trial[trial].transforms
            trialName = self.project.brain[brain].trial[trial].name

        self.Output("Loading {:s}".format(trialName))

        self.openFile(file=dataFile, transforms=transforms, view=view, flip=(trial==-1))
        if view==1:
            self.vtkView.trialLabel.setText('Brain {:d}/{:s}'.format(brain,trialName))
        elif view==2:
            self.vtkView2.trialLabel.setText('Brain {:d}/{:s}'.format(brain, trialName))

    def Output(self, text, timeout=0):
        """
        camphor.Output(self, text, timeout=0):

        This function directs output messages to the statusbar
        Overloaded from CaMPhor_DataIO
        """
        self.statusBar.showMessage(text, timeout)

    def addBrain(self):
        """
        camphor.addBrain()

        This function summons a directory selection dialog and adds the contents of the directory to the project as a new brain
        :return:
        """

        dname = QtGui.QFileDialog.getExistingDirectory(None,
                                                       "Select a Directory holding Brain Data,",
                                                       os.path.normpath(self.ini['LOADDIR']),
                                                       QtGui.QFileDialog.ShowDirsOnly)

        if dname != "":
            # First we append a brain to the project)
            self.project.appendBrain(directory=dname)

            # Then we append all the .lsm files for which a .info file exists
            for file in [f for f in os.listdir(dname) if (f.endswith('.lsm') or f.endswith('.tif'))]:
                dataFile = os.path.join(dname,file)
                self.Output('Reading info for file {:s}...'.format(file),2)
                if file.endswith('.lsm'):
                    info = utils.LSMInfo(dataFile)
                else:
                    info = ''
                self.project.appendTrialToLastBrain(info=info,
                                                    dataFile=dataFile)

                # Updates the application so that it doesn't freeze
                QtCore.QCoreApplication.processEvents()

            self.projectView.setProject(self.project)

    def addTrial(self, more):
        """
        camphor.addTrial()

        This function summons an open file dialog and adds the selected file as a new trial to the current brain

        :return: nothing
        """

        # If the user shift-clicked, we will display a dialog requesting the high-resolution scan
        HRS = QtGui.QApplication.queryKeyboardModifiers().__int__() == QtCore.Qt.SHIFT
        print(HRS)

        # Get the currently selected brain

        brain = self.projectView.getCurrentBrain()
        dir = self.project.brain[brain].directory

        if HRS:
            dialogText = 'Open High-Resolution Scan'
        else:
            dialogText = 'Open Trial Image'

        fname = os.path.normpath(QtGui.QFileDialog.getOpenFileName(self, dialogText,
                                                               os.path.normpath(dir),
                                                               '*.lsm;*.tif'))

        if fname != ".":
            dataFile = os.path.join(dir, fname)
            if fname.endswith('.lsm'):
                info = utils.LSMInfo(fname)
            else:
                info = ''

            if HRS:
                self.project.addHighResScan(brainIndex=brain, info=info, dataFile=dataFile, name='High-Resolution Scan')
            else:
                self.project.appendTrial(brainIndex=brain, info=info, dataFile=dataFile)

            # Updates the application so that it doesn't freeze
            QtCore.QCoreApplication.processEvents()

            self.projectView.setProject(self.project)

    def eraseTrials(self, brain, trial):
        if trial==-1:
            # This means remove the high-resolution scan
            self.project.brain[brain].highResScan = None
            self.projectView.setProject(self.project)
        else:
            self.project.eraseTrials(brain,trial)
            self.projectView.setProject(self.project)

    def saveProject(self, dub=None, fileName=None):
        if fileName is None:
            fileName = os.path.normpath(QtGui.QFileDialog.getSaveFileName(self, 'Save project',
                                                  os.path.normpath(self.ini['SAVEDIR']),'*.cph'))

        if fileName != "":
            DataIO.saveProject(fileName=fileName, camphor=self)

    def loadProject(self, dub=None, fileName=None):
        if fileName is None:
            fileName = os.path.normpath(QtGui.QFileDialog.getOpenFileName(self, 'Load project',
                                                  os.path.normpath(self.ini['SAVEDIR']),'*.cph'))

        if fileName != ".":
            self.project = DataIO.loadProject(fileName=fileName, camphor=self)
            self.projectView.setProject(self.project)

    def registerToMeanBaseline(self, brain, trial):
        print('brain=' + str(brain))
        print('trial=' + str(trial))

    def updateProjectView(self):
        self.projectView.setProject(self.project)

    def showDiff(self, brain, trial, view=1):
        if view==1:
            fun = self.vtkView.showDiff
        elif view==2:
            fun = self.vtkView2.showDiff
        else:
            fun = self.vtkView.showDiff

        data1 = DataIO.LSMLoad(self.project.brain[brain[0]].trial[trial[0]].dataFile)
        data2 = DataIO.LSMLoad(self.project.brain[brain[1]].trial[trial[1]].dataFile)
        transforms1 = self.project.brain[brain[0]].trial[trial[0]].transforms
        transforms2 = self.project.brain[brain[1]].trial[trial[1]].transforms
        fun(data1=data1,transforms1=transforms1, data2=data2,transforms2=transforms2)

    def showtDiff(self, brain, trial, view=1):
        if view==1:
            fun = self.vtkView.showtDiff
        elif view==2:
            fun = self.vtkView2.showtDiff
        else:
            fun = self.vtkView.showtDiff

        data = DataIO.LSMLoad(self.project.brain[brain[0]].trial[trial[0]].dataFile)
        transforms = self.project.brain[brain[0]].trial[trial[0]].transforms
        fun(data=data,transforms=transforms)

    def overlay(self, brain, trial, view=1):
        if view==1:
            fun = self.vtkView.overlay
        elif view==2:
            fun = self.vtkView2.overlay
        else:
            fun = self.vtkView.overlay

        data1 = DataIO.LSMLoad(self.project.brain[brain[0]].trial[trial[0]].dataFile)
        data2 = DataIO.LSMLoad(self.project.brain[brain[1]].trial[trial[1]].dataFile)
        transforms1 = self.project.brain[brain[0]].trial[trial[0]].transforms
        transforms2 = self.project.brain[brain[1]].trial[trial[1]].transforms
        fun(data1=data1,transforms1=transforms1,data2=data2,transforms2=transforms2)

    def overlayHRS(self, brain, trial, view=1):
        if view==1:
            fun = self.vtkView.overlay
        elif view==2:
            fun = self.vtkView2.overlay
        else:
            fun = self.vtkView.overlay

        brain = brain[0]
        trial = trial[0]
        data1 = DataIO.LSMLoad(self.project.brain[brain].trial[trial].dataFile)
        data2 = DataIO.LSMLoad(self.project.brain[brain].highResScan.dataFile)
        data2 = [data2[0][::-1,:,:].copy(order='C') for i in range(len(data1))]
        data1 = [self.resampleData(data1[i], data2[i], data2[i].shape) for i in range(len(data1))]

        transforms1 = self.project.brain[brain].trial[trial].transforms
        transforms2 = self.project.brain[brain].highResScan.transforms
        fun(data1=data1,transforms1=transforms1,data2=data2,transforms2=transforms2, colormap='OverlayHRS')

    def saveRegistered(self):
        for brain in range(self.project.nBrains):
            # Checks if directory exists
            regDir = os.path.join(self.project.brain[brain].directory,'.registered' + datetime.date.today().isoformat())
            if not os.path.exists(regDir):
                os.mkdir(regDir)

            for trial in range(self.project.brain[brain].nTrials):
                self.openFileFromProject(brain=brain,trial=trial,view=0)
                d = numpy.copy(self.rawData,order='C')
                for t in self.project.brain[brain].trial[trial].transforms:
                    if t.active:
                        d = t.apply(d)

                tname = self.project.brain[brain].trial[trial].name
                tnamesplit = os.path.splitext(tname)
                newname = tnamesplit[0] + '.registered.tif'
                newpath = os.path.join(regDir,newname)
                DataIO.saveImageSeries(d,newpath)

    def saveRegisteredHRS(self):
        for brain in range(self.project.nBrains):
            # Checks if directory exists
            regDir = os.path.join(self.project.brain[brain].directory,'.registered' + datetime.date.today().isoformat())
            if not os.path.exists(regDir):
                os.mkdir(regDir)
            regDir = os.path.join(self.project.brain[brain].directory,
                                  '.registered' + datetime.date.today().isoformat(),'highresScan')
            if not os.path.exists(regDir):
                os.mkdir(regDir)

            if self.project.brain[brain].highResScan is not None:
                self.openFileFromProject(brain=brain,trial=-1,view=0)
                d = numpy.copy(self.rawData,order='C')
                for t in self.project.brain[brain].highResScan.transforms:
                    if t.active:
                        d = t.apply(d)

                tname = self.project.brain[brain].highResScan.name
                tnamesplit = os.path.splitext(tname)
                newname = tnamesplit[0] + '.registered.tif'
                newpath = os.path.join(regDir,newname)
                DataIO.saveImageSeries(d,newpath)

    def resampleData(self, data, template, size):
        dataType = data.dtype
        fixed_image = sitk.GetImageFromArray(data.astype(numpy.double))
        moving_image = sitk.GetImageFromArray(template.astype(numpy.double))

        lxf, lyf, lzf = fixed_image.GetSize()
        lxm, lym, lzm = moving_image.GetSize()
        fixed_image.SetSpacing((lxm / lxf, lym / lyf, lzm / lzf))

        # First we need to resample the template to match the dimensions of the data
        resampled_template = sitk.Image(moving_image.GetSize(), moving_image.GetPixelIDValue())
        resampled_template.SetSpacing((1, 1, 1))
        resampled_template.SetOrigin(moving_image.GetOrigin())
        resampled_template.SetDirection(moving_image.GetDirection())

        # Resample original image using identity transform and the BSpline interpolator.
        resample = sitk.ResampleImageFilter()
        resample.SetReferenceImage(resampled_template)
        resample.SetInterpolator(sitk.sitkLinear)
        resample.SetTransform(sitk.Transform())
        resampled_template = resample.Execute(fixed_image)
        return sitk.GetArrayFromImage(resampled_template).astype(dataType)

    def overlayVOIHRS(self, brain, trial, view):
        """
        camphorapp.overlayVOIHRS(brain, trial, view)
        This function overlays the VOIs of a single target trial on top of the high-resolution scan
        If the filter that has been used to extract the VOIs (the VOIfilter object of the target trialData object)
        allows for a control widget, this also spawns the control widget and passes it to vtkView so that it
        can be destroyed when new data is created

        :param brain: brain index of the target trial (as list)
        :param trial:  trial index of the target trial (as list)
        :param view: index of the vtkView in which to display the data
        :return: nothing
        """

        brain = brain[0]
        trial = trial[0]

        f = self.project.brain[brain].trial[trial].VOIfilter()
        f._parameters = self.project.brain[brain].trial[trial].VOIfilterParams

        if view==1:
            fun = self.vtkView.overlayVOIHRS
            VOIpanel = self.vtkView.VOIpanel
        elif view==2:
            fun = self.vtkView2.overlayVOIHRS
            VOIpanel = self.vtkView2.VOIpanel
        else:
            fun = self.vtkView.overlayVOIHRS
            VOIpanel = self.vtkView.VOIpanel

        VOIdata = self.project.brain[brain].trial[trial].VOIdata.astype(numpy.uint8)
        VOIbase = self.project.brain[brain].trial[trial].VOIbase
        HRSdata = DataIO.LSMLoad(self.project.brain[brain].highResScan.dataFile)
        HRSdata = [HRSdata[0][::-1, :, :].copy(order='C')]
        VOIdata = [self.resampleData(VOIdata, HRSdata[0], HRSdata[0].shape)]
        VOIbase = self.resampleData(VOIbase, HRSdata[0], HRSdata[0].shape)

        HRStransforms = self.project.brain[brain].highResScan.transforms
        fun(data2=VOIdata, data1=HRSdata, transforms1=HRStransforms, colormap='Standard')

        VOIpanel = f.controlWidget(self.vtkView, VOIbase, VOIdata[0], message='- View {:d}'.format(view))
        if view==1:
            self.vtkView.VOIpanel= VOIpanel
        elif view==2:
            self.vtkView2.VOIpanel = VOIpanel
        else:
            self.vtkView.VOIpanel = VOIpanel

    def overlayVOIs(self, brain, trial, view):
        """
        camphorapp.overlayVOIs(brain, trial, view)
        This function overlays the VOIs of a any number of target trials in the specified view
        If the filter that has been used to extract the VOIs (the VOIfilter object of the target trialData object)
        allows for a control widget, this also spawns the control widget and passes it to vtkView so that it
        can be destroyed when new data is created

        :param brain: brain index of the target trial (as list)
        :param trial:  trial index of the target trial (as list)
        :param view: index of the vtkView in which to display the data
        :return: nothing
        """

        f = [self.project.brain[i].trial[j].VOIfilter() for i,j in zip(brain,trial)]
        for i in range(len(f)):
            f[i]._parameters = self.project.brain[brain[i]].trial[trial[i]].VOIfilterParams

        if view == 1:
            fun = self.vtkView.overlayVOIs
            VOIpanel = self.vtkView.VOIpanel
        elif view == 2:
            fun = self.vtkView2.overlayVOIs
            VOIpanel = self.vtkView2.VOIpanel
        else:
            fun = self.vtkView.overlayVOIs
            VOIpanel = self.vtkView.VOIpanel


        VOIdata = [self.project.brain[i].trial[j].VOIdata.astype(numpy.uint8) for i,j, in zip(brain,trial)]
        VOIbase = [self.project.brain[i].trial[j].VOIbase for i,j, in zip(brain,trial)]

        # fun(data1=[VOIdata[0]], data2=[VOIdata[1]], colormap='Overlay')
        fun(data=VOIdata)

        VOIpanel = [f[i].controlWidget(self.vtkView, VOIbase[i], VOIdata[i],
                                    message='- View {:d} - brain{:d}/trial{:d}'.format(view, brain[i],trial[i])) for i in range(len(VOIdata))]
        if view == 1:
            self.vtkView.VOIpanel = VOIpanel
        elif view == 2:
            self.vtkView2.VOIpanel = VOIpanel
        else:
            self.vtkView.VOIpanel = VOIpanel

##################################
#########       main () ##########
##################################

def main():
    app = QtGui.QApplication(sys.argv)
    ex = camphor()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


