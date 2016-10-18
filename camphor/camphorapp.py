import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from camphor import utils, guiLayout
import camphor.DataIO as DataIO
from camphor.camphorProject import camphorProject
import os
import datetime
import numpy

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
        guiLayout.makeLayout(self)

        # Displays ready in the status ar
        self.Output('Ready.',2000)

    def openFile(self, dub=None, file=None, view=0, transforms=()):
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
                self.dataLoaded = True
                self.fileName = fname
            elif view==1:
                self.rawData1 = DataIO.LSMLoad(fname)
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

        dataFile = self.project.brain[brain].trial[trial].dataFile
        transforms = self.project.brain[brain].trial[trial].transforms
        trialName = self.project.brain[brain].trial[trial].name
        self.Output("Loading {:s}".format(trialName))

        self.openFile(file=dataFile, transforms=transforms, view=view)
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
        camphor.addTrial()

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


##################################
#########       main () ##########
##################################

def main():
    app = QtGui.QApplication(sys.argv)
    ex = camphor()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


