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

    def controlWidget(self, vtkView, baseData, VOIData):
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

        if not hasattr(self._parameters,'controls'):
            return None
        
        def updateVOIs(filterInstance, vtkView, baseData, VOIData):
            filterInstance.updateVOIs(vtkView, baseData, VOIData)
            pass
        
        def setParamNumeric(filterInstance, key, value):
            setattr(filterInstance.parameters, key, value)
            updateVOIs(filterInstance, vtkView, baseData, VOIData)

        def setParamList(filterInstance, key, valueList, value):
            setattr(filterInstance.parameters, key, valueList[value])
            updateVOIs(filterInstance, vtkView, baseData, VOIData)

        controlPanel = QtGui.QWidget()
        controlPanel.setWindowFlags(QtCore.Qt.Tool)
        layout = QtGui.QFormLayout()

        for i, param in enumerate(self._parameters.controls):
            # For each control parameter, constructs an associated control
            controlType = self._parameters._controls[param][4]
            dataType = self._parameters._controls[param][0]
            minValue = self._parameters._controls[param][1]
            maxValue = self._parameters._controls[param][2]
            step = self._parameters._controls[param][3]

            paramValue = self._parameters.__getattribute__(param)
            if controlType is 'spinBox':
                if dataType is 'double':
                    w = QtGui.QDoubleSpinBox()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, self, param))
                    layout.addRow(QtGui.QLabel(param), w)
                elif dataType is 'doubleg':
                    w = QtGui.QDoubleSpinBoxG()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, self, param))
                    layout.addRow(QtGui.QLabel(param), w)
                elif dataType is 'int':
                    w = QtGui.QSpinBoxG()
                    w.setRange(minValue, maxValue)
                    w.setSingleStep(step)
                    w.setValue(paramValue)
                    w.valueChanged.connect(partial(setParamNumeric, self, param))
                    layout.addRow(QtGui.QLabel(param), w)
            elif controlType is 'slider':
                w = sliderLabel(self, paramValue, minValue, maxValue, step, dataType)

    def updateVOIs(self, vtkView, baseData, VOIdata):
        print('Updating VOIs!!!!')


class sliderLabel(QtGui.QWidget):
    def __init(self, parent, param, minValue, maxValue, step, dataType):
        super(sliderLabel, self).__init__()
        
        self.param = param
        layout = QtGui.QHBoxLayout()
        self.slider = QtGui.QSlider()
        
        if dataType is 'double':
            self.spinbox = QtGui.QDoubleSpinBox()
        elif dataType is 'doubleg':
            self.spinbox = QtGui.QDoubleSpinBoxG()
        elif dataType is 'int':
            self.spinbox = QtGui.QSpinBox()
        
        self.slider.setValue(param)
        self.slider.setRange(minValue, maxValue)
        self.slider.setSingleStep(step)
        self.spinbox.setValue(param)
        self.spinbox.setRange(minValue, maxValue)
        self.spinbox.setSingleStep(step)
        
        self.slider.valueChanged.connect(self.valueChanged)
        self.spinbox.valueChanged.connect(self.valueChanged)

        layout.addWidget(self.slider)
        layout.addWidget(self.combobox)
        self.setLayout(layout)
        
    def valueChanged(self, value):
        if self is self.spinbox:
            self.slider.setValue(value)
        if self is self.slider:
            self.spinbox.setValue()
        self.param = value
        self.parent.updateVOIs()
        
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




