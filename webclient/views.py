import base64
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from io import StringIO
from random import randint
from urllib.parse import urljoin
from urllib.request import urlopen
import numpy as np
import requests
import torch
import torchvision
from PIL import Image as PILImage
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.validators import URLValidator
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.template import loader
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from rasterio.features import shapes as rasterio_shapes
from shapely.geometry import shape as shapely_shape
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.models.detection.rpn import AnchorGenerator
import matplotlib.pyplot as plt
from webclient.image_ops import crop_images
from webclient import helper_ops
from webclient.image_ops.convert_images import convert_label_to_image_stream, convert_image_labels_to_json, \
    convert_image_labels_to_svg_array, combine_all_labels
from webclient.models import Image, CategoryType, CategoryLabel, User, Labeler, ImageWindow, ImageLabel, GEOSGeometry
from webclient.models import ImageSourceType, ImageFilter, datetime, get_color, TileSet, TiledLabel, TiledGISLabel, \
    RasterImage

MODEL_SELECTED = None


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
    context = {
        'categories': {cat.category_name: str(cat.color) for cat in CategoryType.objects.all()}
    }
    request.session['prev_multipoly'] = str(MultiPolygon())
    return HttpResponse(template.render(context, request))


@login_required
@require_POST
@csrf_exempt
def create_mask(request):
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    post_request = json.load(request)
    labels = post_request['labels']
    if len(labels) == 0:
        return JsonResponse({"status": "failure", "message": "No images selected"}, safe=False)
    _user = User.objects.filter(username=user)[0]
    labels_db = []
    for _label in labels:
        _user = User.objects.filter(username=_label["user"])[0]
        _labeler = Labeler.objects.filter(user=_user)[0]
        _image_window = ImageWindow.objects.filter(width=_label["width"],
                                                   height=_label["height"],
                                                   x=_label["padding_x"],
                                                   y=_label["padding_y"])[0]
        _s = _label["parent_image"].split("/")
        _parent_image_name = _s[-1]
        _parent_image_path = "/".join(_s[:-1]) + "/"
        _image = Image.objects.filter(name=_parent_image_name, path=_parent_image_path)[0]
        _label_db = ImageLabel.objects.filter(labeler=_labeler,
                                              parentImage=_image,
                                              timeTaken=_label["timetaken"],
                                              imageWindow=_image_window
                                              )
        if len(_label_db) == 1:
            labels_db.append(_label_db[0])
    file_path = convert_image_labels_to_json(user, labels_db)
    file_path = file_path.replace("media-root", "media")

    return JsonResponse({"status": "success", "message": file_path}, safe=False)


