from wand.image import Image as WandImage
from wand.color import Color as WandColor
import io
from webclient.models import User, Labeler, Image, ImageLabel, CategoryLabel, CategoryType
from django.conf import settings
import re
import wand.exceptions
import os
from PIL import Image as PILImage
import numpy
import SVGRegex
from webclient.image_ops import crop_images
import numpy as np
import imageio
from cairosvg import svg2png
import shutil
import string
import random
import json
from bs4 import BeautifulSoup

IMAGE_FILE_EXTENSION: str = '.png'


def get_label_pillow_image(label: ImageLabel) -> PILImage:
    """
    Args:
        label: ImageLabel object with labels

    Returns:
        PILImage: Pillow image of the labels
    """
    return PILImage.fromarray(convert_svg_string_to_numpy_masks(label.combined_labelShapes))


def get_average_label_pillow_images(image: Image,
                                    category: CategoryType,
                                    avg_threshold: int) -> PILImage or None:
    """
    Args:
        image: Image object
        category: CategoryType object
        avg_threshold: integer

    Returns:
        PILImage or None:
    """
    folder_name = category.category_name + '/Threshold_' + str(avg_threshold) + '/'
    image_name = f"P{image.id:d}C{category.category_name}I{image.name}.png"
    filename = folder_name + image_name
    if not os.path.exists(filename):
        return None
    return PILImage.open(filename)


def convert_svg_to_png(img_file: bytes,
                       folder_name: string,
                       filename: string,
                       reconvert: bool = False) -> string:
    """
    Converts an SVG string stream to an image file stream (bytes)
    Args:
        img_file: Binary Large Object (blob)
        folder_name: string
        filename : string
        reconvert: boolean

    Returns:
        string: 
    """
    if not img_file:
        return ""

    # TODO: error checking on folder_name and file_name and folder_name_ not clear on its usage
    # folder_name_ = folder_name
    # if folder_name_[0] == '/' or folder_name_[0] == '\\':
    #     folder_name_ = folder_name_[1:]
    # if folder_name_[-1] == '/' or folder_name_[-1] == '\\':
    #     folder_name_ = folder_name_[:-1]

    if not reconvert and os.path.exists(
            settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + folder_name + '/' + filename + '.png'):
        return settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + folder_name + '/' + filename + IMAGE_FILE_EXTENSION
    try:
        with WandImage(blob=img_file) as img:
            img.background_color = WandColor('white')
            img.alpha_channel = 'remove'
            img.negate()  # Convert to black and white
            img.threshold(0)
            img.format = 'png'
            if not os.path.exists(settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + folder_name + '/'):
                os.makedirs(settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + folder_name + '/')
            img.save(filename=(
                    settings.STATIC_ROOT +
                    settings.LABEL_FOLDER_NAME +
                    folder_name + '/' +
                    filename + IMAGE_FILE_EXTENSION))
            print(("converted Image " + filename))
            return settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + folder_name + '/' + filename + \
                   IMAGE_FILE_EXTENSION

    except wand.exceptions.CoderError as e:
        print(('Failed to convert: ' + filename + ': ' + str(e)))
    except wand.exceptions.MissingDelegateError as e:
        print(('DE Failed to convert: ' + filename + ': ' + str(e)))
    except wand.exceptions.WandError as e:
        print(('Failed to convert ' + filename + ': ' + str(e)))


def convert_svg_to_image_stream(svg: string) -> bytes or None:
    """
    Converts svg string to an image file stream (bytes)
    Args:
        svg: string

    Returns:
        Binary Large Object or None
    """
    if not svg:
        return None
    svg_file = io.StringIO(svg)
    try:
        with WandImage(file=svg_file) as img:
            img.background_color = WandColor('white')
            img.alpha_channel = 'remove'
            # Convert to black and white
            img.negate()
            img.threshold(0)
            img.format = 'png'
            return img.make_blob()
    except wand.exceptions.CoderError as e:
        print(('Failed to convert: ' + svg + ': ' + str(e)))
    except wand.exceptions.MissingDelegateError as e:
        print(('DE Failed to convert: ' + svg + ': ' + str(e)))
    except wand.exceptions.WandError as e:
        print(('Failed to convert ' + svg + ': ' + str(e)))


