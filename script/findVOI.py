import numpy as np
from scipy import stats
from scipy import ndimage

def findVOIs(data=None, pthresh=0.05, fthresh = 18):
    """
    This function attempts to find VOIs using the following procedure:
    1. Compares the responses in time frames 1-3 with those in time frames 5-7 using a t-test
    2. Thresholds the resulting p-value (e/g/ <0.05)
    3. Finds extended regions of p-values lower than the threshold by:
        - convolving the matrix of p-values with a template cube (3x3x3 matrix of ones)
        - thresholding the result again (the max being 3**3 = 27, an appropriate threshold is slighltly lower than this, e.g., 18)

    The data is a time series of 3D stacks (list of numpy arrays)
    If no data is provided, the data in vtkview1 is used instead

    Return: binary matrix of VOIs, scaled to 255 and in numpy.uint8 type
    """

    # 0. fetches the data
    if data is None:
        data = self.vtkView.tdata1

    lx,ly,lz = data[0].shape
    voi = np.zeros([lx,ly,lz])

    # 1. t-test
    print('** Searching VOIs **')
    print('Computing p-values')
    for i in range(lx):
        for j in range(ly):
            for k in range(lz):
                s = [data[t][i, j, k] for t in range(len(data))]
                t, voi[i, j, k] = stats.ttest_ind(s[0:2], s[4:7], equal_var=False)
        progressBar(i+1,lx)

    print('** Searching for connected regions....')
    q = np.less(voi,pthresh)
    q2 = ndimage.convolve(q.astype(np.uint8), np.ones([3,3,3]))
    q3 = np.greater(q2,fthresh)

    return (q3*255).astype(np.uint8)




def progressBar(value, endvalue, bar_length=20):
    if not hasattr(progressBar, "erasestr"):
        progressBar.erasestr = ''

    percent = float(value) / endvalue
    arrow = '-' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    outstr = "Percent: [{0}] {1}%".format(arrow + spaces, int(round(percent * 100)))

    sys.stdout.write(progressBar.erasestr)
    sys.stdout.write(outstr)
    sys.stdout.flush()
    progressBar.erasestr = '\b' * len(outstr) + '\r'