@login_required
def display_annotations(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

    _user = User.objects.filter(username=user)[0]
    if _user.is_staff or _user.is_superuser:
        labels = ImageLabel.objects.filter()
    else:
        try:
            labeler = Labeler.objects.get(user=user)
        except Labeler.DoesNotExist:
            labeler = Labeler(user=user)
            labeler.save()
        labels = ImageLabel.objects.filter(labeler=labeler)
    response = dict()
    count = 1

    for _label in labels:
        response[count] = dict()
        response[count]["parent_image"] = _label.parentImage.path + _label.parentImage.name
        response[count]["height"] = _label.imageWindow.height
        response[count]["width"] = _label.imageWindow.width
        response[count]["padding_x"] = _label.imageWindow.x
        response[count]["padding_y"] = _label.imageWindow.y
        response[count]["timetaken"] = _label.timeTaken
        soup = BeautifulSoup(_label.combined_labelShapes)
        circles = soup.find_all('circle')
        poly = soup.find_all('polygon')
        paths = soup.find_all('path')
        ellipse = soup.find_all('ellipse')
        shapes = paths + poly + circles + ellipse
        response[count]["labelcount"] = len(shapes)
        response[count]["number"] = _label.id
        response[count]["labeler"] = str(_label.labeler)
        count += 1

    output = {"status": "success", "message": response}
    return JsonResponse(output, safe=False)


@csrf_exempt
@login_required
def edit_image_label(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    image_label_id = request.GET['image_id']
    image_label = ImageLabel.objects.filter(id=image_label_id)[0]
    img = image_label.parentImage

    category_labels = {}
    soup = BeautifulSoup(image_label.combined_labelShapes)
    circles = soup.find_all('circle')
    poly = soup.find_all('polygon')
    paths = soup.find_all('path')
    ellipse = soup.find_all('ellipse')
    shapes = paths + poly + circles + ellipse
    svg_strings = []
    for cat_label in CategoryLabel.objects.filter(parent_label=image_label):
        category_labels[cat_label.categoryType.category_name] = cat_label.labelShapes
        soup = BeautifulSoup(cat_label.labelShapes)
        paths = soup.find_all('polygon')
        # convert to path data add M in the beginning and z and the end
        for path in paths:
            svg_strings.append(("M" + path['points'] + "z", cat_label.categoryType.category_name, "polygon"))

        paths = soup.find_all('path')

        for path in paths:
            svg_strings.append((path.get('d'), cat_label.categoryType.category_name, "path"))

        paths = soup.find_all('circle')
        for path in paths:
            svg_strings.append(({'radius': float(path['r']),
                                 'cx': float(path['cx']),
                                 'cy': float(path['cy'])
                                 },
                                cat_label.categoryType.category_name, "circle"))

        paths = soup.find_all('ellipse')
        for path in paths:
            svg_strings.append(({'rx': float(path['rx']),
                                 'ry': float(path['ry']),
                                 'cx': float(path['cx']),
                                 'cy': float(path['cy'])
                                 }, cat_label.categoryType.category_name, "ellipse"))

    subimage = {'width': image_label.imageWindow.width, 'height': image_label.imageWindow.height,
                'padding': 0, 'x': image_label.imageWindow.x, 'y': image_label.imageWindow.y}

    response = {'path': img.path, 'metadata': {}, 'image_name': img.name,
                'categories': [c.category_name for c in CategoryType.objects.all()],
                'shapes': [c.get_label_type_display() for c in img.categoryType.all()],
                'colors': [str(c.color) for c in CategoryType.objects.all()],
                'subimage': subimage,
                'label_list': image_label.combined_labelShapes,
                'category_labels': category_labels,
                'drawn_labels': svg_strings,
                'count': len(shapes),
                'status': 'success',
                'message': 'Loading the annotations'}
    return JsonResponse(response, safe=False)


@csrf_exempt
@login_required
def select_models(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    get_request = json.load(request)
    global MODEL_SELECTED
    MODEL_SELECTED = "/app/models/" + get_request["model_id"]
    return JsonResponse({"status": "success", "message": "Model {} selected".format(get_request["model_id"])},
                        safe=False)


@login_required
def display_models(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

    _user = User.objects.filter(username=user)[0]

    try:
        labeler = Labeler.objects.get(user=user)
    except Labeler.DoesNotExist:
        labeler = Labeler(user=user)
        labeler.save()

    response = dict()
    count = 1
    files = os.listdir("/app/models")
    for model_file in files:
        response[count] = dict()
        response[count]["file_name"] = str(model_file)
        count += 1
    output = {"status": "success", "message": response}
    return JsonResponse(output, safe=False)


@csrf_exempt
def apply_labels(request):
    try:
        get_request = json.load(request)
    except json.JSONDecodeError:
        print("Could not decode")
        return HttpResponseBadRequest("Could not decode JSON")
    try:
        label_list_ = get_request['label_list']
        category_labels = get_request['category_labels']
        image_name = get_request['image_name']
        path = get_request['path']
        prev_label = get_request['editLabel']
        image_filters = get_request['image_filters']
        sub_image = get_request['subimage']
        time_taken = get_request['timeTaken']
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
    if int(prev_label) != -1 and len(ImageLabel.objects.filter(id=int(prev_label))) > 0:
        image_label = ImageLabel.objects.filter(id=prev_label)[0]
        image_label.combined_labelShapes = label_list_
        image_label.pub_date = datetime.now()
        image_label.timeTaken = int(image_label.timeTaken) + time_taken
        image_label.save()
        CategoryLabel.objects.filter(parent_label=image_label).delete()
        response = {"status": "success", "message": "Successfully updated annotations"}
    else:
        parent_image_ = Image.objects.all().filter(name=image_name, path=path)

        image_window_list = ImageWindow.objects.all().filter(
            x=sub_image['x'], y=sub_image['y'], width=sub_image['width'], height=sub_image['height'])
        if image_window_list:
            image_window = image_window_list[0]
        else:
            image_window = ImageWindow(x=sub_image['x'], y=sub_image['y'],
                                       width=sub_image['width'], height=sub_image['height'])
            image_window.save()

        source_type_list = ImageSourceType.objects.all().filter(description="human")
        if source_type_list:
            source_type = source_type_list[0]
        else:
            source_type = ImageSourceType(description="human", pub_date=datetime.now())
            source_type.save()

        image_label = ImageLabel(parentImage=parent_image_[0], combined_labelShapes=label_list_,
                                 pub_date=datetime.now(),
                                 labeler=labeler, imageWindow=image_window,
                                 timeTaken=time_taken)
        image_label.save()
        response = {"status": "success", "message": "Successfully added annotations"}

    for category_name, _ in category_labels.items():
        category_type_list = CategoryType.objects.all().filter(category_name=category_name)
        if category_type_list:
            category_type = category_type_list[0]
        else:
            category_type = CategoryType(category_name=category_name, pub_date=datetime.now(), color=get_color())
            category_type.save()

        category_label = CategoryLabel(categoryType=category_type,
                                       labelShapes=category_labels[category_name], parent_label=image_label)
        category_label.save()
        image_filter_obj = ImageFilter(brightness=image_filters['brightness'],
                                       contrast=image_filters['contrast'],
                                       saturation=image_filters['saturation'],
                                       imageLabel=image_label,
                                       labeler=labeler)
        image_filter_obj.save()

    return JsonResponse(response)


@require_GET
def load_labels(request):
    if 'image_name' not in request.GET or 'path' not in request.GET:
        print('Path and Image Name required', (request.GET['path'] + ' ' + request.GET['image_name']))
        return HttpResponseBadRequest('Path and Image Name required')

    image = Image.objects.all().filter(name=request.GET['image_name'], path=request.GET['path'])

    if not image:
        return HttpResponseBadRequest("No such image found")
    label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    response_text = ''
    if label_list:
        response_text = response_text + label_list.labelShapes
    return JsonResponse(response_text, safe=False)


@require_GET
def get_info(request):
    if 'image_name' not in request.GET or 'path' not in request.GET:
        return HttpResponseBadRequest("Missing 'image_name or 'path'")
    parent_image_ = request.GET['image_name']
    source_type_list = ImageSourceType.objects.all().filter(description="human")
    if source_type_list:
        source_type = source_type_list[0]
    else:
        source_type = ImageSourceType(description="human", pub_date=datetime.now())
        source_type.save()

    image = Image.objects.all().filter(name=parent_image_)
    if not image:
        return HttpResponseBadRequest(
            "Could not find image with name " + request.GET['image_name'] + " and path " + request.GET['path'])

    label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    response = {}
    if label_list:
        response['label'] = label_list.labelShapes
    else:
        response['label'] = ''
    response['path'] = image[0].path
    response['categories'] = [c.category_name for c in image[0].categoryType.all()]
    return JsonResponse(response, safe=False)


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
def get_lola_crater_annotations(request):
    # get parameters from request
    upper_left_latitude = float(request.GET['UpperLeftLatitude'])
    upper_left_longitude = float(request.GET['UpperLeftLongitude'])
    lower_right_latitude = float(request.GET['LowerRightLatitude'])
    lower_right_longitude = float(request.GET['LowerRightLongitude'])

    min_latitude = min(upper_left_latitude, lower_right_latitude)
    max_latitude = max(upper_left_latitude, lower_right_latitude)
    min_longitude = min(upper_left_longitude, lower_right_longitude)
    max_longitude = max(upper_left_longitude, lower_right_longitude)

    folder_path = os.path.realpath(settings.STATIC_ROOT)
    filename = folder_path + "/lroc_crater_db.csv"

    crater_list = []
    with open(filename) as CSV_FILE:
        reader = csv.reader(CSV_FILE)
        next(reader)
        for line in reader:
            if (max_latitude >= float(line[1]) >= min_latitude and
                    max_longitude >= float(line[0]) >= min_longitude):
                crater_list.append(line)

    return JsonResponse(crater_list, safe=False)


# function to get image metadata from json file
# This function assumes json files are in static_root
def get_image_metadata(file):
    with open(file, 'r') as json_file:
        metadata = json.load(json_file)
    return metadata


def get_model_instance_segmentation(num_classes, image_mean, image_std, stats=False):
    # load an instance segmentation model pre-trained pre-trained on COCO

    model = torchvision.models.detection.maskrcnn_resnet50_fpn(pretrained=True)
    # get number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    # replace the pre-trained head with a new one
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    # the size shape and the aspect_ratios shape should be the same as the shape in the loaded model
    anchor_generator = AnchorGenerator(sizes=((32,), (64,), (128,), (256,), (512,)),
                                       aspect_ratios=(
                                           (0.5, 1.0, 2.0), (0.5, 1.0, 2.0), (0.5, 1.0, 2.0), (0.5, 1.0, 2.0),
                                           (0.5, 1.0, 2.0)))
    model.rpn.anchor_generator = anchor_generator

    if stats:
        model.transform.image_mean = image_mean
        model.transform.image_std = image_std
    # now get the number of input features for the mask classifier
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    # and replace the mask predictor with a new one
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask,
                                                       hidden_layer,
                                                       num_classes)
    model.roi_heads.detections_per_img = 256

    return model


def get_masks(image_path, x, y, width, height):
    global MODEL_SELECTED
    if MODEL_SELECTED is None:
        return {"status": "failure", "message": "Select a model to predict"}, None
    image = PILImage.open(image_path).convert("RGB")
    image = np.array(image)
    image = image[x:x + height, y:y + width]
    image = torch.from_numpy(image / 255.0).float()
    image = image.permute((2, 0, 1))

    if torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')

    num_classes = len(CategoryType.objects.all()) + 1
    image_mean = [0.34616187074865956, 0.34616187074865956, 0.34616187074865956]
    image_std = [0.10754412766560431, 0.10754412766560431, 0.10754412766560431]

    mask_rcnn = get_model_instance_segmentation(num_classes, image_mean, image_std, stats=True)
    mask_rcnn.to(device)
    mask_rcnn.eval()

    model_path = MODEL_SELECTED
    mask_rcnn.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))

    prediction = mask_rcnn(image.unsqueeze(0).to(device))[0]

    boxes_ = prediction["boxes"].cpu().detach().numpy().astype(int)
    boxes = np.empty_like(boxes_)
    boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3] = boxes_[:, 1], boxes_[:, 0], boxes_[:, 3], boxes_[:, 2]
    labels = prediction["labels"].cpu().detach().numpy()
    scores = prediction["scores"].cpu().detach().numpy()
    masks = prediction["masks"]
    indices = scores > 0.98
    labels = labels[indices]
    masks = masks[indices].squeeze(1)
    masks = (masks.permute((1, 2, 0)).cpu().detach().numpy() > 0.5).astype(np.uint8)
    masks = masks * labels
    return masks, labels