def convert_image_label_to_svg_text_stream(label: ImageLabel) -> bytes:
    """
    Converts a ImageLabel object in database to IO String file object
    Args:
        label: ImageLabel object

    Returns:
        StringIO bytes object
    """
    svg_string_file = io.StringIO(convert_image_label_string_to_svg_string(label.combined_labelShapes,
                                                                           label.imageWindow.height,
                                                                           label.imageWindow.width,
                                                                           label.imageWindow.x,
                                                                           label.imageWindow.y,
                                                                           True))
    svg_string_file.seek(0)
    return svg_string_file.read().encode('utf-8')


def convert_svg_to_text_stream(svg_string: string) -> bytes:
    """
    Converts svg string to StringIO file object (bytes)
    Args:
        svg_string: string

    Returns:
        StringIO bytes object
    """
    svg_string_file = io.StringIO(svg_string)
    svg_string_file.seek(0)
    return svg_string_file.read().encode('utf-8')


def convert_category_in_label_to_svg_text_stream(label: CategoryLabel) -> bytes:
    """
    Converts CategoryLabel object containing svg string to StringIO file object (bytes)
    Args:
        label: CategoryLabel

    Returns:
        StringIO bytes object
    """
    svg_string_file = io.StringIO(convert_category_label_string_to_svg_string(label))
    svg_string_file.seek(0)
    return svg_string_file.read().encode('utf-8')


def convert_label_to_image_stream(label: ImageLabel or CategoryLabel) -> bytes:
    """
    Converts an ImageLabel or CategoryLabel containing SVG string to an image file stream (bytes)
    Args:
        label: ImageLabel or CategoryLabel object

    Returns:
        Image: Binary Large Object
    """
    if isinstance(label, ImageLabel):
        svg = label.combined_labelShapes
        svg_file = convert_image_label_to_svg_text_stream(label)
        # convert svg string to png using cairo
        svg2png(bytestring=svg_file, write_to="output.png")
        try:
            with WandImage(filename='output.png') as img:
                img.format = 'png'
                return img.make_blob()
        except wand.exceptions.CoderError as e:
            raise RuntimeError(('Failed to convert: ' + svg + ': ' + str(e)))
        except wand.exceptions.MissingDelegateError as e:
            raise RuntimeError(('DE Failed to convert: ' + svg + ': ' + str(e)))
        except wand.exceptions.WandError as e:
            raise RuntimeError(('Failed to convert ' + svg + ': ' + str(e)))
        except ValueError as e:
            raise RuntimeError(('Failed to convert ' + svg + ': ' + str(e)))

    elif isinstance(label, CategoryLabel):
        svg = label.labelShapes
        svg_file = convert_category_in_label_to_svg_text_stream(label)
    else:
        raise ValueError("Label must be an ImageLabel or CategoryLabel, it is instead an {}".format(type(label)))
    try:
        with WandImage(blob=svg_file) as img:
            img.format = 'png'
            return img.make_blob()
    except wand.exceptions.CoderError as e:
        raise RuntimeError(('Failed to convert: ' + svg + ': ' + str(e)))
    except wand.exceptions.MissingDelegateError as e:
        raise RuntimeError(('DE Failed to convert: ' + svg + ': ' + str(e)))
    except wand.exceptions.WandError as e:
        raise RuntimeError(('Failed to convert ' + svg + ': ' + str(e)))
    except ValueError as e:
        raise RuntimeError(('Failed to convert ' + svg + ': ' + str(e)))


