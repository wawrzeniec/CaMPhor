"""
camphor.registration.camphorRegistrationMethod

This is the abstract base class for implementing registration methods in CaMPhor

"""

from abc import ABC, abstractmethod, abstractproperty

class camphorRegistrationMethod(ABC):
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
        camphorRegistrationMethod.execute(camphor)

        Executes the registration method using the current value of the parameters

        :param camphor:      The camphor instance, to get access to the data
        :return:
        """
        pass

    @abstractmethod
    def getProgress(self):
        """
        camphorRegistrationMethod.getProgress()

        This function returns the progress state of the registration currently being executed
        It is used to update the GUI display with information about the state of the registration

        :return: a camphorRegistrationProgress object
        """
        return camphorRegistrationProgress()

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
        print("Percent done: {:g}\nValue: {:g}".format(progress.percentDone, progress.objectiveFunctionValue))

    def setUpdateEvent(self, function):
        self.updateEvent = function

    def message(self, text, *args, **kwargs):
        print(text)

    def setMessage(self, targetFunc):
        self.message = targetFunc

class camphorRegistrationProgress(object):
    def __init__(self):
        self.iteration = 0
        self.percentDone = 0
        self.objectiveFunctionValue = 0
        self.totalPercentDone = None