# function to return AI predictions
@csrf_exempt
@require_GET
def get_annotations(request):
    # return a list of svg strings
    image_path = request.GET['image_name']
    width = request.GET['width']
    height = request.GET['height']
    masks, labels = get_masks('/app/webclient' + image_path, int(request.GET['x']), int(request.GET['y']), int(width),
                              int(height))
    if "status" in masks:
        return JsonResponse(masks, safe=False)
    svg_strings = []
    categories = ["background"]
    for category in CategoryType.objects.all():
        categories.append(str(category.category_name))
    for _, category in enumerate(categories):
        if _ == 0:  # skip background
            continue
        for i in range(masks.shape[2]):
            mask = masks[:, :, i]
            mask[mask == 0] = -9999
            prediction = mask == _
            mask[mask == _] = 1
            mask = mask.astype(np.int16, copy=False)
            shapes = rasterio_shapes(mask, mask=prediction)
            shapes_list = list(shapes)
            if len(shapes_list) > 0 and len(shapes_list[0]) > 0:
                svg_string = shapely_shape(shapes_list[0][0])._repr_svg_()
                soup = BeautifulSoup(svg_string)
                paths = soup.find_all('path')
                svg_strings.append((paths[0].get('d'), category))
    resp = {"status": "success", "message": svg_strings}
    return JsonResponse(resp, safe=False)


