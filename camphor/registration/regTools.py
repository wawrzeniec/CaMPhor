from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
import os
import importlib
from functools import partial

class regTools(QtGui.QDockWidget):
    """
    This class implements the registration tools widget
    """
    def __init__(self, parent):
        super(regTools,self).__init__(parent=parent)
        self.camphor = parent
        self.currentFilter = 0
        self.activeFilter = None
        self.activeFilterName = None
        self.iniUI()


    def iniUI(self):
        self.setWindowTitle('Registration Tools')

        self.filterLabel = QtGui.QLabel()
        self.filterLabel.setText('Method:')

        self.filterDropBox = QtGui.QComboBox()
        # dynamically lists the available registration filters
        self.filterNames = [os.path.splitext(f)[0] for f in os.listdir('camphor/registration/filters') if f.endswith('.py')]
        self.filterDropBox.addItems(self.filterNames)
        self.filterDropBox.currentIndexChanged.connect(self.newParamLayout)

        # also imports all the packages
        self.filtermod = [importlib.import_module('camphor.registration.filters.' + f) for f in self.filterNames]
        self.filters = [mod.filter() for mod in self.filtermod]

        self.methodLayout = QtGui.QFormLayout()
        self.methodLayout.setContentsMargins(5, 5, 5, 5)
        self.methodLayout.addRow(self.filterLabel, self.filterDropBox)

        self.paramFrame = QtGui.QGroupBox('Parameters')
        self.paramLayout = self.makeParamLayout(self.filters[0])
        self.paramFrame.setLayout(self.paramLayout)
        self.paramFrame.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)

        # The "register" button
        self.registerButton = QtGui.QPushButton('Register')
        self.registerButton.clicked.connect(self.doRegistration)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addLayout(self.methodLayout)
        self.layout.addWidget(self.paramFrame)
        self.layout.addStretch(1)
        self.layout.addWidget(self.registerButton)
        self.layout.setAlignment(Qt.AlignTop)
        self.widget = QtGui.QWidget()
        self.widget.setLayout(self.layout)

        self.setWidget(self.widget)

    def doRegistration(self):

        # Finds the selected filter
        sel = self.filterDropBox.currentIndex()
        self.currentfilter = sel

        # Tags the filter as active
        self.activeFilter = self.filters[sel]
        self.activeFilterName = self.filterNames[sel]

        # Creates a progress dialog
        try:
            with regProgress(parent=self) as pdialog:
                # Here we connect the filter to our display
                self.filters[sel].setUpdateEvent(pdialog.updateProgress)
                # self.filters[sel].setUpdateEvent(self.updateEvent)
                pdialog.show()

                # Execute the filter
                self.activeFilter.execute(camphor=self.camphor)
        except Exception:
            pdialog.setLabelText('ERROR DURING REGISTRATION!')
            raise

        # Tags the filter as inactive once finished
        self.activeFilter = None
        self.activeFilterName = None

        # Updates the project view
        self.camphor.updateProjectView()

    def updateEvent(self):
        progress = self.activeFilter.getProgress()
        print("[{:2g}%] Value={:g}".format(progress.percentDone, progress.objectiveFunctionValue))


    def newParamLayout(self):
        index = self.filterDropBox.currentIndex()
        self.currentFilter = index
        self.paramLayout = self.makeParamLayout(self.filters[index])
        QtGui.QWidget().setLayout(self.paramFrame.layout())
        self.paramFrame.setLayout(self.paramLayout)

    def makeParamLayout(self, f):
        """
        Constructs the parameter edit zone for the specified filter (passed as a python module object)

        :param mod: python module object for the specified filter (the list of loaded filter modules is in regTools.filtermod)
        :return:
        """
        print('Creating layout with filter object {:d}'.format(id(f)))
        params = f.parameters.__dict__
        paramType = f.parameters._paramType
        paramLayout = QtGui.QFormLayout()
        for i, j in enumerate(params):
            if j is not '_paramType':
                if paramType[j][0] is 'double':
                    w = QtGui.QDoubleSpinBox()
                    w.setRange(paramType[j][1], paramType[j][2])
                    w.setSingleStep(paramType[j][3])
                    w.setValue(params[j])
                    w.valueChanged.connect(partial(self.setParamNumeric, j))
                    paramLayout.addRow(QtGui.QLabel(j), w)
                elif paramType[j][0] is 'doubleg':
                    w = QDoubleSpinBoxG()
                    w.setRange(paramType[j][1], paramType[j][2])
                    w.setSingleStep(paramType[j][3])
                    w.setValue(params[j])
                    w.valueChanged.connect(partial(self.setParamNumeric, j))
                    paramLayout.addRow(QtGui.QLabel(j), w)
                elif paramType[j][0] is 'int':
                    w = QtGui.QSpinBox()
                    w.setRange(paramType[j][1], paramType[j][2])
                    w.setSingleStep(paramType[j][3])
                    w.setValue(params[j])
                    w.valueChanged.connect(partial(self.setParamNumeric, j))
                    paramLayout.addRow(QtGui.QLabel(j), w)
                elif paramType[j][0] is 'list':
                    w = QtGui.QComboBox()
                    itemValue = paramType[j][1]
                    itemString = paramType[j][2]
                    for ii in range(len(itemString)):
                        w.addItem(itemString[ii], itemValue[ii])
                        if params[j] == itemValue[ii]:
                            w.setCurrentIndex(ii)
                    w.currentIndexChanged.connect(partial(self.setParamList, j, itemValue))
                    paramLayout.addRow(QtGui.QLabel(j), w)
                elif paramType[j] is 'fixed':
                    paramLayout.addRow(QtGui.QLabel(j), QtGui.QLabel(str(params[j])))
                else:
                    paramLayout.addRow(QtGui.QLabel(j), QtGui.QLabel(str(params[j])))

        return paramLayout


    def setParamNumeric(self, key, value):
        setattr(self.filters[self.currentFilter].parameters,key,value)

    def setParamList(self, key, valueList, value):
        print(value)
        setattr(self.filters[self.currentFilter].parameters,key,valueList[value])

