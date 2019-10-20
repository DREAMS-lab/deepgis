import sys
from svgpathtools import svg2paths
import math
import matplotlib.pyplot as plt
import numpy as np

# filename = sys.argv[1]
filename = '/home/jdas/litter-mask-human.svg'

paths, attributes = svg2paths(filename)

areas = []
for path in paths:
    area = math.fabs(path.area()) * 0.00541658112
    areas.append(area)

areas.pop()
np.random.seed(19680801)
n_bins = 50
x = np.asarray(areas)
# Generate a normal distribution, center at x=0 and y=5

# We can set the number of bins with the `bins` kwarg
plt.hist(x, bins=n_bins)
plt.show()