@require_GET
def get_new_image(request):
    if len(Image.objects.all()) == 0:
        return HttpResponseBadRequest("No images in database")

    labels_per_image = crop_images.NUM_WINDOW_COLS * \
                       crop_images.NUM_WINDOW_ROWS * crop_images.NUM_LABELS_PER_WINDOW

    images = Image.objects.all().annotate(count=Count('imagelabel')).filter(count__lt=labels_per_image)
    user = request.user

    ignore_max_count = bool(user.groups.filter(name='god').exists())

    images = images.order_by('count').reverse()

    img = None
    sub_image = None
    for _ in images:
        indices = randint(0, len(images) - 1)
        i = images[indices]
        sub_image = crop_images.getImageWindow(i, request.user, ignore_max_count=ignore_max_count)
        if sub_image is not None:
            img = i
            break

    if not img:
        return HttpResponseBadRequest("Could not find image to serve")

    # fetch image metadata from xml file
    metadata_file = os.path.realpath(settings.STATIC_ROOT) + '/life-images-json/' + img.name
    image_metadata = {}
    if os.path.exists(metadata_file):
        image_metadata = get_image_metadata(metadata_file)
        print("Log: Colors in getNewImage: ", img.categoryType.all())

    response = {'path': img.path,
                'metadata': image_metadata,
                'image_name': img.name,
                'categories': [c.category_name for c in CategoryType.objects.all()],
                'shapes': [c.get_label_type_display() for c in img.categoryType.all()],
                'colors': [str(c.color) for c in CategoryType.objects.all()],
                'subimage': sub_image
                }

    return JsonResponse(response)


