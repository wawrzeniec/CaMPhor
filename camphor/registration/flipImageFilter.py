from camphor.registration import transform
import SimpleITK as sitk
import numpy

class flipImageFilter(transform.transform):
    def __init__(self):
        super(flipImageFilter, self).__init__()

        # This transform is applied to an entire trial
        self.type = transform.TRIALWISE

        # Default transform = identity
        self.transform = []

        # The transform's name
        self.name = 'flipImageFilter'

    def apply(self, data):
        transformed_data = []

        print("Applying flipImageFilter")
        transformed_data = [data[i][:,:,::-1] for i in range(len(data))]

        return transformed_data

# All registration filters map the filter class to the 'filter' variable for easy dynamic instantiation
filter = flipImageFilter