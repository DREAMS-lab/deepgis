import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deepgis_moon.agdss.settings")
django.setup()

import io
from webclient.models import User, Labeler, Image, ImageLabel, CategoryLabel

def image_labels_to_countable_npy():
    _user = User.objects.filter(username='Labeler1')[0]
    _labeler = Labeler.objects.filter(user=_user)[0]
    labels = ImageLabel.objects.filter(labeler=_labeler)
    foldername = 'npy'

    for label in labels:
        parent_image = label.parentImage
        filename = '%s' % parent_image.name.replace('.JPG','')
        outputFilenameNpy = (settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + foldername + '/' + filename + '.npy')
        categorylabels = label.categorylabel_set.all()
        height = parent_image.height
        width = parent_image.width
        total_paths = 300
        masks_ndarray = np.zeros((total_paths, height, width), dtype=np.int8)
        ctr = 0

        for cat_id, categorylabel in enumerate(categorylabels):
            svg = categorylabel.labelShapes
            paths = []
            poly = []
            print(filename, svg)
            paths = re.findall(SVGRegex.rePath, svg)
            poly = re.findall(SVGRegex.rePolygon, svg)
            circles = re.findall(SVGRegex.reCircle, svg)
            shapes = paths + poly + circles
            if len(paths) + len(poly) +len(circles) > 0:
                for idx,path in enumerate(shapes):
                    print("logging image info:----",filename, ctr, cat_id, idx, path)
                    img=WandImage(blob=image_string_to_SVG_string_file(image_label_string_to_SVG_string(path, height, width)))
                    img.resize(width,height)
                    img.background_color = WandColor('white')
                    img.alpha_channel = 'remove'
                    img.negate()
                    img.threshold(0)
                    img.format = 'png'
                    if not os.path.exists(settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + foldername):
                        os.makedirs(settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + foldername)
                    outputFilename = (
                            settings.STATIC_ROOT + settings.LABEL_FOLDER_NAME + foldername + '/' + filename + '_' + str(idx) + '_' + str(ctr) + IMAGE_FILE_EXTENSION)
                    img.save(filename=outputFilename)
                    im = imageio.imread(outputFilename)
                    masks = np.array(im)
                    category_id = categorylabel.categoryType_id
                    cat_mask = np.where(masks == 255,category_id , masks)
                    masks_ndarray[ctr, :, :] = cat_mask
                    ctr = ctr + 1
            else:
                print(filename, ctr, cat_id, 0, 'EMPTY')
        masks_ndarray.resize(ctr, height, width)
        print(masks_ndarray.shape)
        np.save(outputFilenameNpy,masks_ndarray)

image_labels_to_countable_npy()
