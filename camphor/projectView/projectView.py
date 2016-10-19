from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
import os
import numpy

## Some constants
BRAIN_ITEM_TYPE = QtGui.QStandardItem.UserType+1
TRIAL_ITEM_TYPE = QtGui.QStandardItem.UserType+2
HIGHRESSCAN_ITEM_TYPE = QtGui.QStandardItem.UserType+3
TRANSFORM_ITEM_TYPE = QtGui.QStandardItem.UserType+4
DESC_ITEM_TYPE = QtGui.QStandardItem.UserType+5

class projectView(QtGui.QTreeView):
    """
    This class implements the tree view for a project

    The view displays a camphor.projectView.project object passed using the setProject() function

    """

    def __init__(self, parent):
        super(projectView, self).__init__(parent)

        # Creates a dummy model
        # This will be constructed using the setProject() function
        self.camphor = parent

        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Object', 'Information'])
        self.setModel(self.model)
        self.setColumnWidth(0, 150)

        # To accelerate rendering, gives a hint to the QTreeView object
        self.setUniformRowHeights(True)

        # On double-clicking an item, call this function
        self.doubleClicked.connect(self.doubleClick_callback)

        # On clicking an item, call this function
        self.clicked.connect(self.click_callback)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # For the context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def setProject(self, project):
        """
        This function sets the specified project data

        :param proj: a camphor.projectView.project item containing the data for the project to be displayed
        :return:
        """

        # Reinitializes the model

        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Object', 'Information'])
        self.setModel(self.model)

        # Constructs the model
        for i in range(project.nBrains):
            self.appendBrain(project.brain[i])
            for j in range(project.brain[i].nTrials):
                self.appendTrial(trial=project.brain[i].trial[j])

            if project.brain[i].highResScan is not None:
                self.appendHighResScan(highResScan=project.brain[i].highResScan)


    def appendBrain(self, brain):
        item = brainItem("Brain {:d}".format(brain.index + 1), brainIndex=brain.index)
        self.model.appendRow(item)
        index = self.model.indexFromItem(item)
        self.expand(index)

    def appendTrial(self, trial):
        tItem = trialItem(trial.name, brainIndex=trial.brainIndex, trialIndex=trial.index)
        for k in trial.transforms:
            tItem.appendRow(transformItem(k, brainIndex=trial.brainIndex, trialIndex=trial.index))
        brainItem = self.model.item(trial.brainIndex)
        brainItem.appendRow(tItem)

    def appendHighResScan(self, highResScan):
        tItem = highResScanItem(highResScan.name, brainIndex=highResScan.brainIndex)
        for k in highResScan.transforms:
            tItem.appendRow(transformItem(k, brainIndex=highResScan.brainIndex, trialIndex=-1))
        brainItem = self.model.item(highResScan.brainIndex)
        brainItem.appendRow(tItem)

    def updateSelf(self):
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def doubleClick_callback(self, index):
        """
        This function loads and displays the data when user double-clicks on a trial item
        """

        # Retrieves the clicked tree item
        item = self.model.itemFromIndex(index)

        # Takes appropriate action
        if item.column() == 0 and item.type() == TRIAL_ITEM_TYPE:
            # The item is a trial item => load the data in camphor
            brain = item.brain
            self.camphor.openFileFromProject(brain=item.brain, trial=item.trial, view=1)
        elif item.column() == 0 and item.type() == HIGHRESSCAN_ITEM_TYPE:
            # The item is a trial item => load the data in camphor
            brain = item.brain
            self.camphor.openFileFromProject(brain=item.brain, trial=-1, view=1)

    def click_callback(self, index):
        """
            This function toggles the active/inactive state for checkable filters
        """
        # Retrieves the clicked tree item
        item = self.model.itemFromIndex(index)

        # Takes appropriate action
        if item.column() == 0 and item.type() == TRANSFORM_ITEM_TYPE:
            # The item is a filter item => check the state
            item.transform.active = (item.checkState()>0)

    def contextMenu(self, position):
        index = self.selectedIndexes()
        if len(index) > 0:

            # Checks that all items are trials
            item = [self.model.itemFromIndex(i) for i in index]
            column = [i.column() for i in item]
            type = [i.type() for i in item]

            # Checks if selected items are all trials
            if all(numpy.array(column) == 0) and all(numpy.array(type) == TRIAL_ITEM_TYPE):
                brain = [i.brain for i in item]
                trial = [i.trial for i in item]
                menu = allItemsContextMenu(self, brain, trial)
                menu.exec_(self.viewport().mapToGlobal(position))

            if len(item) == 1 and numpy.array(column) == 0 and numpy.array(type) == HIGHRESSCAN_ITEM_TYPE:
                brain = item[0].brain
                menu = HRSContextMenu(self, brain)
                menu.exec_(self.viewport().mapToGlobal(position))

    def getCurrentTrial(self):
        """
        getCurrentTrial()

        Returns the currently selected brain and trial numbers
        If there are multiple selected items, returns data for the first item only
        If there are no items selected, returns (0,0)

        :return: a (brain number, trial number) list
        """

        index = self.selectedIndexes()
        if len(index) > 0:
            item = self.model.itemFromIndex(index[0])
            return (item.brain, item.trial)
        else:
            return (0,0)

    def getCurrentBrain(self):
        """
        Returns the index of the currently selected brain
        If there are multiple selected items, returns data for the first item only
        If there are no items selected, returns 0

        :return: the index of the currently selected brain as int
        """

        index = self.selectedIndexes()
        if len(index) > 0:
            item = self.model.itemFromIndex(index[0])
            return item.brain
        else:
            return 0

