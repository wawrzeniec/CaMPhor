"""

camphor.camphorProject

This is the class that holds data about a CaMPhor project
The display is implemented in camphor.projectView's projectView class

"""

import os
import copy

class camphorProject:
    """
    class camphor.projectView.project

    This class stores and manipulates the hierarchical data for a CaMPhor project

    A project is organized as follows:

        - a number of brains are included in the project

        - for each brain, a number of trials (data) are included

        - for each trials, a number of analyses can be performed
            e.g., intra-trial registration, VOI detection, segmentation

    This class stores this information for a project and inmplements data I/O (load & save)
    """

    def __init__(self):

        # The number of brains in the project
        self.nBrains = 0

        # The data for the brains in the project
        self.brain = []

    def appendBrain(self, directory):
        self.brain.append(brainData(index=self.nBrains, directory=directory))
        self.nBrains += 1

    def appendTrial(self, brainIndex, dataFile, info, name=None, stimulusID=None):
        self.brain[brainIndex].trial.append(
            trialData(brainIndex=brainIndex,
            index=self.brain[brainIndex].nTrials,
            dataFile=dataFile,
            info=info,
            name=name,
            stimulusID = stimulusID))
        self.brain[brainIndex].nTrials += 1

    def appendTrialToLastBrain(self, dataFile, info, name=None, stimulusID=None):
        brainIndex = self.nBrains - 1
        self.brain[brainIndex].trial.append(
            trialData(brainIndex=brainIndex,
            index=self.brain[brainIndex].nTrials,
            dataFile=dataFile,
            info=info,
            name=name,
            stimulusID=stimulusID))
        self.brain[brainIndex].nTrials += 1

    def copy(self):
        """
        camphorProject.copy()

        :return: a copy of the project without the non-serializable objects (ITK transforms)
        """

        newp = camphorProject()

        for b in self.brain:
            newp.brain.append(b.copy())
            newp.nBrains += 1

        return newp

class brainData:
    """
    This class holds information about a brain included in a project
    """

    def __init__(self, index = None, directory = None, trial = None):
        # The properties of a brain are stored here
        # For now, only a number is attributed, but more detailed
        # info could be stored here (e.g., genotype, date, etc)

        # The number attributed to this brain in the project
        if index is None:
            self.index =  None
        else:
            self.index = index

        # The data for the trials
        if trial is None:
            self.trial = []
            self.nTrials = 0
        else:
            self.trial = trial
            self.nTrials = len(self.trial)

        if directory is None:
            self.directory = ''
        else:
            self.directory = directory

        self.transforms = []

    def copy(self):
        newb = brainData()

        d = self.__dict__
        for k in d.keys():
            if k == 'transforms':
                attr = self.__getattribute__(k)
                for t in attr:
                    newb.transforms.append(t.copy())
            elif k == 'trial':
                attr = self.__getattribute__(k)
                for t in attr:
                    print(t.copy())
                    newb.trial.append(t.copy())
            else:
                newb.__setattr__(k, copy.deepcopy(self.__getattribute__(k)))

        return newb


class trialData:
    """
    This class holds information about a single trial from a parent brain
    """

    def __init__(self, brainIndex = None, index=None, dataFile=None, info = None, name=None, stimulusID=None):
        # The properties of a trial are stored here
        # Add more properties as appropriate

        # The index of the brain belongs to in the project
        if brainIndex is None:
            self.brainIndex = None
        else:
            self.brainIndex = brainIndex

        # The index of the trial
        if index is None:
            self.index = None
        else:
            self.index = index

        # The location of the .lsm file
        if dataFile is None:
            self.dataFile = None
        else:
            self.dataFile = dataFile

        # Trial name (by default, this should be the .lsm file name
        if name is None:
            if dataFile is None:
                self.name = None
            else:
                self.name = os.path.basename(self.dataFile)
        else:
            self.name = name

        if info is None:
            self.info = {'dimX': 'N/A', 'dimY': 'N/A', 'dimZ': 'N/A', 'dimC': 'N/A', 'dimT': 'N/A', 'voxSizeX': 'N/A',
                         'voxSizeY': 'N/A', 'voxSizeZ': 'N/A', 'specScan': 'N/A', 'bitDepth': 'N/A'}
        else:
            self.info = info

        # The stimulus identity
        self.stimulusID = stimulusID

        # The transforms
        self.transforms = []

    def copy(self):
        newt = trialData()

        d = self.__dict__
        for k in d.keys():
            if k =='transforms':
                attr = self.__getattribute__(k)
                for t in attr:
                    newt.transforms.append(t.copy())
            else:
                newt.__setattr__(k, copy.deepcopy(self.__getattribute__(k)))

        return newt