@csrf_exempt
@require_POST
def add_image(request):
    if not ('image_name' in request.POST and 'path' in request.POST and 'categories' in request.POST):
        return HttpResponseBadRequest("Missing required input.")

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

    path = request.POST['path']
    if path[-1] != '/' and path[-1] != '\\':
        path += '/'
    url_check = URLValidator()
    try:
        url_check(path)
        width, height = PILImage.open(StringIO(urllib.request.urlopen(path + request.POST['image_name']).read())).size
    except ValidationError as value_error:
        print(value_error)
        try:
            width, height = PILImage.open(path + request.POST['image_name']).size
        except IOError:
            return HttpResponseBadRequest(
                "Image file %s cannot be found or the image cannot be opened and identified.\n" % (
                        path + request.POST['image_name']))

        root = os.path.join(os.path.realpath(settings.STATIC_ROOT), '')
        path_dir = os.path.realpath(request.POST['path'])

        if not os.path.commonprefix([root, path_dir]) == root:
            return HttpResponseBadRequest(
                "Image in unreachable location. Make sure that it is in a subdirectory of " + settings.STATIC_ROOT + ".\n")
        path = os.path.relpath(path_dir, root)
        path = settings.STATIC_URL + path
        if path[-1] != '/' and path[-1] != '\\':
            path += '/'

    # Get or create ImageSourceType
    desc = request.POST.get('source_description', default="human")
    image_source_type_list = ImageSourceType.objects.all().filter(description=desc)
    if image_source_type_list:
        source_type = image_source_type_list[0]
    else:
        source_type = ImageSourceType(description=request.POST.get('source_description', default="human"),
                                      pub_date=datetime.now())
        source_type.save()

    # Get CategoryType entries or add if necessary.
    category_list = [CategoryType.objects.get_or_create(category_name=category)[0] for category in request_categories]
    for cat in category_list:
        print(cat.color)
        if not cat.color:
            cat.color = get_color()
            cat.save()

    image_list = Image.objects.all().filter(name=request.POST['image_name'], path=path,
                                            description=request.POST.get('description', default=''), source=source_type)
    if image_list:
        img = image_list[0]
    else:
        img = Image(name=request.POST['image_name'], path=path, description=request.POST.get('description', default=''),
                    source=source_type, width=width, height=height)
        img.save()

    img.categoryType.add(*category_list)
    return HttpResponse("Added image " + request.POST['image_name'] + '\n')


@csrf_exempt
@require_POST
def clean_and_fix_images(request):
    helper_ops.fixAllImagePaths()
    helper_ops.updateAllImageSizes(request.scheme, request.get_host())
    return HttpResponse("All images rows cleaned up and fixed.")


@csrf_exempt
@require_POST
def update_image(request):
    # Validate input
    cat = None
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
def convert_all():
    convert_image_labels_to_svg_array(ImageLabel.objects.all())
    return HttpResponse('Ok')


@csrf_exempt
@require_GET
def unlabeled_images():
    images = Image.objects.all().filter(imagelabel__isnull=True).distinct()
    return HttpResponse("Images: " + ','.join(map(str, images)))


@csrf_exempt
@require_GET
def num_image_labels():
    images = Image.objects.all().annotate(num=Count('imagelabel')).order_by('-num')
    return HttpResponse("Images: " + ','.join(map(str, images)))


@csrf_exempt
@require_POST
def combine_all_images(request):
    threshold_percent = int(request.POST.get('thresholdPercent', 50))
    combine_all_labels(threshold_percent)
    return HttpResponse("OK")


@csrf_exempt
@require_POST
def calculate_entropy_map():
    images = Image.objects.all()
    crop_images.calculate_entropy_map(images[0], images[0].categoryType.all()[0])
    return HttpResponse('ok')


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
    if (str(user) == str(image_label.labeler)) or _user.is_staff or _user.is_superuser:
        try:
            blob = convert_label_to_image_stream(image_label)
        except RuntimeError as runtime_error:
            print(runtime_error, file=sys.stderr)
            return HttpResponseServerError(str(runtime_error))
        foreground = PILImage.open(io.BytesIO(blob)).convert('RGBA')
        output = io.BytesIO()
        foreground.save(output, format='png')
        return HttpResponse(output.getvalue(), content_type="image/png")
    return HttpResponseBadRequest('Authentication error')


