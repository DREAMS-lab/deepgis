dir = '/home/jdas/AI-pred/'

import os
import PIL.Image as Image
import numpy as np
import re

index = -1
for filename in os.listdir(dir):
    if filename.endswith(".png"):
        index = int(filename.split(".")[0])
        img = np.asarray(Image.open(os.path.join(dir, filename)).convert('L'))
        m, n = img.shape
        img = 1 * (img == 0)
        mask_area = img.sum()
        total_area = m * n
        print(str(index) + "," + str(total_area) + "," + str(mask_area))
        continue
    else:
        continue