class allItemsContextMenu(QtGui.QMenu):
    def __init__(self, treeview, brain, trial):
        super(allItemsContextMenu, self).__init__()

        self.loadInView1 = QtGui.QAction('Load in view 1', self)
        self.loadInView1.setStatusTip('Load selected trial in VTK view #1')
        self.loadInView1.triggered.connect(
            lambda x: treeview.camphor.openFileFromProject(brain=brain[0], trial=trial[0], view=1))

        self.loadInView2 = QtGui.QAction('Load in view 2', self)
        self.loadInView2.setStatusTip('Load selected trial in VTK view #2')
        self.loadInView2.triggered.connect(
            lambda x: treeview.camphor.openFileFromProject(brain=brain[0], trial=trial[0], view=2))

        self.showDiff = QtGui.QMenu('Show diff')
        self.showDiff.setStatusTip('Displays the difference of the two selected trials')
        self.showDiffAction1 = QtGui.QAction('In view 1', self)
        self.showDiffAction2 = QtGui.QAction('In view 2', self)
        self.showDiffAction1.triggered.connect(lambda x: treeview.camphor.showDiff(brain, trial, view=1))
        self.showDiffAction2.triggered.connect(lambda x: treeview.camphor.showDiff(brain, trial, view=2))
        self.showDiff.addAction(self.showDiffAction1)
        self.showDiff.addAction(self.showDiffAction2)

        self.showtDiff = QtGui.QMenu('Show tdiff')
        self.showtDiff.setStatusTip('Displays the temporal difference of the selected trial')
        self.showtDiffAction1 = QtGui.QAction('In view 1', self)
        self.showtDiffAction2 = QtGui.QAction('In view 2', self)
        self.showtDiffAction1.triggered.connect(lambda x: treeview.camphor.showtDiff(brain, trial, view=1))
        self.showtDiffAction2.triggered.connect(lambda x: treeview.camphor.showtDiff(brain, trial, view=2))
        self.showtDiff.addAction(self.showtDiffAction1)
        self.showtDiff.addAction(self.showtDiffAction2)

        self.overlay = QtGui.QMenu('Overlay')
        self.overlay.setStatusTip('Overlays the selected trials in the specified view')
        self.overlayAction1 = QtGui.QAction('In view 1', self)
        self.overlayAction2 = QtGui.QAction('In view 2', self)
        self.overlayAction1.triggered.connect(lambda x: treeview.camphor.overlay(brain, trial, view=1))
        self.overlayAction2.triggered.connect(lambda x: treeview.camphor.overlay(brain, trial, view=2))
        self.overlay.addAction(self.overlayAction1)
        self.overlay.addAction(self.overlayAction2)

        self.overlayHRS= QtGui.QMenu('Overlay with high-res scan')
        self.overlayHRS.setStatusTip('Overlays the selected trials with the high-resolution scan in the specified view')
        self.overlayHRSAction1 = QtGui.QAction('In view 1', self)
        self.overlayHRSAction2 = QtGui.QAction('In view 2', self)
        self.overlayHRSAction1.triggered.connect(lambda x: treeview.camphor.overlayHRS(brain, trial, view=1))
        self.overlayHRSAction2.triggered.connect(lambda x: treeview.camphor.overlayHRS(brain, trial, view=2))
        self.overlayHRS.addAction(self.overlayHRSAction1)
        self.overlayHRS.addAction(self.overlayHRSAction2)

        self.eraseTrial = QtGui.QAction('Erase selected trial(s)', self)
        self.eraseTrial.setStatusTip('Erase selected trial(s)')
        self.eraseTrial.triggered.connect(lambda x: treeview.camphor.eraseTrials(brain,trial))

        if(len(brain)==1):
            self.addAction(self.loadInView1)
            self.addAction(self.loadInView2)
            self.addMenu(self.showtDiff)
            self.addMenu(self.overlayHRS)
        elif(len(brain)==2):
            self.addMenu(self.showDiff)
            self.addMenu(self.overlay)

        self.addSeparator()
        self.addAction(self.eraseTrial)