@never_cache
@require_GET
def get_overlayed_combined_gif(request, image_label_id):
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    image_label = ImageLabel.objects.filter(id=image_label_id)
    if not image_label:
        return HttpResponseBadRequest('Bad image_label_id: ' + image_label_id)
    image_label = image_label[0]
    _user = User.objects.filter(username=user)[0]
    if (str(user) == str(image_label.labeler)) or _user.is_staff or _user.is_superuser:
        image = image_label.parentImage
        try:
            blob = convert_label_to_image_stream(image_label)
        except RuntimeError as runtime_error:
            print(runtime_error, file=sys.stderr)
            return HttpResponseServerError(str(runtime_error))

        # image with annotations has been saved as blob
        foreground = PILImage.open(io.BytesIO(blob)).convert('PA')
        url = 'http://' + request.get_host() + image.path + image.name
        crop_dimensions = (image_label.imageWindow.x,
                           image_label.imageWindow.y,
                           image_label.imageWindow.x + image_label.imageWindow.width,
                           image_label.imageWindow.y + image_label.imageWindow.height)
        background = PILImage.open(urlopen(url)).convert('PA').crop(crop_dimensions)
        base_folder = settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + str(user) + '/'
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
        if os.path.exists(base_folder + "combined_image.gif"):
            os.remove(base_folder + "combined_image.gif")
        background.save(base_folder + "combined_image.gif", save_all=True, append_images=[foreground], duration=500,
                        loop=0)
        print(base_folder + "combined_image.gif")
        with open(base_folder + "combined_image.gif", 'rb') as f:
            response = HttpResponse(f.read(), content_type="image/gif")
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
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
        blob = convert_label_to_image_stream(category_label)
    except RuntimeError as runtime_error:
        print(runtime_error, file=sys.stderr)
        return HttpResponseServerError(str(runtime_error))
    foreground = PILImage.open(io.BytesIO(blob))
    foreground = foreground.convert('RGBA')
    path = image.path
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
def fix_label_location():
    for _label in ImageLabel.objects.all():
        shape = _label.labelShapes
        _label.labelShapes = re.sub(re_transform_xy, subtract_padding, shape)
        _label.save()
    return HttpResponse("Changed")


def subtract_padding(match_object):
    try:
        s = '%s%d,%d%s' % (match_object.group('prefix'),
                           int(match_object.group('x')) - 20,
                           int(match_object.group('y')) - 20,
                           match_object.group('suffix'))
    except ValueError:
        s = match_object.group(0)
    return s


@csrf_exempt
@require_POST
def print_label_data():
    with open('imageLabel_data.csv', 'w') as csvfile:
        fieldnames = ['parentImage_name', 'parentImage_path', 'categoryType',
                      'pub_date', 'labeler', 'iw_x', 'iw_y', 'iw_width', 'iw_height', 'timeTaken',
                      'if_brightness', 'if_contrast', 'if_saturation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for _label in ImageLabel.objects.all():
            image_filter = ImageFilter.objects.all().get(imageLabel=_label)
            label_dict = {
                'parentImage_name': _label.parentImage.name,
                'parentImage_path': _label.parentImage.path,
                'categoryTypes': [cat_label.categoryType.category_name for cat_label in _label.categorylabel_set],
                'pub_date': _label.pub_date,
                'labeler': _label.labeler,
                'iw_x': _label.imageWindow.x,
                'iw_y': _label.imageWindow.y,
                'iw_width': _label.imageWindow.width,
                'iw_height': _label.imageWindow.height,
                'timeTaken': _label.timeTaken,
                'if_brightness': image_filter.brightness,
                'if_contrast': image_filter.contrast,
                'if_saturation': image_filter.saturation,
            }
            writer.writerow(label_dict)
    return HttpResponse("Printed")


@csrf_exempt
@require_POST
def add_raster(request):
    request_json = json.load(request)
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    raster_image = RasterImage()
    raster_image.name = request_json["name"]
    raster_image.path = request_json["path"]
    raster_image.attribution = request_json["attribution"]
    raster_image.minZoom = request_json["minZoom"]
    raster_image.maxZoom = request_json["maxZoom"]
    raster_image.resolution = request_json["resolution"]
    raster_image.save()
    resp_obj = {"status": "success",
                "message": "Successfully added the raster image"}
    return JsonResponse(resp_obj)


@csrf_exempt
@require_GET
def get_raster_info(request):
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    rasters = []
    data = RasterImage.objects.all()
    for raster in data:
        single_raster = {
            "name": raster.name,
            "path": raster.path,
            "attribution": raster.attribution,
            "minZoom": raster.minZoom,
            "maxZoom": raster.maxZoom,
            "resolution": raster.resolution,
            "lat_lng": [raster.latitude, raster.longitude]
        }
        rasters.append(single_raster)
    resp_obj = {"status": "success",
                "message": rasters}
    return JsonResponse(resp_obj)


@csrf_exempt
@require_POST
def add_tiled_label(request):
    request_json = json.load(request)
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)
    tiled_label = TiledGISLabel()
    tiled_label.northeast_Lat = request_json["northeast_lat"]
    tiled_label.northeast_Lng = request_json["northeast_lng"]
    tiled_label.southwest_Lat = request_json["southwest_lat"]
    tiled_label.southwest_Lng = request_json["southwest_lng"]
    tiled_label.zoom_level = request_json["zoom_level"]
    _user = User.objects.filter(username=user)[0]
    _labeler = Labeler.objects.filter(user=_user)
    if len(_labeler) == 0:
        labeler = Labeler(user=_user)
        labeler.save()
        _labeler = Labeler.objects.filter(user=_user)
    _labeler = _labeler[0]
    tiled_label.labeler = _labeler
    raster = RasterImage.objects.filter(name=request_json["raster"])
    if len(raster) == 0 or len(raster) > 1:
        return JsonResponse({"status": "failure", "message": "0 or multiple raster found. "}, safe=False)
    tiled_label.parent_raster = raster[0]
    tiled_label.category = CategoryType.objects.get(category_name=request_json["category_name"])
    tiled_label.label_type = \
        [K for (K, v) in TiledGISLabel.label_type_enum if request_json["label_type"].lower() == v.lower()][0]
    json_ = request_json["geoJSON"]
    tiled_label.label_json = json_
    tiled_label.geometry = GEOSGeometry(str(json_["geometry"]))
    tiled_label.save()
    resp_obj = {"status": "success",
                "message": "Successfully added your annotation",
                "category": request_json["category_name"]}
    return JsonResponse(resp_obj)