def convert_svg_to_array_of_vector_images(svg: string) -> list:
    """
    Convert vectors inside svg string to an array of corresponding image stream

    TODO: Replace convert_svg_to_array_of_vector_images regex usage with Beautiful Soup based approach
    Args:
        svg (string):
    """
    paths = re.findall(SVGRegex.rePath, svg) + re.findall(SVGRegex.reCircle, svg)
    image, height, width = get_svg_dimensions(svg)
    images = []
    for path in paths:
        images.append(convert_svg_to_image_stream(convert_image_label_string_to_svg_string(path, height, width)))
    return images


def get_svg_dimensions(svg: string) -> (None, None, None) or (string, int, int):
    """
    Finds image, width and height from svg string
    Args:
        svg: svg string

    Returns:
        (None, None, None) or (string, int, int)
    """
    result = re.search(SVGRegex.reWH, svg)
    if result is None:
        return None, None, None

    # reFill = r'<path[^/>]*fill\s*=\s*"(?P<fill>[^"]*)"'
    # reStroke = r'<path[^/>]*stroke\s*=\s*"(?P<stroke>[^"]*)"'
    # pathFill = '#000001'
    # pathStroke = '#000001'

    image = result.group(0)
    height = int(result.group('height'))
    width = int(result.group('width'))
    return image, height, width


def convert_image_label_string_to_svg_string(image_label_string: string,
                                             height: int = None,
                                             width: int = None,
                                             x: int = 0,
                                             y: int = 0,
                                             keep_image: object = False) -> string:
    """
    Convert paper.js vector string in image label object to svg string

    If height and width are defined, image tag is not removed.
    Otherwise, height and width are extracted from it and it is removed.

    Args:
        image_label_string (string): ImageLabel.combined_labelShapes string
        height:
        width:
        x:
        y:
        keep_image:

    Returns:
        string
    """
    added_str = image_label_string
    image_string = ""

    if keep_image:
        image_path = re.search('ns1:href="(.*)png"', image_label_string)
        try:
            image_path = image_path.group(1) + "png"
        except AttributeError as e:
            image_path = re.search('a0:href="(.*)png"', image_label_string)
            image_path = image_path.group(1) + "png"
            print(e)

        image_width = re.search(r'width="(\d+)"', added_str).group(1)
        image_height = re.search(r'height="(\d+)"', added_str).group(1)

        image_string = '<defs><pattern id="backgroundImage" ' \
                       'patternUnits="userSpaceOnUse" width="{}" height="{}">' \
                       '<image xlink:href="{}" x="-{}" y="-{}" width="{}" height="{}"/>' \
                       '</pattern></defs><rect id="background" fill="url(#backgroundImage)" ' \
                       'width="{}" height="{}"/>'.format(width,
                                                         height,
                                                         image_path,
                                                         x,
                                                         y,
                                                         image_width,
                                                         image_height,
                                                         width,
                                                         height)
        print(image_string)

    if height is None or width is None:
        image, height, width = get_svg_dimensions(image_label_string)
        if not keep_image and image:
            added_str = image_label_string.replace(image, '')

    added_str = re.sub(r'<image.+hidden"/>', '', added_str)
    added_str = added_str.encode('utf-8')

    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>' \
           '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg"' \
           ' xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" xml:space="preserve" height="{}"' \
           ' width="{}">{}{}</svg>'.format(height, width, image_string, added_str)


def get_annotation_count_per_user(username: string) -> None:
    """
    Get a count of all annotations done by a single user
    Args:
        username: eg "user1"

    Returns:
        None
    """
    _user = User.objects.filter(username=username)[0]
    _labeler = Labeler.objects.filter(user=_user)[0]
    labels = ImageLabel.objects.filter(labeler=_labeler)
    ctr_total = 0
    for label in labels:
        parent_image = label.parentImage
        filename = '%s' % parent_image.name
        category_labels = label.categorylabel_set.all()
        time_taken = int(label.timeTaken)
        minimum_time = (time_taken / 1000.0) / 60.0

        for cat_id, category_label in enumerate(category_labels):
            svg = category_label.labelShapes
            paths = re.findall(SVGRegex.rePath, svg)
            poly = re.findall(SVGRegex.rePolygon, svg)
            circles = re.findall(SVGRegex.reCircle, svg)
            total = len(paths) + len(poly) + len(circles)
            ctr_total += total
            print(f"filename={filename}, category_enum={cat_id}, paths={len(paths)}, polygon={len(poly)}, "
                  f"circles={len(circles)}, count={total}, time_taken={minimum_time}, cumulative count={ctr_total}")

    return None


