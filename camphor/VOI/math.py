from scipy import stats
from scipy import ndimage
import numpy


def ncov(x,n,onesided=False):
    """
    camphor.VOI.math.ncov(x,n,onesided=False)

    Neighborhood covariance
    This function calculate the average covariance in a neighborhood of side n, for every pixel in the input image
    For example, n = 1 calculates the covariance, and n=2 calculates the mean covariance in a 3x3 cube centered on each pixel
    When oneSided is True, only positive shifts are considered, thus n=2 results in the mean covariance in a 2x2 cube with the target pixel in a corner

    :param x:           3D time-series passed as a list of 3D numpy arrays
    :param n:           Size of the neighborhood
    :param onesided:    If true, considers only positive index shifts
    :return:            A 3D image of the neighborhood covariance
    """

    X = numpy.stack(x).astype(numpy.double)
    rho = numpy.zeros(x[0].shape,dtype=numpy.double)
    nd = 0
    if onesided:
        rmin = 0
    else:
        rmin = -(n-1)
    for i in range(rmin, n):
        for j in range(rmin, n):
            for k in range(rmin, n):
                nd += 1
                k1 = numpy.roll(numpy.roll(numpy.roll(X,i,1),j,2),k,3)
                rho = numpy.add(rho, numpy.mean(numpy.multiply(k1,X),0)
                                - numpy.multiply(numpy.mean(k1,0),numpy.mean(X,0)))
    rho = numpy.divide(rho,nd)
    print("ncov: covered {:d} pixels".format(nd))
    return rho

    # Normalized to uint8:
    # return ((rho*127/numpy.max(rho))+128).astype(numpy.uint8)

