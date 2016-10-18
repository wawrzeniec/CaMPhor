"""
This file contains abandoned code from CaMPhor...
"""

class plotView(FigureCanvas):
    """

    class camphor.vtkView(FigureCanvas)

    This class implements the embedding of the matplotlib graph into Qt
    To create a plotView object into a QMainWindow widget ('self' below), use:

            ...

    Initially considered to render z-slices of the volume data, but found to be
    much too slow so implemented the rendering with VTK within the vtkView class

    """
    def __init__(self, parent, dpi=100):
        self.figure = Figure(figsize=(3, 10),dpi=dpi)
        super(plotView, self).__init__(self.figure)
        self.axes = self.figure.add_subplot(111, aspect=8/5)
        # plt.axis('equal')
        self.axes.hold(False)
        matplotlib.pyplot.ion()
        self.setParent(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.updateGeometry()

        # The colormap
        cdict = {'red': ((0.0, 0.0, 0.0),
                         (0.5, 1.0, 1.0),
                         (1.0, 1.0, 1.0)),

                 'green': ((0.0, 0.0, 0.0),
                           (0.5, 1.0, 1.0),
                           (1.0, 0.0, 0.0)),

                 'blue': ((0.0, 1.0, 1.0),
                          (0.5, 1.0, 1.0),
                          (1.0, 0.0, 0.0))}

        self.cmap = LinearSegmentedColormap('BlueWhiteRed', cdict)


    def displaySlice(self, data, z):
        self.axes.imshow(numpy.transpose(data[:,z,:]), cmap=self.cmap)
        self.axes.invert_xaxis()
        self.figure.canvas.draw()
        # self.figure.canvas.blit(self.axes.bbox)
        matplotlib.pyplot.pause(0.05)