def get_random_string(length: int = 16) -> string:
    """
    Generate a random string of length (16 default)
    Args:
        length: int

    Returns:
        string
    """
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return str(result_str)


def convert_image_labels_to_numpy_masks(user_name: string,
                                        labels: list) -> string:
    """
    Convert a list of image label objects to numpy masks for MaskRCNN format
    Username is used to create a unique path for saving the outputs.

    settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user + '/' + get_random_string() + '/dataset.zip

    Args:
        user_name: user who requested for creation of numpy masks
        labels: a list of ImageLabel objects

    Returns:
        string
    """
    _user = User.objects.filter(username=user_name)[0]
    user = str(_user.username)
    folder_name = 'labels'

    # Delete all previous user generated zip files
    if os.path.exists(settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user):
        shutil.rmtree(settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user)
    base_folder = settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user + '/' + get_random_string() + '/dataset/'

    for label in labels:
        parent_image = label.parentImage
        filename = '%s' % parent_image.name.replace('.JPG', '')
        filename = '%s' % filename.replace('.PNG', '')
        filename = '%s' % filename.replace('.jpg', '')
        filename = '%s' % filename.replace('.png', '')

        category_labels = label.categorylabel_set.all()
        height = label.imageWindow.height
        width = label.imageWindow.width
        padding_x = label.imageWindow.x
        padding_y = label.imageWindow.y
        total_paths = 300
        masks_array = np.zeros((total_paths, height, width), dtype=np.int8)
        ctr = 0
        output_filename_npy = (base_folder + folder_name + '/' + filename + '_' + str(padding_x) + '_' + str(padding_y)
                               + '.npy')

        # create cropped images
        image_path = re.search('ns1:href="(.*)png"', label.combined_labelShapes)
        try:
            image_path = image_path.group(1) + "png"
        except AttributeError as e:
            image_path = re.search('a0:href="(.*)png"', label.combined_labelShapes)
            image_path = image_path.group(1) + "png"
            print(e)

        image_path = settings.STATIC_ROOT + image_path[image_path.find("static/") + 7:]
        im = PILImage.open(image_path)
        crop_dimensions = (padding_x, padding_y, padding_x + width, padding_y + height)
        im_crop = im.crop(crop_dimensions)

        if not os.path.exists(base_folder + "images"):
            os.makedirs(base_folder + "images")
        output_image_filename = base_folder + "images/" + filename + '_' + str(padding_x) + '_' + str(padding_y) + \
                                IMAGE_FILE_EXTENSION

        im_crop.save(output_image_filename, quality=95)

        # Create masks
        for cat_id, category_label in enumerate(category_labels):
            svg = category_label.labelShapes
            paths = re.findall(SVGRegex.rePath, svg)
            poly = re.findall(SVGRegex.rePolygon, svg)
            circles = re.findall(SVGRegex.reCircle, svg)
            shapes = paths + poly + circles
            if len(paths) + len(poly) + len(circles) > 0:
                for idx, path in enumerate(shapes):
                    print("logging image info:----", filename, ctr, cat_id, idx, path)
                    img = WandImage(blob=convert_svg_to_text_stream(convert_image_label_string_to_svg_string(path,
                                                                                                             height,
                                                                                                             width)))
                    img.resize(width, height)
                    img.background_color = WandColor('white')
                    img.alpha_channel = 'remove'
                    img.negate()
                    img.threshold(0)
                    img.format = 'png'
                    if not os.path.exists(base_folder + folder_name):
                        os.makedirs(base_folder + folder_name)
                    output_filename = (
                            base_folder + folder_name + '/' + filename + '_' + str(padding_x) + '_' + str(padding_y) +
                            '_' + str(padding_x) + '_' + str(padding_y) + '_' + str(idx) + '_' + str(ctr) +
                            IMAGE_FILE_EXTENSION)
                    img.save(filename=output_filename)
                    im = imageio.imread(output_filename)
                    masks = np.array(im)
                    category_id = category_label.categoryType_id
                    cat_mask = np.where(masks == 255, category_id, masks)
                    masks_array[ctr, :, :] = cat_mask
                    ctr = ctr + 1
            else:
                print(filename, ctr, cat_id, 0, 'EMPTY')
        np.resize(masks_array, (ctr, height, width))
        np.save(output_filename_npy, masks_array)

        for png_file in os.listdir(base_folder + folder_name):
            if png_file.endswith('.png'):
                os.remove(base_folder + folder_name + '/' + png_file)
    base_folder_without_dataset = base_folder[:-8]

    # create a zip file of the dataset
    shutil.make_archive(base_folder_without_dataset + 'dataset', 'zip', base_folder)

    # delete the folder with images/ and labels/
    shutil.rmtree(base_folder)
    return base_folder_without_dataset + 'dataset.zip'


