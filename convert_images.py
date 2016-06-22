from wand.image import Image as WandImage
from wand.color import Color as WandColor
import StringIO
from webclient.models import Image, ImageLabel
from django.conf import settings
import re
import wand.exceptions
import os

def convertSVGtoPNG(img_file, foldername, filename, reconvert=False):
    #Convert copy of image to new format
    if not file:
        #TODO: Some error checking
        return
    #TODO: error checking on foldername and filename
    foldername_ = foldername
    if foldername_[0] == '/' or foldername_[0] == '\\':
        foldername_ = foldername_[1:]
    if foldername_[-1] == '/' or foldername_[-1] == '\\':
        foldername_ = foldername_[:-1]

    if not reconvert and os.path.exists(settings.STATIC_ROOT +  settings.LABEL_FOLDER_NAME + foldername + '/' + filename + '.png'):
         return
    try:
        with WandImage(file=img_file) as img:
            #img.depth = 1
            #img.colorspace = 'gray'

            #print(filename)
	    #print(WandColor('white'))

            img.background_color = WandColor('white')
            img.alpha_channel = 'remove'

            #Convert to black and white
            img.negate()
            img.threshold(0)
            img.negate()

            img.format = 'png'


            if not os.path.exists(settings.STATIC_ROOT +  settings.LABEL_FOLDER_NAME + foldername + '/'):
                os.makedirs(settings.STATIC_ROOT +  settings.LABEL_FOLDER_NAME + foldername + '/')
            img.save(filename=(settings.STATIC_ROOT +  settings.LABEL_FOLDER_NAME + foldername + '/' + filename + '.png'))
            print("converted Image " + filename)
 

    except wand.exceptions.CoderError as e:
        print('Failed to convert: ' + filename + ': '+ str(e))
    except wand.exceptions.MissingDelegateError as e:
        print('DE Failed to convert: ' + filename + ': '+ str(e))
    except wand.exceptions.WandError as e:
	print('Failed to convert ' + filename + ': '+ str(e))

def labelToSVGString(str):
    #Find width and height
    reWH = r'<image [^>]*(height="(?P<height>\d+)"[^>]* | width="(?P<width>\d+)"[^>]*){2}[^>]*/>'
    result = re.search(reWH, str)
    if result == None:
        #TODO: Some errory stuff
        return

    #Requires encoding as unicode format does not work
    height = result.group('height').encode('utf-8')
    width = result.group('width').encode('utf-8')

    if height == None or width == None:
        #TODO: Do some error stuff
        return

    SVGStringFile = StringIO.StringIO('<?xml version="1.0" encoding="UTF-8" standalone="no"?>' \
             '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg"' \
            ' xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" xml:space="preserve" height="%s"' \
             ' width="%s">%s</svg>\n' %(height, width, str.replace(result.group(0), '').encode('utf-8')) )
    SVGStringFile.seek(0)

    return SVGStringFile

def convertSVGs(LabelList, reconvert=False):
    for label in LabelList:
        convertSVG(label, reconvert)

def convertSVG(label, reconvert=False):
    convertSVGtoPNG(img_file=labelToSVGString(label.labelShapes), foldername=label.categoryType.category_name,
                    filename='P%iL%iC%sI%s' % (
                    label.parentImage.id, label.id, label.categoryType.category_name, label.parentImage.name),
                    reconvert=False)
def convertAll(reconvert=False):
    convertSVGs(ImageLabel.objects.all())
