import io
import json
import os.path
from random import randint
import subprocess
import os
from django.shortcuts import render
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urljoin
import logging
from urllib.request import urlopen
import re
import sys
import io
import urllib.request, urllib.parse, urllib.error
from io import StringIO
from PIL import Image as PILImage
import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.validators import URLValidator
from django.db.models import Count
from django.http import *
from django.http import JsonResponse, HttpResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core import serializers

from . import helper_ops
from .image_ops.convert_images import image_label_string_to_SVG_string, render_SVG_from_label, \
    image_labels_to_countable_npy, image_labels_to_countable_npy_with_labels
from webclient.image_ops import crop_images
from .models import Color, CategoryType, ImageSourceType, Image, Labeler, ImageWindow, ImageLabel, CategoryLabel, \
    ImageFilter, TiledLabel, TileSet, Tile
from . import models
from webclient.image_ops.convert_images import convert_image_label_to_SVG

import csv
import base64
import numpy as np
from .models import *
from django.contrib.gis.geos import Polygon, MultiPolygon
import csv

######
# PAGES
######

@login_required
def index(request):
    template = loader.get_template('webclient/index.html')
    context = {}
    return HttpResponse(template.render(context, request))


@login_required
def view_label(request):
    template = loader.get_template('webclient/view_label.html')
    context = {}
    return HttpResponse(template.render(context, request))


@login_required
def label(request):
    # latest_image_list = os.listdir('C:/Users/Sandeep/Dropbox/kumar-prec-ag/tag_images') # '/Users/jdas/Dropbox/Research/agriculture/agdss/image-store/')
    latest_image_list = Image.objects.all()
    template = loader.get_template('webclient/label.html')
    if latest_image_list:
        context = {
            'latest_image_list': latest_image_list,
            'selected_image': latest_image_list[0],
        }
    else:
        context = {}
    return HttpResponse(template.render(context, request))


@login_required
def results(request):
    template = loader.get_template('webclient/results.html')
    context = {}
    return HttpResponse(template.render(context, request))


@login_required
def map_label(request):
    template = loader.get_template('webclient/map_label.html')
    # str(cat.color)
    context = {
        # 'categories': [{"category_name":cat.category_name, "color":str(cat.color)} for cat in CategoryType.objects.all()]
        'categories': {cat.category_name: str(cat.color) for cat in CategoryType.objects.all()}

    }
    request.session['prev_multipoly'] = str(MultiPolygon())
    return HttpResponse(template.render(context, request))


@login_required
@require_POST
@csrf_exempt
def createMasks(request):
    try:
        user = request.user
        print(user)
        if not user.is_authenticated:
            return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
        else:
            dict = json.load(request)
            labels = dict['labels']
            if (len(labels) == 0):
                return JsonResponse({"status": "failure", "message": "No images selected"}, safe=False)
            _user = User.objects.filter(username=user)[0]
            labels_db = []
            for label in labels:
                _user = User.objects.filter(username=label["user"])[0]
                _labeler = Labeler.objects.filter(user=_user)[0]
                _image_window = ImageWindow.objects.filter(width=label["width"],
                                                           height=label["height"],
                                                           x=label["padding_x"],
                                                           y=label["padding_y"])[0]
                _image = Image.objects.filter(name=label["parent_image"])[0]
                _label_db = ImageLabel.objects.filter(labeler=_labeler,
                                                      parentImage=_image,
                                                      timeTaken=label["timetaken"],
                                                      imageWindow=_image_window
                                                      )
                print(_label_db)
                if len(_label_db) == 1:
                    labels_db.append(_label_db[0])

            file_path = image_labels_to_countable_npy_with_labels(user, labels_db)
            file_path = file_path.replace("media-root", "media")

            return JsonResponse({"status": "success", "message": file_path}, safe=False)
    except:
        return JsonResponse({"status": "failure", "message": "Something failed"}, safe=False)