def convert_image_labels_to_json(user_name: string,
                                 labels: list) -> string:
    """
    Convert a list of image label objects to a json format for MaskRCNN Google colaboratory notebook
    Username is used to create a unique path for saving the outputs.

    settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user + '/' + get_random_string() + '/dataset.zip

    TODO: Add an example of the actual output format in docstring
    labels_json = { "height": height,
                    "width": width,
                    "labelShapes": [], # svg string
                    "categories": ["background"]}
    Args:
        user_name: user who requested for creation of numpy masks
        labels: a list of ImageLabel objects

    Returns:
        string
    """
    _user = User.objects.filter(username=user_name)[0]
    user = str(_user.username)

    # Delete all previous user generated zip files
    if os.path.exists(settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user):
        shutil.rmtree(settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user)
    base_folder = settings.MEDIA_ROOT + settings.LABEL_FOLDER_NAME + user + '/' + get_random_string() + '/dataset/'

    for label in labels:
        parent_image = label.parentImage
        filename = '%s' % parent_image.name.replace('.JPG', '')
        filename = '%s' % filename.replace('.PNG', '')
        filename = '%s' % filename.replace('.jpg', '')
        filename = '%s' % filename.replace('.png', '')

        height = label.imageWindow.height
        width = label.imageWindow.width
        padding_x = label.imageWindow.x
        padding_y = label.imageWindow.y

        # create cropped images
        image_path = re.search('ns1:href="(.*)png"', label.combined_labelShapes)
        try:
            image_path = image_path.group(1) + "png"
        except AttributeError as e:
            image_path = re.search('a0:href="(.*)png"', label.combined_labelShapes)
            image_path = image_path.group(1) + "png"
            print(e)

        image_path = settings.STATIC_ROOT + image_path[image_path.find("static/") + 7:]
        im = PILImage.open(image_path)
        crop_dimensions = (padding_x, padding_y, padding_x + width, padding_y + height)
        im_crop = im.crop(crop_dimensions)

        if not os.path.exists(base_folder + "images"):
            os.makedirs(base_folder + "images")
        if not os.path.exists(base_folder + "json"):
            os.makedirs(base_folder + "json")

        output_image_filename = base_folder + "images/" + parent_image.path.replace("/", "_") + filename + '_' + \
                                str(padding_x) + '_' + str(padding_y) + str(label.id) + IMAGE_FILE_EXTENSION

        im_crop.save(output_image_filename, quality=95)

        output_json_filename = base_folder + "json/" + parent_image.path.replace("/", "_") + filename + '_' + \
                               str(padding_x) + '_' + str(padding_y) + str(label.id) + ".json"
        labels_json = {"height": height, "width": width, "labelShapes": [], "categories": ["background"]}

        soup = BeautifulSoup(label.combined_labelShapes)
        for category in CategoryType.objects.all():
            labels_json["categories"].append(str(category.category_name))
            container = soup.find_all('g', id=category.category_name)
            if len(container) > 0:
                # noinspection PyTypeChecker
                labels_json["labelShapes"].append((labels_json["categories"].index(str(category.category_name)),
                                                   str(container[0])))

        print(output_json_filename)
        with open(output_json_filename, 'w') as fp:
            json.dump(labels_json, fp)

    base_folder_without_dataset = base_folder[:-8]

    # create a zip file of the dataset
    shutil.make_archive(base_folder_without_dataset + 'dataset', 'zip', base_folder)

    # delete the folder with images/ and labels/
    shutil.rmtree(base_folder)
    print(base_folder_without_dataset)
    return base_folder_without_dataset + 'dataset.zip'


