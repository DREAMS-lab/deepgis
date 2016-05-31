from django.template import loader
from django.http import *
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

from webclient.models import *
from datetime import datetime
from django.template import RequestContext

import os


from .models import Image

def index(request):
    #latest_image_list = os.listdir('C:/Users/Sandeep/Dropbox/kumar-prec-ag/tag_images') # '/Users/jdas/Dropbox/Research/agriculture/agdss/image-store/')
    latest_image_list = Image.objects.all()
    template = loader.get_template('webclient/index.html')

    context = {
        'latest_image_list': latest_image_list,
        'selected_image': latest_image_list[0],
    }
    return HttpResponse(template.render(context, request))


def results(request):
    template = loader.get_template('webclient/results.html')
    context = {}
    return HttpResponse(template.render(context, request))
@csrf_exempt
def applyLabels(request):
    dict = json.load(request)
    label_list_ = dict['label_list']
    image_name = dict['image_name']
    category_name = dict['category_name']
    sourceType = ''
    categoryType = ''
    parentImage_ = Image.objects.all().filter(name = image_name);
    categoryTypeList = CategoryType.objects.all().filter(category_name=category_name);
    if (categoryTypeList):
        categoryType = categoryTypeList[0]
    else:
        categoryType = CategoryType(category_name=category_name, pub_date=datetime.now())
        categoryType.save()

    sourceTypeList = ImageSourceType.objects.all().filter(description="human");
    if (sourceTypeList):
        sourceType = sourceTypeList[0]
    else:
        sourceType = ImageSourceType(description="human", pub_date=datetime.now())
        sourceType.save()


    if not parentImage_:

        parentImage_ = Image(name=image_name, path = '/static/tag_images/', description = "development test", source = sourceType, pub_date=datetime.now())
        parentImage_.save()
    else:
        labelObject = ImageLabel(parentImage = parentImage_[0], labelShapes=label_list_,pub_date=datetime.now(),categoryType=categoryType)
        labelObject.save()
    return JsonResponse(label_list_,safe=False)


def loadLabels(request):
    parentImage_ = request.GET['image_name']
    label_list = []
    sourceType = ''
    categoryType = ''
    sourceTypeList = ImageSourceType.objects.all().filter(description="human");
    if (sourceTypeList):
        sourceType = sourceTypeList[0]
    else:
        sourceType = ImageSourceType(description="human", pub_date=datetime.now())
        sourceType.save()


    image = Image.objects.all().filter(name = parentImage_)
    if not image:
        parentImage_ = Image(name=parentImage_, path='/static/tag_images/',description='test generation at serverside', source=sourceType, pub_date=datetime.now())
        parentImage_.save()
    else:
        label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    responseText = ''
    if(label_list):
        responseText = responseText + label_list.labelShapes
    return JsonResponse(responseText, safe=False)



@require_GET
def getInfo(request):
    parentImage_ = request.GET['image_name']
    label_list = []
    sourceType = ''
    categoryType = ''
    sourceTypeList = ImageSourceType.objects.all().filter(description="human");
    if (sourceTypeList):
        sourceType = sourceTypeList[0]
    else:
        sourceType = ImageSourceType(description="human", pub_date=datetime.now())
        sourceType.save()


    image = Image.objects.all().filter(name = parentImage_)
    if not image:
        parentImage_ = Image(name=parentImage_, path='/static/tag_images/',description='test generation at serverside', source=sourceType, pub_date=datetime.now())
        parentImage_.save()
    else:
        label_list = ImageLabel.objects.all().filter(parentImage=image[0]).order_by('pub_date').last()

    responseTextJSON = ''
    if(label_list): #?
        responseTextJSON = json.loads('' + label_list.labelShapes)
    response = {}
    response['labels'] = responseTextJSON
    print(responseTextJSON)
    response['path'] = image[0].path
    return JsonResponse(response, safe=False)


def purge(request):
    Image.objects.all().delete()
    ImageLabel.objects.all().delete()
    ImageSourceType.objects.all().delete()
    CategoryType.objects.all().delete()
    return HttpResponse("PURGED TABLES!")


'''
Request: POST
{
    path: location of image (not including image name itself. E.g. '/home/self/image-location/'). REQUIRED
    image-name:name of image REQUIRED
    description: A description NOT REQUIRED
    source_description: Description of image_source. NOT REQUIRED
    category: Category of the image (e.g. 'apple'). REQUIRED.
}

'''
@csrf_exempt
@require_POST
def addImage(request):
    sourceType = ImageSourceType(description=request.POST.get('source_description', default="human"), pub_date=datetime.now())
    sourceType.save()
    categoryType = CategoryType(category_name=request.POST[catgory], pub_date=datetime.now())
    categoryType.save()
    img = Image(name=request.POST['image-name'], path=request.POST['path'], description=request.POST.get('description', default=''), source=sourceType, pub_date=datetime.now())
    img.save()
    imgLabel = ImageLabel(parentImage=img, categoryType=categoryType, pub_date=datetime.now())
    imgLabel.save()
    return HttpResponse("Added image " + request.POST['image-name'])