class HRSContextMenu(QtGui.QMenu):
    def __init__(self, treeview, brain):
        super(HRSContextMenu, self).__init__()

        self.loadInView1 = QtGui.QAction('Load in view 1', self)
        self.loadInView1.setStatusTip('Load in VTK view #1')
        self.loadInView1.triggered.connect(
            lambda x: treeview.camphor.openFileFromProject(brain=brain, trial=-1, view=1))

        self.loadInView2 = QtGui.QAction('Load in view 2', self)
        self.loadInView2.setStatusTip('Load in VTK view #2')
        self.loadInView2.triggered.connect(
            lambda x: treeview.camphor.openFileFromProject(brain=brain, trial=-1, view=2))


        self.eraseTrial = QtGui.QAction('Remove from project', self)
        self.eraseTrial.setStatusTip('Remove from project')
        self.eraseTrial.triggered.connect(lambda x: treeview.camphor.eraseTrials(brain, -1))


        self.addAction(self.loadInView1)
        self.addAction(self.loadInView2)
        self.addSeparator()
        self.addAction(self.eraseTrial)
            


class brainItem(QtGui.QStandardItem):
    """
    class projectView.brainItem

    Tree item template for brain
    """

    def __init__(self, name, brainIndex):
        super(brainItem, self).__init__(name)
        self.setEditable(False)
        self.brain = brainIndex

    def flags(self):
        # flags don't seem to do anything
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return BRAIN_ITEM_TYPE

class trialItem(QtGui.QStandardItem):
    """
    class projectView.trialItem

    Tree item template for imaging trials
    """
    def __init__(self, name, brainIndex, trialIndex):
        super(trialItem, self).__init__(name)
        self.setEditable(False)
        self.brain = brainIndex
        self.trial = trialIndex

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return TRIAL_ITEM_TYPE

class highResScanItem(QtGui.QStandardItem):
    """
    class projectView.trialItem

    Tree item template for imaging trials
    """
    def __init__(self, name, brainIndex):
        super(highResScanItem, self).__init__(name)
        self.setEditable(False)
        self.brain = brainIndex
        self.    setIcon(QtGui.QIcon('res/icons/highResScan_12x12-01.png'))

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return HIGHRESSCAN_ITEM_TYPE

class transformItem(QtGui.QStandardItem):
    """
    class projectView.trialItem

    Tree item template for imaging trials
    """
    def __init__(self, transform, brainIndex, trialIndex):
        super(transformItem, self).__init__(transform.name)
        self.setEditable(False)
        self.setCheckable(True)
        self.setCheckState(Qt.Checked)
        self.brain = brainIndex
        self.trial = trialIndex
        self.transform = transform

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return TRANSFORM_ITEM_TYPE

class descItem(QtGui.QStandardItem):
    """
    class projectView.descItem

    Tree item template for the description of brains and imaging trials
    """

    def __init__(self, name, parent):
        super(trialItem, self).__init__(name, parent=parent)
        self.setEditable(False)

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def type(self):
        return DESC_ITEM_TYPE

#####################################################################################################
#####################################################################################################
#####################################################################################################

class projectModel(QtCore.QAbstractItemModel):
    """
    This class (deriving from QtCore.QAbstractItemModel) was considered to implement a more customized model/view framework, but not pursued very long
    """
    def __init__(self):
        super(projectView, self).__init__()

    def rowCount(self,index):
        if index.isValid():
            return index.internalPointer().childCount()
        return self._root.childCount()


    def columnCount(self, index):
        return 1


#### TEST CLASS ####
# Obsolete because the project class has been moved to a new package camphor.camphorProject
class test(QtGui.QMainWindow):

    def __init__(self):
        super(test, self).__init__()

        print('initializing...')

        p = project()
        p.brain.append(brainData())
        p.nBrains = 1
        p.brain[0].index = 1
        p.brain[0].nTrials = 1
        p.brain[0].trial.append(trialData(dataFile='test',name='Trial1',stimulusID=0))

        self.view = projectView()
        self.view.setProject(p)

        self.setGeometry(200, 200, 700, 500)
        self.setWindowTitle("test of projectView")
        self.show()

        self.mainWidget = QtGui.QWidget()
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.view)
        self.mainWidget.setLayout(self.layout)
        self.setCentralWidget(self.mainWidget)

def main():
    app = QtGui.QApplication(sys.argv)
    ex = test()
    sys.exit(app.exec_())

if __name__ == '__main__':
    print("main!!!")
    main()