def get_numpy_masks_of_a_user(user_name: string) -> string:
    """
    Generate numpy masks of all annotations made by a user
    Args:
        user_name: string

    Returns:
        string
    """
    _user = User.objects.filter(username=user_name)[0]
    _labeler = Labeler.objects.filter(user=_user)[0]
    labels = ImageLabel.objects.filter(labeler=_labeler)
    return convert_image_labels_to_numpy_masks(user_name, labels)


def convert_category_label_string_to_svg_string(category_label: CategoryLabel,
                                                keep_image: bool = False) -> string:
    """
    Converts CategoryLabel string to its corresponding svg format
    Args:
        category_label: CategoryLabel
        keep_image: bool

    Returns:
        svg string
    """
    added_str = category_label.labelShapes
    image, height, width = get_svg_dimensions(category_label.parent_label.combined_labelShapes)
    if keep_image:
        added_str = image + added_str
    added_str = added_str.encode('utf-8')
    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>' \
           '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg"' \
           ' xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" xml:space="preserve" height="{}"' \
           ' width="{}">{}</svg>\n'.format(height, width, added_str)


def convert_image_labels_to_svg_array(label_list: list) -> string:
    """
    Convert an array ImageLabel objects to svg string array
    Args:
        label_list: list of ImageLabel objects

    Returns:
        list of svg string of each ImageLabel object
    """
    return [convert_image_label_to_svg(label) for label in label_list if label is not None]


def convert_category_labels_to_svg_array(label_list: list, reconvert: bool = False) -> string:
    """
    Convert an array CategoryLabel objects to svg string array
    Args:
        label_list: list of CategoryLabel objects
        reconvert: bool

    Returns:
        list of svg string of each CategoryLabel object
    """
    return [convert_category_label_to_svg(label, reconvert) for label in label_list if label is not None]


def convert_image_label_to_svg(image_label: ImageLabel, reconvert: bool = False) -> str:
    """
    Convert a ImageLabel object to svg string
    Args:
        image_label:
        reconvert:

    Returns:
        svg string
    """
    return convert_svg_to_png(img_file=convert_image_label_to_svg_text_stream(image_label),
                              folder_name="combined_image_labels",
                              filename=get_image_label_details(image_label),
                              reconvert=reconvert)


def convert_category_label_to_svg(category_label: CategoryLabel, reconvert: bool = False) -> str:
    """
    Convert a CategoryLabel object to svg string
    Args:
        category_label:
        reconvert:

    Returns:
        svg string
    """
    return convert_svg_to_png(img_file=convert_category_in_label_to_svg_text_stream(category_label),
                              folder_name=category_label.categoryType.category_name,
                              filename=get_category_label_details(category_label),
                              reconvert=reconvert)


def get_image_label_details(label: ImageLabel) -> string:
    """
    Generates the image id, label id and parent image name
    Args:
        label: ImageLabel

    Returns:
        string
    """
    return 'P%iL%iI%s' % (
        label.parentImage.id, label.id, label.parentImage.name)


