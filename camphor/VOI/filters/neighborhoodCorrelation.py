from camphor.VOI.camphorVOIExtractionMethod import camphorVOIExtractionMethod, camphorVOIExtractionProgress
import numpy
import camphor.DataIO as DataIO
from scipy import stats
from scipy import ndimage
from camphor.VOI.math import ncov
import copy

"""
neighborhoodCorrelation - VOI detection filter

This filter attempts to find VOIs using the neighborhood correlation measure:
0. Calculates the neighborhood correlations (camphor.VOI.math.ncov) and assigns the result to VOIbase
3. Finds extended regions of neighborhood correlation higher than a threshold, by:
    - convolving the matrix of p-values with a template cube (3x3x3 matrix of ones)
    - thresholding the result (the max being 3**3 = 27, an appropriate threshold is slighltly lower than this, e.g., 18)

The data is a time series of 3D stacks (list of numpy arrays)

Result: a binary matrix of VOIs, scaled to 255 and in numpy.uint8 type
"""

class neighborhoodCorrelation(camphorVOIExtractionMethod):
    def __init__(self):
        super(neighborhoodCorrelation, self).__init__()
        self._parameters = neighborhoodCorrelationParameters()
        self.nDone = 0
        self.nTotal = 1

    @property
    def parameters(self):
        return self._parameters

    def execute(self, camphor):
        # Only first brain, for now
        brain = range(camphor.project.nBrains)
        brain = [0]

        # Determines the total number of trials to do
        nBrains = len(brain)
        self.nTotal = 0
        for b in brain:
            self.nTotal += camphor.project.brain[b].nTrials

        self.nDone = 0

        for b in brain:
            nTrials = camphor.project.brain[b].nTrials
            for t in range(nTrials):
                self.message('Computing neighborhood correlation (brain {:d}/{:d}, trial {:d}/{:d})'.format(b+1,nBrains,t+1,nTrials), progress=100 * self.nDone / self.nTotal)

                camphor.openFileFromProject(brain=b, trial=t, view=0)

                data = camphor.rawData
                transforms = camphor.project.brain[b].trial[t].transforms
                for tr in transforms:
                    if tr.active:
                        data = tr.apply(data)

                lx, ly, lz = data[0].shape

                VOIbase = ncov(data,2,onesided=False)

                self.message('** Searching for connected regions(brain {:d}/{:d}, trial {:d}/{:d})'.format(
                             b + 1, nBrains, t + 1, nTrials),
                             progress=100 * (self.nDone + 0.99) / self.nTotal)

                VOIdata = numpy.zeros(VOIbase.shape, dtype=numpy.uint8)
                self.computeVOIs(VOIbase, VOIdata)

                camphor.project.brain[b].trial[t].VOIdata = VOIdata
                camphor.project.brain[b].trial[t].VOIbase = VOIbase
                camphor.project.brain[b].trial[t].VOIfilter = self.__class__
                camphor.project.brain[b].trial[t].VOIfilterParams = copy.deepcopy(self.parameters)

                if self.cancelled:
                    self.cancelled = False
                    self.message('Registration cancelled', progress=100)
                    return None

                self.nDone += 1

        self.message('VOI extraction completed', progress=100)

    def computeVOIs(self, VOIbase, VOIdata):
        print('computing VOIs')
        print("VOIbase: min = {:f}, max={:f}".format(numpy.min(VOIbase), numpy.max(VOIbase)))
        q = ndimage.percentile_filter(VOIbase / numpy.max(VOIbase), self.parameters.prctile, size=self.parameters.fSize)
        print("q: min = {:f}, max={:f}".format(numpy.min(q), numpy.max(q)))
        q3 = (numpy.greater(q, self.parameters.fThresh)).astype(numpy.uint8)
        print("q3: sum={:d}".format(numpy.sum(q3)))
        VOIdata[:] = q3

    def getProgress(self):
        progress = camphorVOIExtractionProgress()
        progress.iteration = self.nDone
        progress.percentDone = progress.iteration / self.nTotal * 100
        progress.totalPercentDone = progress.iteration / self.nTotal * 100

        return progress



class neighborhoodCorrelationParameters(object):
    def __init__(self):
        self.prctile = 75
        self.fSize = 2
        self.fThresh = 0.05

        self._paramType = {'prctile': ['int', 0, 100, 1],
                           'fSize': ['int',1,100,1],
                           'fThresh': ['doubleg', 0, 1, 0.001]}

        self._controls = {'prctile': ['int', 0, 100, 1, 'slider'],
                          'fSize': ['int', 1, 100, 1, 'spinbox'],
                          'fThresh': ['doubleg', 0, 1, 0.001, 'slider']}

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = neighborhoodCorrelation