@login_required
def display_annotations(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

    _user = User.objects.filter(username=user)[0]
    _labeler = Labeler.objects.filter(user=_user)[0]
    if _user.is_staff or _user.is_superuser:
        labels = ImageLabel.objects.filter()
    else:
        labels = ImageLabel.objects.filter(labeler=_labeler)
    response = dict()
    count = 1

    for label in labels:
        response[count] = dict()
        response[count]["parent_image"] = label.parentImage.name
        response[count]["height"] = label.imageWindow.height
        response[count]["width"] = label.imageWindow.width
        response[count]["padding_x"] = label.imageWindow.x
        response[count]["padding_y"] = label.imageWindow.y
        response[count]["timetaken"] = label.timeTaken
        response[count]["number"] = label.id
        response[count]["labeler"] = str(label.labeler)
        count += 1
    output = {"status": "success"}
    output["message"] = response
    return JsonResponse(output, safe=False)


##################
# POST/GET REQUESTS
##################
@csrf_exempt
def applyLabels(request):
    try:

        dict = json.load(request)
    #        print("-------------------=========-")
    #        image_labels_to_countable_npy()
    except json.JSONDecodeError:
        print("Could not decode")
        return HttpResponseBadRequest("Could not decode JSON")
    try:
        label_list_ = dict['label_list']
        category_labels = dict['category_labels']
        image_name = dict['image_name']
        path = dict['path']
        # category = dict['category']
        # category_name = dict['category_name']
        image_filters = dict['image_filters']
        subimage = dict['subimage']
        timeTaken = dict['timeTaken']
    except KeyError as e:
        return HttpResponseBadRequest("Missing required key {}".format(e))
    user = request.user
    if not user.is_authenticated:
        return HttpResponseBadRequest("Requires logged in user")
    try:
        labeler = Labeler.objects.get(user=user)
    except Labeler.DoesNotExist:
        labeler = Labeler(user=user)
        labeler.save()
    except MultipleObjectsReturned:
        print("Multiple labelers for user object", file=sys.stderr)
        return HttpResponseBadRequest("Multiple labelers for user object")

    parentImage_ = Image.objects.all().filter(name=image_name, path=path)

    imageWindowList = ImageWindow.objects.all().filter(
        x=subimage['x'], y=subimage['y'], width=subimage['width'], height=subimage['height'])
    if imageWindowList:
        imageWindow = imageWindowList[0]
    else:
        imageWindow = ImageWindow(x=subimage['x'], y=subimage['y'],
                                  width=subimage['width'], height=subimage['height'])
        imageWindow.save()

    sourceTypeList = ImageSourceType.objects.all().filter(description="human")
    if (sourceTypeList):
        sourceType = sourceTypeList[0]
    else:
        sourceType = ImageSourceType(description="human", pub_date=datetime.now())
        sourceType.save()

    labelObject = ImageLabel(parentImage=parentImage_[0], combined_labelShapes=label_list_,
                             pub_date=datetime.now(),
                             labeler=labeler, imageWindow=imageWindow,
                             timeTaken=timeTaken)
    labelObject.save()

    for category_name, labels in category_labels.items():
        categoryTypeList = CategoryType.objects.all().filter(category_name=category_name)
        if (categoryTypeList):
            categoryType = categoryTypeList[0]
        else:
            categoryType = CategoryType(category_name=category_name, pub_date=datetime.now(), color=get_color())
            categoryType.save()

        category_label = CategoryLabel(categoryType=categoryType,
                                       labelShapes=category_labels[category_name], parent_label=labelObject)
        category_label.save()
        image_filter_obj = ImageFilter(brightness=image_filters['brightness'],
                                       contrast=image_filters['contrast'],
                                       saturation=image_filters['saturation'],
                                       imageLabel=labelObject,
                                       labeler=labeler)
        image_filter_obj.save()

        # convert_image_label_to_SVG(labelObject)
        # convert_category_label_to_SVG(category_label)
    #
    # convert_image_label_to_SVG(labelObject)

    #    if not parentImage_:
    #        parentImage_ = Image(name=image_name, path = '/static/tag_images/', description = "development test", source = sourceType, pub_date=datetime.now())
    #        parentImage_.save()
    #   else:

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    # if x_forwarded_for:
    #     #ipaddress = x_forwarded_for.split(',')[-1].strip()
    # else:
    #     #ipaddress = request.META.get('REMOTE_ADDR')

    # combineImageLabels(parentImage_[0], 50)
    return HttpResponse(label_list_)


@require_GET
def loadLabels(request):
    if 'image_name' not in request.GET or 'path' not in request.GET:
        print('Path and Image Name required', (request.GET['path'] + ' ' + request.GET['image_name']))
        return HttpResponseBadRequest('Path and Image Name required')

    parentImage_ = request.GET['image_name']
    label_list = []
    sourceType = ''
    categoryType = ''
    # sourceTypeList = ImageSourceType.objects.all().filter(description="human");
    # if (sourceTypeList):
    #     sourceType = sourceTypeList[0]
    # else:
    #     sourceType = ImageSourceType(description="human", pub_date=datetime.now())
    #     sourceType.save()

    image = Image.objects.all().filter(name=request.GET['image_name'], path=request.GET['path'])
    # if not image:
    #     parentImage_ = Image(name=parentImage_, path='/static/tag_images/',description='test generation at serverside', source=sourceType, pub_date=datetime.now())
    #     parentImage_.save()
    if not image:
        return HttpResponseBadRequest("No such image found")
    label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    responseText = ''
    if (label_list):
        responseText = responseText + label_list.labelShapes
    return JsonResponse(responseText, safe=False)


@require_GET
def getInfo(request):
    if 'image_name' not in request.GET or 'path' not in request.GET:
        return HttpResponseBadRequest("Missing 'image_name or 'path'")
    parentImage_ = request.GET['image_name']
    label_list = []
    sourceType = ''
    categoryType = ''
    sourceTypeList = ImageSourceType.objects.all().filter(description="human")
    if (sourceTypeList):
        sourceType = sourceTypeList[0]
    else:
        sourceType = ImageSourceType(description="human", pub_date=datetime.now())
        sourceType.save()

    image = Image.objects.all().filter(name=parentImage_)
    if not image:
        return HttpResponseBadRequest(
            "Could not find image with name " + request.GET['image_name'] + " and path " + request.GET['path'])
        # img = Image(name=parentImage_, path='/static/tag_images/',description='test generation at serverside', source=sourceType, pub_date=datetime.now())
        # img.save()
    # else:
    label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    response = {}
    if label_list:
        response['label'] = label_list.labelShapes
    else:
        response['label'] = ''
    response['path'] = image[0].path
    response['categories'] = [c.category_name for c in image[0].categoryType.all()]
    return JsonResponse(response, safe=False)


# function to get category information for all categories
@require_GET
@csrf_exempt
def get_category_info(request):
    response = {}
    for category in CategoryType.objects.all():
        response[category.category_name] = {
            'color': str(category.color),
        }
    return JsonResponse(response, safe=False)


# function to get LOLA craters within the specified region for annotation app
@csrf_exempt
@require_GET
def getLOLACraterAnnotations(request):
    # get parameters from request
    UpperLeftLatitude = float(request.GET['UpperLeftLatitude'])
    UpperLeftLongitude = float(request.GET['UpperLeftLongitude'])
    LowerRightLatitude = float(request.GET['LowerRightLatitude'])
    LowerRightLongitude = float(request.GET['LowerRightLongitude'])

    minLatitude = min(UpperLeftLatitude, LowerRightLatitude)
    maxLatitude = max(UpperLeftLatitude, LowerRightLatitude)
    minLongitude = min(UpperLeftLongitude, LowerRightLongitude)
    maxLongitude = max(UpperLeftLongitude, LowerRightLongitude)

    print(minLatitude, maxLatitude, minLongitude, maxLongitude)

    # get file path
    folderpath = os.path.realpath(settings.STATIC_ROOT)
    filename = folderpath + "/lroc_crater_db.csv"

    # parse file to get only required crater data
    craterList = []
    with open(filename) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for line in reader:
            if (float(line[1]) <= maxLatitude and
                    float(line[1]) >= minLatitude and
                    float(line[0]) <= maxLongitude and
                    float(line[0]) >= minLongitude):
                craterList.append(line)

    # print(craterList)
    return JsonResponse(craterList, safe=False)


# function to get image metadata from json file
# This function assumes json files are in static_root
def getImageMetadata(file):
    with open(file, 'r') as json_file:
        metadata = json.load(json_file)
    return metadata


@require_GET
def getNewImage(request):
    # if not 'image_name' in request.GET or not 'path' in request.GET:
    #     hasPrior = False
    # else:
    #     hasPrior = True
    #     #return HttpResponseBadRequest("Missing image name or path")

    if len(Image.objects.all()) == 0:
        return HttpResponseBadRequest("No images in database")

    ##Choose image

    # Random choice
    # if len(Image.objects.all()) > 1 and hasPrior:
    #     img = choice(Image.objects.all().exclude(name=request.GET['image_name'], path=request.GET['path']))
    # else:
    #     img = choice(Image.objects.all())
    #

    # Least number of labels which was not just seen
    # if hasPrior and len(Image.objects.all()) > 1:
    #     img = img.exclude(name=request.GET['image_name'], path=request.GET['path'])

    labelsPerImage = crop_images.NUM_WINDOW_COLS * \
                     crop_images.NUM_WINDOW_ROWS * crop_images.NUM_LABELS_PER_WINDOW

    images = Image.objects.all().annotate(count=Count('imagelabel')).filter(count__lt=labelsPerImage)
    user = request.user
    print(user)
    if user.groups.filter(name='god').exists():
        ignore_max_count = True
    else:
        ignore_max_count = False
        print(images)

        # categories_to_label = [settings.CATEGORY_TO_LABEL]
        # all_unfinished_images = images
        # for cat in categories_to_label:
        #     print(cat)
        #     images = all_unfinished_images.filter(categoryType__category_name=cat)
        #     if images:
        #         break

    images = images.order_by('count').reverse()
    print(images)
    #
    # subimage = None
    # categories_to_label = [settings.CATEGORY_TO_LABEL]
    # all_unfinished_images = images
    # for cat in categories_to_label:
    #     images = all_unfinished_images.filter(categoryType__category_name=cat)
    #     if images:
    #         break
    #
    # images = images.order_by('count').reverse()
    # subimage = None

    img = None
    for im in images:
        index = randint(0, len(images) - 1)
        i = images[index]
        subimage = crop_images.getImageWindow(i, request.user, ignore_max_count=ignore_max_count)
        if subimage is not None:
            img = i
            break

    if not img:
        return HttpResponseBadRequest("Could not find image to serve")
    label_list = ImageLabel.objects.all().filter(parentImage=img).order_by('pub_date').last()

    # fetch image metadata from xml file
    metadata_file = os.path.realpath(settings.STATIC_ROOT) + '/life-images-json/' + img.name
    image_metadata = {}
    if os.path.exists(metadata_file):
        image_metadata = getImageMetadata(metadata_file)
        print("Log: Colors in getNewImage: ", img.categoryType.all())

    response = {
        'path': img.path,
        'metadata': image_metadata,
        'image_name': img.name,
        'categories': [c.category_name for c in CategoryType.objects.all()],
        'shapes': [c.get_label_type_display() for c in img.categoryType.all()],
        'colors': [str(c.color) for c in CategoryType.objects.all()],
        'subimage': subimage,
    }
    # if label_list:
    #    response['labels'] = label_list.labelShapes
    #    response['labels'] = label_list.combined_labelShapes
    # else:
    response['labels'] = ''

    return JsonResponse(response)


# #TODO: Remove csrf_exempt
# @csrf_exempt
# def purge(request):
#    Image.objects.all().delete()
#    ImageLabel.objects.all().delete()
#    ImageSourceType.objects.all().delete()
#    CategoryType.objects.all().delete()
#    return HttpResponse("PURGED TABLES!")


# TODO: Check for bad input
'''
Request: POST
{
    path: location of image (not including image name itself. E.g. '/home/self/image-location/'). REQUIRED
    image_name:name of image REQUIRED
    description: A description NOT REQUIRED
    source_description: Description of image_source. NOT REQUIRED
    categories: List of categories of the image (e.g. ['apple', 'day']). REQUIRED, must be NONEMPTY.
}

'''


@csrf_exempt
@require_POST
def addImage(request):
    # Validate input
    # print(request.POST)
    if not ('image_name' in request.POST and 'path' in request.POST and 'categories' in request.POST):
        return HttpResponseBadRequest("Missing required input.")
    # print(request.POST['categories'])
    try:
        request_categories = json.loads(request.POST['categories'])
    except json.JSONDecodeError:
        return HttpResponseBadRequest(
            'Category list could not be understood. Please provide a list in the format: '
            '["category_1", "category_2", ... , "category_n"]. Please note that you may need to '
            'escape quotes with a backslash (\\)')
    if not request_categories:  # if empty
        return HttpResponseBadRequest("Missing a category, 'categories' field required to be nonempty list")
    for category in request_categories:
        if category == "":
            HttpResponseBadRequest("A category cannot be an empty string")
    # print(request_categories)
    # Determine wheter 'path' is URL or file path
    path = request.POST['path']
    if path[-1] != '/' and path[-1] != '\\':
        path += '/'
    url_check = URLValidator()
    width, height = None, None
    try:
        url_check(path)
        width, height = PILImage.open(StringIO(urllib.request.urlopen(path + request.POST['image_name']).read())).size
    except ValidationError as e:
        # Validate image and get width, height
        try:
            width, height = PILImage.open(path + request.POST['image_name']).size
        except IOError:
            return HttpResponseBadRequest(
                "Image file %s cannot be found or the image cannot be opened and identified.\n" % (
                        path + request.POST['image_name']))

        # Convert Filepath to webpath if necessary
        ##Check if path is in STATIC_ROOT (https://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory)
        root = os.path.join(os.path.realpath(settings.STATIC_ROOT), '')
        path_dir = os.path.realpath(request.POST['path'])
        # print(path_dir)
        if not os.path.commonprefix([root, path_dir]) == root:
            return HttpResponseBadRequest(
                "Image in unreachable location. Make sure that it is in a subdirectory of " + settings.STATIC_ROOT + ".\n")
        path = os.path.relpath(path_dir, root)
        path = settings.STATIC_URL + path
        if path[-1] != '/' and path[-1] != '\\':
            path += '/'

    # Get or create ImageSourceType
    desc = request.POST.get('source_description', default="human")
    imageSourceTypeList = ImageSourceType.objects.all().filter(description=desc)
    if imageSourceTypeList:
        sourceType = imageSourceTypeList[0]
    else:
        sourceType = ImageSourceType(description=request.POST.get('source_description', default="human"),
                                     pub_date=datetime.now())
        sourceType.save()

    # Get CategoryType entries or add if necessary.
    category_list = [CategoryType.objects.get_or_create(category_name=category)[0] for category in request_categories]
    for cat in category_list:
        print(cat.color)
        if not cat.color:
            cat.color = models.get_color()
            cat.color = get_color()
            cat.save()

    imageList = Image.objects.all().filter(name=request.POST['image_name'], path=path,
                                           description=request.POST.get('description', default=''), source=sourceType)
    if imageList:
        img = imageList[0]
    else:
        img = Image(name=request.POST['image_name'], path=path, description=request.POST.get('description', default=''),
                    source=sourceType, width=width, height=height)
        img.save()

    # print(category_list)
    img.categoryType.add(*category_list)
    # imgLabel = ImageLabel(parentImage=img, categoryType=categoryType, pub_date=datetime.now())
    # imgLabel.save()
    return HttpResponse("Added image " + request.POST['image_name'] + '\n')


@csrf_exempt
@require_POST
def cleanUpAndFixImages(request):
    helper_ops.fixAllImagePaths()
    helper_ops.updateAllImageSizes(request.scheme, request.get_host())
    return HttpResponse("All images rows cleaned up and fixed.")


'''
Request: POST
{
    path: location of image (not including image name itself. E.g. '/home/self/image-location/'). REQUIRED
    image_name:name of image REQUIRED
    description: A description CHANGED IF INCLUDED
    source_description: Description of image_source. CHANGED IF INCLUDED
    add_category: Category of the image (e.g. 'apple') to be added to the list. UPDATED IF INCLUDED
    remove_category: Category of the image (e.g. 'apple') to be added to the list. UPDATED IF INCLUDED
}

'''


@csrf_exempt
@require_POST
def updateImage(request):
    # Validate input
    if not ('image_name' in request.POST and 'path' in request.POST):
        return HttpResponseBadRequest("Missing required input")
    image = Image.objects.all().filter(name=request.POST['image_name'], path=request.POST['path'])[0]
    if 'description' in request.POST:
        image.description = request.POST['description']
    if 'source-description' in request.POST:
        image.description = request.POST['source-description']
    if 'add_category' in request.POST:
        cats = CategoryType.objects.all().filter(category_name=request.POST['add_category'])
        cat = None
        if not cats or not image.filter(categoryType=cats[0]):
            if cats:
                cat = cats[0]
            else:
                cat = CategoryType(category_name=request.POST['add_category'])
                cat.save()
            image.categoryType.add(cat)
    if 'remove_category' in request.POST:
        cats = CategoryType.objects.all().filter(category_name=request.POST['remove_category'])
        if cats and image.filter(categoryType=cats[0]):
            image.categoryType.remove(cat)
    return HttpResponse("Made changes")


@csrf_exempt
@require_POST
def convertAll(request):
    from webclient.image_ops.convert_images import convertAll
    convertAll(request.POST.get('reconvert', False))
    return HttpResponse('Ok')


@csrf_exempt
@require_GET
def unlabeledImages(request):
    images = Image.objects.all().filter(imagelabel__isnull=True).distinct()
    return HttpResponse("Images: " + ','.join(map(str, images)))


@csrf_exempt
@require_GET
def numImageLabels(request):
    images = Image.objects.all().annotate(num=Count('imagelabel')).order_by('-num')
    # print(images)
    return HttpResponse("Images: " + ','.join(map(str, images)))


@csrf_exempt
@require_POST
def combineAllImages(request):
    thresholdPercent = int(request.POST.get('thresholdPercent', 50))
    from webclient.image_ops.convert_images import combineAllLabels
    # for img in Image.objects.all():
    #    combineImageLabels(img, thresholdPercent)
    combineAllLabels(thresholdPercent)
    return HttpResponse("OK")


@csrf_exempt
@require_POST
def calculateEntropyMap(request):
    import webclient.image_ops.crop_images
    images = Image.objects.all()
    webclient.image_ops.crop_images.calculate_entropy_map(images[0], images[0].categoryType.all()[0])
    return HttpResponse('ok')


############
# Image Views
############
re_image_path = re.compile(r'/%s%s(.*)' % ('webclient', settings.STATIC_URL))


@require_GET
def get_overlayed_combined_image(request, image_label_id):
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    image_label = ImageLabel.objects.filter(id=image_label_id)
    if not image_label:
        return HttpResponseBadRequest('Bad image_label_id: ' + image_label_id)
    image_label = image_label[0]
    _user = User.objects.filter(username=user)[0]
    if (str(user) == str(image_label.labeler)) or (_user.is_staff) or _user.is_superuser:
        image = image_label.parentImage
        try:
            blob = render_SVG_from_label(image_label)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return HttpResponseServerError(str(e))

        # image with annotations has been saved as blob
        foreground = PILImage.open(io.BytesIO(blob)).convert('RGBA')
        output = io.BytesIO()
        foreground.save(output, format='png')
        return HttpResponse(output.getvalue(), content_type="image/png")
    else:
        return HttpResponseBadRequest('Authentication error')


@csrf_exempt
@require_GET
def get_overlayed_category_image(request, category_label_id):
    category_label = CategoryLabel.objects.filter(id=category_label_id)
    if not category_label:
        return HttpResponseBadRequest('Bad category_label_id: ' + category_label_id)
    category_label = category_label[0]
    image = category_label.parent_label.parentImage
    try:
        blob = render_SVG_from_label(category_label)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return HttpResponseServerError(str(e))
    foreground = PILImage.open(io.BytesIO(blob))
    foreground = foreground.convert('RGBA')
    # path = re.match(re_image_path, image.path).groups(1)[0]
    path = image.path
    # background = PILImage.open(path + image.name).convert('RGB')
    # print(request.get_host())
    # fd = urllib.request.urlopen(path+image.name)
    # image_file = io.BytesIO(fd.read())
    url = 'http://' + request.get_host() + path + image.name
    background = PILImage.open(urlopen(url))
    background.paste(foreground, (0, 0), foreground)
    output = io.BytesIO()
    background.save(output, format='png')
    return HttpResponse(output.getvalue(), content_type="image/png")


re_transform_xy = re.compile(
    r'(?P<prefix><circle[^\>]*transform="[^\>]*translate\()(?P<x>\d*),(?P<y>\d*)(?P<suffix>[^\>]*\)"[^\>]*/>)')


@csrf_exempt
@require_POST
def fix_label_location(request):
    for label in ImageLabel.objects.all():
        shape = label.labelShapes
        label.labelShapes = re.sub(re_transform_xy, subtractPadding, shape)
        label.save()
    return HttpResponse("Changed")


def subtractPadding(matchobj):
    try:
        s = '%s%d,%d%s' % (matchobj.group('prefix'),
                           int(matchobj.group('x')) - 20,
                           int(matchobj.group('y')) - 20,
                           matchobj.group('suffix'))
    except ValueError:
        s = matchobj.group(0)
    return s


@csrf_exempt
@require_POST
def print_label_data(request):
    with open('imageLabel_data.csv', 'w') as csvfile:
        fieldnames = ['parentImage_name', 'parentImage_path', 'categoryType',
                      'pub_date', 'labeler', 'iw_x', 'iw_y', 'iw_width', 'iw_height', 'timeTaken',
                      'if_brightness', 'if_contrast', 'if_saturation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for label in ImageLabel.objects.all():
            imageFilter = ImageFilter.objects.all().get(imageLabel=label)
            labelDict = {
                'parentImage_name': label.parentImage.name,
                'parentImage_path': label.parentImage.path,
                'categoryTypes': [cat_label.categoryType.category_name for cat_label in label.categorylabel_set],
                'pub_date': label.pub_date,
                'labeler': label.labeler,
                'iw_x': label.imageWindow.x,
                'iw_y': label.imageWindow.y,
                'iw_width': label.imageWindow.width,
                'iw_height': label.imageWindow.height,
                'timeTaken': label.timeTaken,
                'if_brightness': imageFilter.brightness,
                'if_contrast': imageFilter.contrast,
                'if_saturation': imageFilter.saturation,
            }
            writer.writerow(labelDict)
    return HttpResponse("Printed")


@csrf_exempt
@require_POST
def add_tiled_label(request):
    # print(request['POST'])
    request_json = json.load(request)

    tiled_label = TiledLabel()
    tiled_label.northeast_Lat = request_json["northeast_lat"]
    tiled_label.northeast_Lng = request_json["northeast_lng"]
    tiled_label.southwest_Lat = request_json["southwest_lat"]
    tiled_label.southwest_Lng = request_json["southwest_lng"]
    tiled_label.zoom_level = request_json["zoom_level"]
    tiled_label.category = CategoryType.objects.get(category_name=request_json["category_name"])
    tiled_label.label_type = \
        [K for (K, v) in TiledGISLabel.label_type_enum if request_json["label_type"].lower() == v.lower()][0]
    json_ = request_json["geoJSON"]
    tiled_label.label_json = json_
    print(json_["geometry"])
    print(type(json_["geometry"]))
    tiled_label.geometry = GEOSGeometry(str(json_["geometry"]))
    tiled_label.save()

    # Send the response

    resp_obj = {}
    resp_obj["status"] = "success"
    resp_obj["category"] = request_json["category_name"]
    return JsonResponse(resp_obj)


from django.db.models import Q


@csrf_exempt
def get_all_tiled_labels(request):
    xmin = float(request.GET.get("southwest_lng"))
    ymin = float(request.GET.get("southwest_lat"))
    xmax = float(request.GET.get("northeast_lng"))
    ymax = float(request.GET.get("northeast_lat"))
    bbox = (xmin, ymin, xmax, ymax)
    current_bbox = Polygon.from_bbox(bbox)

    response_obj = []
    prev_boxes_wkt = request.session.get('prev_multipoly')
    previous_boxes = MultiPolygon.from_ewkt(prev_boxes_wkt)
    new_polygon = Polygon()
    for polygon in previous_boxes:
        new_polygon = new_polygon.union(polygon)

    query_set = TiledGISLabel.objects.filter(geometry__within=current_bbox).filter(~Q(geometry__within=new_polygon))

    for tiled_label in query_set:
        response_dict = {}
        response_dict["northeast_lat"] = tiled_label.northeast_Lat
        response_dict["northeast_lng"] = tiled_label.northeast_Lng
        response_dict["southwest_lat"] = tiled_label.southwest_Lat
        response_dict["southwest_lng"] = tiled_label.southwest_Lng
        response_dict["zoom_level"] = tiled_label.zoom_level
        response_dict["label_type"] = tiled_label.get_label_type_display()
        response_dict["geoJSON"] = tiled_label.label_json
        response_dict["category"] = tiled_label.category.category_name
        response_obj.append(response_dict)

    previous_boxes.append(current_bbox)
    request.session['prev_multipoly'] = str(previous_boxes)
    return JsonResponse(response_obj, safe=False)


import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

import base64
import math


@csrf_exempt
def get_histogram_for_window(request):
    xmin = float(request.GET.get("southwest_lng"))
    ymin = float(request.GET.get("southwest_lat"))
    xmax = float(request.GET.get("northeast_lng"))
    ymax = float(request.GET.get("northeast_lat"))
    number_of_bins = int(request.GET.get("number_of_bins"))

    bbox = (xmin, ymin, xmax, ymax)
    current_bbox = Polygon.from_bbox(bbox)
    result_set = []
    query_set = TiledGISLabel.objects.filter(geometry__within=current_bbox)
    for polygon in query_set:
        geometry = polygon.geometry
        geometry.srid = 4326
        geometry.transform(26911)
        area = geometry.area
        result_set.append(area)

    area_list = np.asarray(result_set)
    f = plt.figure(figsize=(4, 3))
    plt.clf()
    plt.hist((area_list), number_of_bins)
    plt.xlabel('Rock area (sq. m)')
    plt.ylabel('Count')
    plt.tight_layout()
    response = io.BytesIO()
    plt.savefig(response, format='png')
    response.seek(0)
    encoded_string = base64.b64encode(response.read())
    return HttpResponse(encoded_string, 'contentType: image/PNG')


def get_window_tiled_labels(request):
    response_obj = []
    float_tollerance = 1e-5
    print(request)
    request_json = json.load(request)
    print(request_json)

    tileLabels = TiledLabel.objects.filter(
        northeast_Lat__range=(
        request_json["northeast_lat"] - float_tollerance, request_json["northeast_lat"] + float_tollerance),
        northeast_Lng__range=(
        request_json["northeast_lng"] - float_tollerance, request_json["northeast_lat"] + float_tollerance),
        southwest_Lat__range=(
        request_json["southwest_lat"] - float_tollerance, request_json["northeast_lat"] + float_tollerance),
        southwest_Lng__range=(
        request_json["southwest_lng"] - float_tollerance, request_json["northeast_lat"] + float_tollerance))

    for tiled_label in tileLabels:
        response_dict = {}
        response_dict["northeast_lat"] = tiled_label.northeast_Lat
        response_dict["northeast_lng"] = tiled_label.northeast_Lng
        response_dict["southwest_lat"] = tiled_label.southwest_Lat
        response_dict["southwest_lng"] = tiled_label.southwest_Lng
        response_dict["zoom_level"] = tiled_label.zoom_level
        response_dict["label_type"] = tiled_label.get_label_type_display()
        response_dict["geoJSON"] = tiled_label.label_json
        response_dict["category"] = tiled_label.category.category_name
        response_obj.append(response_dict)
    return JsonResponse(response_obj, safe=False)


@csrf_exempt
@require_POST
def add_train_image_label(request):
    request_json = json.load(request)
    image_name = request_json["image_name"]
    train_image_base64 = request_json["image_blob"]
    train_label_base64 = request_json["mask_blob"]

    train_image_base64 = re.search(r'base64,(.*)', train_image_base64).group(1)
    train_label_base64 = re.search(r'base64,(.*)', train_label_base64).group(1)
    train_image_blob = io.BytesIO(base64.b64decode(train_image_base64))
    train_label_blob = io.BytesIO(base64.b64decode(train_label_base64))
    train_image = PILImage.open(train_image_blob)
    train_label = PILImage.open(train_label_blob)

    train_label = np.array(train_label)
    # train_label[train_label != 221] = 255
    # train_label[train_label == 221] = 0

    train_label = PILImage.fromarray(train_label)

    img_name = "/home/jdas/aerialapps/trainset/" + request_json["category_name"] + "/" + image_name + ".png"
    label_name = "/home/jdas/aerialapps/trainset/" + request_json["category_name"] + "/" + image_name + "_label.png"

    train_image.save(img_name)
    train_label.save(label_name)
    print("saved: " + img_name)
    print("saved: " + label_name)

    resp_obj = {}
    resp_obj["status"] = "success"

    return JsonResponse(resp_obj)


@csrf_exempt
@require_POST
def add_all_tiled_categories(request):
    for cat_name in ["amp", "tap", "car", "house", "tree", "road"]:
        category = CategoryType()
        category.category_name = cat_name
        category.color = get_color()
        category.label_type = "A"
        category.save()

    return HttpResponse("Success")


@csrf_exempt
@require_POST
def delete_tile_label(request):
    float_tollerance = 1e-5
    print(request)
    request_list = json.load(request)
    print(request_list)
    to_delete = []
    for request in request_list:
        northeast_Lat = request.get("northeast_lat")
        northeast_Lng = request.get("northeast_lng")
        southwest_Lat = request.get("southwest_lat")
        southwest_Lng = request.get("southwest_lng")

        category_name = request.get("category_name")
        if northeast_Lat is None or northeast_Lng is None or \
                southwest_Lat is None or southwest_Lng is None or category_name is None:
            return HttpResponseBadRequest("Missing required field")
        category = CategoryType.objects.get(category_name=category_name)
        jsonStr = json.loads(request.get('geojson'))
        s = str(jsonStr["geometry"])
        poly = GEOSGeometry(s)
        tile_label = TiledGISLabel.objects.filter(category=category).filter(geometry__equals=poly)

        if not tile_label:
            return HttpResponseBadRequest('ERROR' + category_name)
        if len(tile_label) > 1:
            return HttpResponseBadRequest("Request ambigous")
        to_delete.append(tile_label[0])

    # Make sure all objects are okay to delete first
    # If there's an error don't change database
    for label in to_delete:
        label.delete()
    return JsonResponse('Success', safe=False)


@csrf_exempt
@require_POST
def add_tileset(request):
    if 'base_location' not in request.POST:
        return HttpResponseBadRequest("base_location required for tileset")
    tileset = TileSet(base_location=request.POST['base_location'])
    tileset.save()

    url_val = URLValidator()
    try:
        url_val(tileset.base_location)
        url_location = True
    except ValidationError:
        url_location = False

    if url_location and requests.head(
            tileset.base_location).status_code != 200:
        return HttpResponseBadRequest("Error: {} must be value url".format(tileset.base_location))
    valid_zoom_levels = [z for z in range(30) if request.head(urljoin(tileset.base_location, z)).status_code == 200]


@csrf_exempt
@require_GET
def get_tiled_label_coordinates(request):
    lat_long = [{'category': tl.category.category_name,
                 'latitude': (tl.northeast_Lat + tl.southwest_Lat) / 2,
                 'longitude': (tl.northeast_Lng + tl.southwest_Lng) / 2}
                for tl in TiledLabel.objects.all()]
    # print(lat_long)
    return JsonResponse(lat_long, safe=False)


@csrf_exempt
@require_GET
def get_combined_label_geojson(request):
    combined_dict = {}
    combined_dict['type'] = 'FeatureCollection'
    combined_dict['features'] = [label.label_json for label in TiledLabel.objects.all()]
    print(combined_dict)
    return JsonResponse(combined_dict)


@csrf_exempt
@require_POST
def add_new_category(request):
    data = request.POST.get("data")
    color = get_color()
    if data != "":
        if CategoryType.objects.all().filter(category_name=data).count() == 0:
            category = CategoryType()
            category.category_name = data
            category.color = color
            category.label_type = "A"
            category.save()
        else:
            return JsonResponse({"result": "failure", "reason": data + " already exists."}, safe=False)

    return JsonResponse({"result": "success", "data": data, "color": str(color)}, safe=False)