def get_category_label_details(label: CategoryLabel) -> string:
    """
    Generates the category name, image id, label id and parent image name
    Args:
        label: CategoryLabel

    Returns:
        string
    """
    return 'C%sP%iL%iI%s' % (
        label.categoryType.category_name, label.parent_label.parentImage.id, label.id,
        label.parent_label.parentImage.name)


def convert_svg_string_to_numpy_masks(svg_string: string) -> numpy:
    """
    Convert a svg string to numpy mask
    Args:
        svg_string: string

    Returns:
        numpy array
    """
    converted_images = convert_svg_to_array_of_vector_images(svg_string)
    height, width = get_svg_dimensions(svg_string)[1:]
    if not height or not width:
        return None
    image = numpy.zeros((height, width), numpy.uint8)
    for converted_image in converted_images:
        img = PILImage.open(io.StringIO(converted_image)).convert("L")
        img_arr = numpy.array(img, copy=True)
        img_arr[img_arr == 255] = 1
        image += img_arr

    return image


def combine_image_labels_to_numpy_array(image: Image, category: CategoryType, threshold_percent: int = 50) -> object:
    """

    Args:
        image:
        category:
        threshold_percent:

    Returns:

    """
    threshold = threshold_percent / 100.0
    labels = ImageLabel.objects.all().filter(parentImage=image, categoryType=category)
    if not labels:
        return
    label_images = [convert_svg_string_to_numpy_masks(label.combined_labelShapes) for label in labels]

    # Based on https://stackoverflow.com/questions/17291455/how-to-get-an-average-picture-from-100-pictures-using-pil

    height, width = get_svg_dimensions(labels[0].combined_labelShapes)[1:]
    arr = numpy.zeros((height, width), numpy.float)

    # TODO: Make this code better by taking into account ImageWindows
    # n = len(label_images)
    n = crop_images.NUM_LABELS_PER_WINDOW
    for im in label_images:
        if im is None:
            continue
        imarr = im.astype(numpy.float)
        # img.show()
        arr = arr + imarr / n

    ui8 = arr.astype(numpy.uint8)
    return ui8 + (arr >= (ui8 + threshold)).astype(numpy.uint8)


def save_combined_image(image_numpy_array: numpy, image: Image, category: CategoryType, threshold: int):
    """

    Args:
        image_numpy_array:
        image:
        category:
        threshold:
    """
    # Folder format: /averages/*category*/Threshold_*threshold*/
    folder_name = category.category_name + '/Threshold_' + str(threshold) + '/'
    image_name = "P%iC%sI%s.png" % (image.id, category.category_name, image.name)

    if not os.path.exists(settings.STATIC_ROOT + settings.LABEL_AVERAGE_FOLDER_NAME + folder_name):
        os.makedirs(settings.STATIC_ROOT + settings.LABEL_AVERAGE_FOLDER_NAME + folder_name)
    out = PILImage.fromarray(image_numpy_array, mode='L')

    out.save(settings.STATIC_ROOT + settings.LABEL_AVERAGE_FOLDER_NAME + folder_name + image_name)


def combine_all_labels(threshold: int):
    """

    Args:
        threshold:
    """
    for image in Image.objects.all():
        if len(ImageLabel.objects.all.filter(
                parentImage=image)) < crop_images.NUM_LABELS_PER_WINDOW * crop_images.NUM_WINDOW_ROWS * \
                crop_images.NUM_WINDOW_COLS:
            continue
        combine_image_labels(image, threshold)


def combine_image_labels(image: Image, threshold: int):
    """

    Args:
        image:
        threshold:
    """
    for category in image.categoryType.all():
        combined_image = combine_image_labels_to_numpy_array(image, category, threshold)
        if combined_image is not None and combined_image.size:
            save_combined_image(combined_image, image, category, threshold)