def add_tiled_label1(request):
    import csv

    with open('agdss_public_webclient_tiledgislabel.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                print(row)
                line_count += 1
                continue
            else:
                print(line_count)
                line_count += 1
                tiled_label = TiledGISLabel()
                tiled_label.northeast_Lat = row[1]
                tiled_label.northeast_Lng = row[2]
                tiled_label.southwest_Lat = row[3]
                tiled_label.southwest_Lng = row[4]
                tiled_label.zoom_level = row[5]
                _user = User.objects.all()[0]
                _labeler = Labeler.objects.all()  # ADD

                if len(_labeler) == 0:
                    labeler = Labeler(user=_user)
                    labeler.save()
                    _labeler = Labeler.objects.filter(user=_user)
                _labeler = _labeler[0]

                tiled_label.labeler = _labeler
                tiled_label.parent_raster = RasterImage.objects.all()[0]
                tiled_label.category = CategoryType.objects.get(category_name="rocks")  # ADD
                tiled_label.label_json = row[6]
                tiled_label.label_type = row[7]
                tiled_label.geometry = row[8]
                tiled_label.save()

    return JsonResponse({"status": "failure", "message": f"{line_count}"}, safe=False)


@csrf_exempt
def get_all_tiled_labels(request):
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

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

    _user = User.objects.filter(username=user)[0]
    if _user.is_staff or _user.is_superuser:
        query_set = TiledGISLabel.objects.filter(geometry__within=current_bbox).filter(~Q(geometry__within=new_polygon))
    else:
        query_set = TiledGISLabel.objects.filter(geometry__within=current_bbox, labeler=_user).filter(
            ~Q(geometry__within=new_polygon))

    for tiled_label in query_set:
        response_dict = {"northeast_lat": tiled_label.northeast_Lat, "northeast_lng": tiled_label.northeast_Lng,
                         "southwest_lat": tiled_label.southwest_Lat, "southwest_lng": tiled_label.southwest_Lng,
                         "zoom_level": tiled_label.zoom_level, "label_type": tiled_label.get_label_type_display(),
                         "geoJSON": tiled_label.label_json, "category": tiled_label.category.category_name}
        response_obj.append(response_dict)

    previous_boxes.append(current_bbox)
    request.session['prev_multipoly'] = str(previous_boxes)
    return JsonResponse(response_obj, safe=False)


@cache_page(6000)
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

    # Update the 50 value to whatever range the histogram x-axis should be plotted. 
    # It's set to 2m in rocks deepgis, but it can be adjusted. 
    # TODO: take this as user input
    result = np.histogram(np.array(result_set).astype(np.float32), bins=np.linspace(0, 50, num=number_of_bins))

    x = []
    y = []
    for i in range(result[0].shape[0]):
        x.append(round(result[1].item(i), 2))
        y.append(round(result[0].item(i), 2))

    unique = str(xmin) + str(xmax) + str(ymin) + str(ymax)
    print(unique)
    return JsonResponse({"status": "success", "y": y, "x": x, "unique": unique}, safe=False)


def get_window_tiled_labels(request):
    response_obj = []
    float_tolerance = 1e-5
    request_json = json.load(request)

    tile_labels = TiledLabel.objects.filter(
        northeast_Lat__range=(
            request_json["northeast_lat"] - float_tolerance, request_json["northeast_lat"] + float_tolerance),
        northeast_Lng__range=(
            request_json["northeast_lng"] - float_tolerance, request_json["northeast_lat"] + float_tolerance),
        southwest_Lat__range=(
            request_json["southwest_lat"] - float_tolerance, request_json["northeast_lat"] + float_tolerance),
        southwest_Lng__range=(
            request_json["southwest_lng"] - float_tolerance, request_json["northeast_lat"] + float_tolerance))

    for tiled_label in tile_labels:
        response_dict = {"northeast_lat": tiled_label.northeast_Lat, "northeast_lng": tiled_label.northeast_Lng,
                         "southwest_lat": tiled_label.southwest_Lat, "southwest_lng": tiled_label.southwest_Lng,
                         "zoom_level": tiled_label.zoom_level, "label_type": tiled_label.get_label_type_display(),
                         "geoJSON": tiled_label.label_json, "category": tiled_label.category.category_name}
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

    train_label = PILImage.fromarray(train_label)

    img_name = "/home/jdas/aerialapps/trainset/" + request_json["category_name"] + "/" + image_name + ".png"
    label_name = "/home/jdas/aerialapps/trainset/" + request_json["category_name"] + "/" + image_name + "_label.png"

    train_image.save(img_name)
    train_label.save(label_name)

    resp_obj = {"status": "success"}

    return JsonResponse(resp_obj)


@csrf_exempt
@require_POST
def add_all_tiled_categories():
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
    user = request.user
    print(user)
    if not user.is_authenticated:
        return JsonResponse({"status": "failure", "message": "Authentication failure"}, safe=False)

    request_list = json.load(request)
    to_delete = []
    if len(request_list) == 0:
        return JsonResponse({"status": "success", "message": f"Successfully deleted {len(request_list)} labels"},
                            safe=False)
    for request in request_list:
        northeast_lat = request.get("northeast_lat")
        northeast_lng = request.get("northeast_lng")
        southwest_lat = request.get("southwest_lat")
        southwest_lng = request.get("southwest_lng")
        category_name = request.get("category_name")

        if northeast_lat is None or northeast_lng is None or \
                southwest_lat is None or southwest_lng is None or category_name is None:
            return JsonResponse({"status": "failure", "message": "Failed. Missing required field."}, safe=False)

        category = CategoryType.objects.get(category_name=category_name)
        poly = GEOSGeometry(str(json.loads(request.get('geoJSON'))['geometry']))
        tile_label = TiledGISLabel.objects.filter(category=category).filter(geometry__equals=poly)

        if len(tile_label) < 1:
            return JsonResponse({"status": "failure", "message": "Failed. Annotation not found."}, safe=False)
        if len(tile_label) == 2:
            return JsonResponse({"status": "failure", "message": "Failed. More than one Annotation found."}, safe=False)
        to_delete.append(tile_label[0])

    # Make sure all objects are okay to delete first
    # If there's an error don't change database
    for _label in to_delete:
        _label.delete()

    return JsonResponse({"status": "success", "message": f"Successfully deleted {len(to_delete)} labels"}, safe=False)


@csrf_exempt
@require_POST
def add_tileset(request):
    if 'base_location' not in request.POST:
        return HttpResponseBadRequest("base_location required for tileset")
    tile_set = TileSet(base_location=request.POST['base_location'])
    tile_set.save()

    url_val = URLValidator()
    try:
        url_val(tile_set.base_location)
        url_location = True
    except ValidationError:
        url_location = False

    if url_location and requests.head(
            tile_set.base_location).status_code != 200:
        return HttpResponseBadRequest("Error: {} must be value url".format(tile_set.base_location))
    valid_zoom_levels = [z for z in range(30) if request.head(urljoin(tile_set.base_location, z)).status_code == 200]


@csrf_exempt
@require_GET
def get_tiled_label_coordinates():
    lat_long = [{'category': tl.category.category_name,
                 'latitude': (tl.northeast_Lat + tl.southwest_Lat) / 2,
                 'longitude': (tl.northeast_Lng + tl.southwest_Lng) / 2}
                for tl in TiledLabel.objects.all()]
    return JsonResponse(lat_long, safe=False)


@csrf_exempt
@require_GET
def get_combined_label_geojson():
    combined_dict = {'type': 'FeatureCollection',
                     'features': [_label.label_json for _label in TiledLabel.objects.all()]}
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
