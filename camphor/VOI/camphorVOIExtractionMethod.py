"""
camphor.VOI.camphorVOiExtractionMethod

This is the abstract base class for implementing VOI extraction methods in CaMPhor

"""

from abc import ABC, abstractmethod, abstractproperty

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

        Each implementation of camphorRegistrationMethod should hook its algorithm to the updateEvent property of the object
        The client (the program that instantiates the registration method can then call setUpdateEvent() to the desired function
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

class camphorVOIExtractionProgress(object):
    def __init__(self):
        self.iteration = 0
        self.percentDone = 0
        self.totalPercentDone = None