class QDoubleSpinBoxG(QtGui.QDoubleSpinBox):
    def __init__(self, *args):
        QtGui.QDoubleSpinBox.__init__(self, *args)
        self.validator = QtGui.QDoubleValidator()
        self.lineEdit().setValidator(self.validator)
        self.setDecimals(10)

    def textFromValue(self, value):
        return '{:.6g}'.format(value)

    def valueFromText(self, text):
        return float(text)

    def setValue(self, value):
        QtGui.QDoubleSpinBox.setValue(self, value)

    def validate(self, value, position):
        return self.validator.validate(value, position)


class GValidator(QtGui.QValidator):
    def __init__(self, *args):
        QtGui.QValidator.__init__(self, *args)

    def validate(self, value, position):
        try:
            float(value)
            print('validated {:g}'.format(float(value)))
            return 2
        except:
            print('rejected {:s}'.format(value))
            return 0


class regProgress(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent=parent)

        self.parent = parent
        self.layout = QtGui.QVBoxLayout()
        self.label = QtGui.QLabel('Registering...')
        self.label.setAlignment(Qt.AlignHCenter)
        self.layout.addWidget(self.label)
        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMaximum(10000)
        self.progressBar.valueChanged.connect(lambda: self.progressBar.setFormat(
            '  {:.1f}%'.format(self.progressBar.value() / self.progressBar.maximum() * 100)))
        self.layout.addWidget(self.progressBar)
        self.progress = QtGui.QFormLayout()
        self.iterationNumber = QtGui.QLabel('0')
        self.objLabel = QtGui.QLabel('n/a')
        self.progressLabel = QtGui.QLabel('0%')
        self.progress.addRow(QtGui.QLabel('Iteration:'), self.iterationNumber)
        self.progress.addRow(QtGui.QLabel('Objective Function Value:'), self.objLabel)
        self.progress.addRow(QtGui.QLabel('Progress:'), self.progressLabel)
        self.layout.addLayout(self.progress)
        self.bottomLayout = QtGui.QHBoxLayout()
        self.bottomLayout.addStretch(1)
        self.cancelButton = QtGui.QPushButton('Cancel')
        self.bottomLayout.addWidget(self.cancelButton)
        self.layout.addLayout(self.bottomLayout)
        self.cancelButton.clicked.connect(self.cancel)

        self.setModal(True)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.setLayout(self.layout)
        self.setWindowTitle('Computing registration filter ({:s})'.format(self.parent.activeFilterName))

    def cancel(self):
        print('registration cancelled!')
        self.parent.activeFilter.cancelled = True
        self.cancelButton.setDisabled(True)

    def setLabelText(self, text):
        self.label.setText(text)

    def updateProgress(self):
        progress = self.parent.activeFilter.getProgress()
        self.iterationNumber.setText(str(progress.iteration))
        self.objLabel.setText('{:.4f}%'.format(progress.objectiveFunctionValue))
        self.progressLabel.setText('{:.1f}%'.format(progress.percentDone))
        if progress.totalPercentDone is not None:
            self.setValue(progress.totalPercentDone)
        # Updates the application so that it doesn't freeze
        QtCore.QCoreApplication.processEvents()

    def setValue(self, value):
        """
        Sets the progressbar value.
        Parameter value is givent in percent (0~100), but the progressBar's maximum value is 10000
        so that it will display fractional progress (hence, value is multiplied by 100 again)

        :param value: percentage of progress
        :return:
        """
        self.progressBar.setValue(100*value)

    def __enter__(self):
        self.oldmessage = self.parent.activeFilter.message
        self.parent.activeFilter.message = self.message
        return self

    def __exit__(self, type, value, traceback):
        self.parent.activeFilter.message = self.oldmessage
        self.cancelButton.setText('Done')
        self.cancelButton.clicked.disconnect(self.cancel)
        self.cancelButton.clicked.connect(self.close)
        self.cancelButton.setEnabled(True)

    def message(self, text, progress):
        self.setLabelText(text)
        self.setValue(progress)
        # Updates the application so that it doesn't freeze
        QtCore.QCoreApplication.processEvents()