"""
camphor.registration.transform

This module implements the abstract base class for applying transformations to the data

A transform implementation must define its type (brain-wise, trial-wise, slice-wise, etc) so that camphor knows where to display
the object in projectView, and implement the apply() function to execute the transform on input data (input data being an array
of 3D numpy arrays)

"""

from abc import ABC, abstractmethod, abstractproperty
from camphor.camphorProject import camphorProject
import copy
import time

# The types of transformations
BRAINWISE = 0
TRIALWISE = 1
TIMESLICEWISE = 2

class transform(ABC):
    def __init__(self):
        self._type = 0
        self._target = None
        self.name = ''
        self._active = True
        self._transform = []

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, newtransform):
        self._transform = newtransform

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, newtype):
        if(newtype not in (BRAINWISE, TRIALWISE, TIMESLICEWISE)):
            raise transformInvalidType('The requested type ({:d}) for camphor.registration.transform object is invalid'.format(newtype))
        self._type = newtype

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, newtarget):
        newclass = newtarget.__class__
        if(newclass not in (camphorProject.brainData, camphorProject.trialData)):
            raise transformInvalidTarget('Transform targets must be camphorProject.brainData or camphorProject.trialData objects')
        self._target = newtarget

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, newstate):
        if (newstate.__class__ is not bool):
            raise transformInvalidState(
                'Active property must be bool (received {:s}'.format(str(newstate.__class__)))
        self._active = newstate

    @abstractmethod
    def apply(self, data):
        pass

    def copy(self):
        """
        transform.copy()

        This function creates a (mostly deep) copy of a transform, EXCLUDING THE transform property which is not serializable
        Instead, the transform property is mapped to list with the same structure, containing None in each item

        A deepcopy operation could be implemented by writing ITK transforms to a file and reinstantiating them

        In the current version, transforms can have depth 2, i.e., the transform property is an array, the elements of which
        can be arrays, the elements of which can also be arrays.

        The first depth level is intended to account for TIMESLICEWISE transformations, for which there is a different transform
        for each time frame. Thus transform is an array that can contain one ITK transform for each time slice.

        The second depth level is intended to allow for transformations on a single time frame that cannot be summarized in a single ITK transform.
        For example, registering each Z-slice of the volume independently would require one transformation for each slice. Thus, the transformation
        for this time frame can also be an array containing multiple ITK transforms.
        Ultimately, the class implementing a camphor.registration.transform object makes use of the available ITK transforms appropriately in its apply() method.

        :return: a copy of the transform object (without ITK transforms)
        """
        filterClass = self.__class__
        newFilter = filterClass()

        d = self.__dict__
        for k in d.keys():
            if k=='_transform':
                attr = self.__getattribute__(k)
                if isinstance(attr, list):
                    newFilter.transform = []
                    for i1 in range(len(attr)):
                        if isinstance(attr[i1], list):
                            transform2 = []
                            for ia, a in enumerate(attr[i1]):
                                if isinstance(a, list):
                                    transform2.append([None for i in range(len(a))])
                                else:
                                    transform2.append(None)
                            newFilter.transform.append(transform2)
                        else:
                            newFilter.transform.append(None)
                else:
                    newFilter.transform = None
            else:
                newFilter.__setattr__(k, copy.deepcopy(self.__getattribute__(k)))

        return newFilter

    def __copy__(self):
        return self.copy()


    def __deepcopy__(self):
        return self.copy()


class transformInvalidType(Exception):
    pass

class transformInvalidTarget(Exception):
    pass

class transformInvalidState(Exception):
    pass