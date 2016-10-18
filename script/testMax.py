# This calculates the max over all trials in the project (only for the first brain right now)
# The idea being to extract VOIs easily

# 1. Loads the first trial
self.openFileFromProject(brain=0,trial=0,view=1)

maxData = [self.vtkView.tdata1[i] for i in range(self.vtkView.nt)]

nTrials = self.project.brain[0].nTrials


for i in range(1,nTrials):
    self.openFileFromProject(brain=0, trial=i, view=1)
    maxData = [np.maximum(maxData[t],self.vtkView.tdata1[t]) for t in range(self.vtkView.nt)]



