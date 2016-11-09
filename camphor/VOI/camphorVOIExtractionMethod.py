"""
camphor.VOI.camphorVOiExtractionMethod

This is the abstract base class for implementing VOI extraction methods in CaMPhor

"""

from abc import ABC, abstractmethod, abstractproperty
from PyQt4 import QtGui, QtCore
from functools import partial

class camphorVOIExtractionMethod(ABC):
    def __init__(self):
        self._parameters = None
        self.updateEvent = self.updateProgress
        self.cancelled = False

    @abstractproperty
    def parameters(self):
        return self._parameters

    @parameters.setter
    def parameters(self, newparams):
        self._parameters = newparams

    @abstractmethod
    def execute(self, camphor):
        """
        camphorVOIExtractionMethod.execute(camphor)

        Executes the VOI extraction method using the current value of the parameters

        :param camphor:      The camphor instance, to get access to the data
        :return:
        """
        pass

    @abstractmethod
    def getProgress(self):
        """
        camphorVOIExtractionMethod.getProgress()

        This function returns the progress state of the VOI extraction algorithm currently being executed
        It is used to update the GUI display with information about the state of the algorithm

        :return: a camphorVOIExtractionProgress object
        """
        return camphorVOIExtractionProgress()

    def updateProgress(self):
        """
        camphorRegistrationMethod.updateProgress()

        This is the default function for updating the information about the state of the algorithm

        Each implementation of camphorVOIExtractionMethod should hook its algorithm to the updateEvent property of the object
        The client (the program that instantiates the VOI extraction method can then call setUpdateEvent() to the desired function
        This internally modifies the updateEvent property

        :return:
        """
        progress = self.getProgress()
        print("Percent done: {:g}".format(progress.percentDone))

    def setUpdateEvent(self, function):
        self.updateEvent = function

    def message(self, text, *args, **kwargs):
        print(text)

    def setMessage(self, targetFunc):
        self.message = targetFunc

    def controlWidget(self, camphor, baseData, VOIdata, message=None, dockArea=None):
        """
        VOIextractionMethod.controlWidget()

        method to spawn a control widget if the filter allows for modifying parameters
        (e.g., a threshold) post-hoc

        The current way this is implemented is that the method used the class instance's parameter property
        to recompute VOIs based on its baseData argument and stored the result in its VOIdata argument
        VOIData should be a reference to the array that is displayed in the vtkView instance, so that modifications
        to this object are reflected in the visual output.
        The method then calls vtkView.renderAll() to reflect the changes made

        Filter that implement this capability simply need to implement a _controls attribute in their parameters class

        :return: the QWidget object of the control panel
        """

        if not hasattr(self._parameters,'_controls'):
            return None
        
        def updateVOIs():
            self.updateVOIs(camphor, baseData, VOIdata)
            pass
        
        def setParamNumeric(key, value):
            setattr(self.parameters, key, value)

        def setParamList(key, valueList, value):
            setattr(self.parameters, key, valueList[value])

        controlPanelContainer = QtGui.QDockWidget(parent=None)
        controlPanel = QtGui.QWidget()
        controlPanel.setWindowFlags(QtCore.Qt.Tool)
        if message is None:
            panelTitle = "VOI Control Panel"
        else:
            panelTitle = "VOI Control Panel {:s}".format(message)
        controlPanel.setWindowTitle(panelTitle)
        controlPanelContainer.setWindowTitle(panelTitle)
        layout = QtGui.QFormLayout()

        for i, param in enumerate(self._parameters._controls):
            # For each control parameter, constructs an associated control
            controlType = self._parameters._controls[param][4]
            dataType = self._parameters._controls[param][0]
            minValue = self._parameters._controls[param][1]
            maxValue = self._parameters._controls[param][2]
            step = self._parameters._controls[param][3]

            paramValue = self._parameters.__getattribute__(param)
            if str.lower(controlType) == 'spinbox':
                if str.lower(dataType) == 'double':
                    w = QtGui.QDoubleSpinBox()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, param))
                    layout.addRow(QtGui.QLabel(param), w)
                elif str.lower(dataType) == 'doubleg':
                    w = QDoubleSpinBoxG()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, param))
                    layout.addRow(QtGui.QLabel(param), w)
                elif str.lower(dataType) == 'int':
                    w = QtGui.QSpinBox()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, param))
                    layout.addRow(QtGui.QLabel(param), w)
            elif str.lower(controlType) == 'slider':
                w = sliderLabel(paramName=param, paramValue=paramValue, minValue=minValue,
                                maxValue=maxValue, step=step, dataType=dataType, target=self.parameters)
                layout.addRow(w)

        recomputeButton = QtGui.QPushButton('Recompute VOIs')
        recomputeButton.clicked.connect(updateVOIs)
        layout.addRow(recomputeButton)
        controlPanel.setLayout(layout)
        controlPanelContainer.setWidget(controlPanel)
        if dockArea is None:
            controlPanelContainer.show()
        else:
            dockArea.addDockWidget(QtCore.Qt.DockWidgetArea(2), controlPanelContainer)
            q = dockArea.findChildren(QtGui.QDockWidget)
            if len(q)%2 == 0:
                dockArea.splitDockWidget(q[-2],q[-1],QtCore.Qt.Horizontal)
            dockArea.show()
            dockArea.raise_()

        return controlPanelContainer

    def updateVOIs(self, camphor, baseData, VOIdata):
        self.computeVOIs(baseData, VOIdata)
        for i in camphor.vtkView.VOI.importer:
            i.Modified()
        for i in camphor.vtkView2.VOI.importer:
            i.Modified()

        camphor.vtkView.renderAll()
        camphor.vtkView2.renderAll()

class sliderLabel(QtGui.QWidget):
    def __init__(self, paramName, paramValue, minValue, maxValue, step, dataType, target):
        super(sliderLabel, self).__init__()

        self.paramName = paramName
        self.paramValue = paramValue
        vlayout = QtGui.QVBoxLayout()
        hlayout = QtGui.QHBoxLayout()
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.label = QtGui.QLabel(paramName)
        self.target = target

        if str.lower(dataType) == 'double':
            self.spinbox = QtGui.QDoubleSpinBox()
        elif str.lower(dataType) == 'doubleg':
            self.spinbox = QtGui.QDoubleSpinBoxG()
        elif str.lower(dataType) == 'int':
            self.spinbox = QtGui.QSpinBox()
        
        self.slider.setValue(paramValue)
        self.slider.setRange(minValue, maxValue)
        self.slider.setSingleStep(step)
        self.spinbox.setValue(paramValue)
        self.spinbox.setRange(minValue, maxValue)
        self.spinbox.setSingleStep(step)
        
        self.slider.valueChanged.connect(partial(self.valueChanged, 0))
        self.spinbox.valueChanged.connect(partial(self.valueChanged, 1))

        hlayout.addWidget(self.label)
        hlayout.addWidget(self.spinbox)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.slider)
        vlayout.setContentsMargins(0,0,0,0)
        hlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vlayout)
        
    def valueChanged(self, id, value):
        if id is 1:
            self.slider.setValue(value)
        if id is 0:
            self.spinbox.setValue(value)
        setattr(self.target, self.paramName, value)
        
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


class camphorVOIExtractionProgress(object):
    def __init__(self):
        self.iteration = 0
        self.percentDone = 0
        self.totalPercentDone = None




