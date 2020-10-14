# scripts/injectImages
import sys
import glob
import PIL.Image as PILImage
from webclient.models import Image as Im, ImageSourceType, CategoryType
import agdss.settings.common as A
import numpy as np
import os


def run():
        path = sys.argv[3]
        ctr = 1
        if len(sys.argv) < 6:
                print("python manage.py runscript injectImages folder_with_images image_description category_name")
                return

        for filename in os.listdir(path):
                path_basename = os.path.basename(os.path.normpath(path)) + '/'
                print(path_basename, filename)
                image_name = filename
                description = sys.argv[4]
                A.CATEGORY_TO_LABEL = sys.argv[5]
                if ImageSourceType.objects.filter(description=description).count() > 0:
                    sourceType = ImageSourceType.objects.filter(description=description)[0]
                else:
                    i = ImageSourceType(description=description)
                    i.save()
                    sourceType = ImageSourceType.objects.filter(description=description)[0]
                img = PILImage.open(path + image_name)
                width, height = img.size
                print(width,height,type(image_name))
                request_categories = [A.CATEGORY_TO_LABEL]
                category_list = [CategoryType.objects.get_or_create(category_name=category)[0] for category in request_categories]
                print(category_list)
                dbImage = Im(name=image_name, path='/static/' + path_basename, description=description,source=sourceType, width=width, height=height)
                Im.save(dbImage)
                dbImage.categoryType.add(*category_list)
                Im.save(dbImage)
                ctr = ctr + 1
                print(A.CATEGORY_TO_LABEL)

