# scripts/injectImages
import sys
import glob
import PIL.Image as PILImage
from webclient.models import Image as Im, ImageSourceType, CategoryType
from agdss.settings.common import *
import numpy as np
import os


def run():
        path = sys.argv[3]
        ctr = 1
        for filename in os.listdir(path):
                path_basename = os.path.basename(os.path.normpath(path)) + '/'
                print(path_basename, filename)
                image_name = filename
                description = "hypolith"
                if ImageSourceType.objects.filter(description=description).count() > 0:
                    sourceType = ImageSourceType.objects.filter(description=description)[0]
                else:
                    i = ImageSourceType(description=description)
                    i.save()
                    sourceType = ImageSourceType.objects.filter(description=description)[0]
                img = PILImage.open(path + image_name)
                width, height = img.size
                print(width,height,type(image_name))
                request_categories = [CATEGORY_TO_LABEL]
                category_list = [CategoryType.objects.get_or_create(category_name=category)[0] for category in request_categories]
                print(category_list)
                dbImage = Im(name=image_name, path='/static/' + path_basename, description=description,source=sourceType, width=width, height=height)
                Im.save(dbImage)
                dbImage.categoryType.add(*category_list)
                Im.save(dbImage)
                ctr = ctr + 1

