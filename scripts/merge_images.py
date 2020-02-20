import cv2
from PIL import Image
import glob
import numpy as np

def merge_images(framearray,rAvg, gAvg, bAvg):
    for frame in framearray:
        cvframe = np.array(frame)
        (B, G, R) = cv2.split(cvframe.astype("float"))
        print cvframe.shape
        if rAvg is None:
            rAvg = R
            bAvg = B
            gAvg = G

        else:
            rAvg = (rAvg + R) / 2.0
            gAvg = (gAvg + G) / 2.0
            bAvg = (bAvg + B) / 2.0
    return rAvg, gAvg,bAvg



image_list = []
(rAvg, gAvg, bAvg) = (None, None, None)
total = 1
path = '/home/jdas/pbr-media/'

for filename in glob.glob(path + '/*.png'): #assuming gif
    im=Image.open(filename)
    image_list.append(im)

rAvg, gAvg,bAvg = merge_images(image_list, rAvg, gAvg, bAvg)

avg = cv2.merge([bAvg, gAvg, rAvg]).astype("uint8")
cv2.imwrite('merged_image.png', avg)
