import sys
import imp
sys.path.insert(0, "C:\\Users\\chantal\\PycharmProjects\\CaMPhor")

from camphor.utils import VTKdisplay as disp
import numpy as np

disp = camphor.utils.VTKdisplay
apply = camphor.utils.applyReg

disp(apply(img, tx, img[0]))

# Check termination condition
print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))

# # To reload the module if it has changed
# imp.reload(camphor.utils); disp = camphor.utils.VTKdisplay; apply = camphor.utils.applyReg;



# this worked well with fake test data
# seems like the number of iterations and the learning rate are important

# registration_method.SetOptimizerAsGradientDescent(learningRate=0.01, numberOfIterations=100,
#                                                   convergenceMinimumValue=1e-20, convergenceWindowSize=100)