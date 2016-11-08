from camphor.VOI.camphorVOIExtractionMethod import camphorVOIExtractionMethod, camphorVOIExtractionProgress
import numpy
import camphor.DataIO as DataIO
from scipy import stats
from scipy import ndimage
import copy

"""
CtCT - VOI detection filter (Convolution, t-test, Convolution, Threshold)

This filter attempts to find VOIs using the following procedure:
0. Convolves the data with a template cube (the typical size of a cell, 3x3x3) 
1. Compares the responses in baseline time frames with those in stimulation time frames using a t-test
2. Thresholds the resulting p-value (e.g. <0.05)
3. Finds extended regions of p-values lower than the threshold by:
    - convolving the matrix of p-values with a template cube (3x3x3 matrix of ones)
    - thresholding the result again (the max being 3**3 = 27, an appropriate threshold is slighltly lower than this, e.g., 18)

The data is a time series of 3D stacks (list of numpy arrays)

Result: a binary matrix of VOIs, scaled to 255 and in numpy.uint8 type
"""

class CtCT(camphorVOIExtractionMethod):
    def __init__(self):
        super(CtCT, self).__init__()
        self._parameters = CtCTParameters()
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
                self.message('Computing p-values (brain {:d}/{:d}, trial {:d}/{:d})'.format(b+1,nBrains,t+1,nTrials), progress=100 * self.nDone / self.nTotal)

                camphor.openFileFromProject(brain=b, trial=t, view=0)

                data = camphor.rawData
                transforms = camphor.project.brain[b].trial[t].transforms
                for tr in transforms:
                    if (tr.active):
                        data = tr.apply(data)

                lx, ly, lz = data[0].shape

                VOIbase = numpy.zeros([lx, ly, lz])

                # Convolves the data
                cdata = [ndimage.convolve(d.astype(numpy.double), numpy.ones([self.parameters.cubeSize] * 3)) for d in data]

                # 1. t-test
                nttests = lx*ly*lz
                npixdone=0

                for i in range(lx):
                    for j in range(ly):
                        for k in range(lz):
                            s = [data[t][i, j, k] for t in range(len(data))]
                            tstat, VOIbase[i, j, k] = stats.ttest_ind(s[0:2], s[3:7], equal_var=False)
                            npixdone += 1
                        self.message(
                            'Computing p-values (brain {:d}/{:d}, trial {:d}/{:d})'.format(
                            b + 1, nBrains, t + 1, nTrials),
                            progress=100 * (self.nDone+0.99*npixdone/nttests) / self.nTotal)
                        if self.cancelled:
                            self.cancelled = False
                            self.message('Registration cancelled', progress=100)
                            return None

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
        q = numpy.less(VOIbase, self.parameters.pThresh)
        q2 = ndimage.convolve(q.astype(numpy.uint8), numpy.ones([self.parameters.cubeSize] * 3))
        q3 = (numpy.greater(q2, self.parameters.fThresh)).astype(numpy.uint8)
        VOIdata[:] = q3

    def getProgress(self):
        progress = camphorVOIExtractionProgress()
        progress.iteration = self.nDone
        progress.percentDone = progress.iteration / self.nTotal * 100
        progress.totalPercentDone = progress.iteration / self.nTotal * 100

        return progress



class CtCTParameters(object):
    def __init__(self):
        self.pThresh = 0.05
        self.cubeSize = 3
        self.fThresh = 18

        self._paramType = {'pThresh': ['doubleg', 1e-20, 1, 1e-2],
                           'cubeSize': ['int', 1, 100, 1],
                           'fThresh': ['int', 1, 1000, 1]}

        self._controls = {'pThresh': ['doubleg', 1e-20, 1, 1e-2, 'spinBox'],
                          'fThresh': ['int', 1, 100, 1, 'slider'],
                          'cubeSize': ['int', 1, 100, 1, 'spinBox']}

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = CtCT

