from __future__ import unicode_literals

from datetime import datetime
from unicodedata import decimal
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MaxValueValidator
import random
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db import models


class Color(models.Model):
    red = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(255)])
    green = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(255)])
    blue = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(255)])

    class Meta:
        unique_together = ('red', 'green', 'blue')

    def __str__(self):
        return "rgb({}, {}, {})".format(self.red, self.green, self.blue)


def get_default_Color():
    default_Color = Color.objects.all()
    if default_Color:
        default_Color = default_Color[0]
    else:
        default_Color = Color()
        default_Color.save()
    return default_Color.id


def get_color():
    if Color.objects.all().count() <= 1:
        with open('webclient/distinct_colors.txt') as f:
            for line in f:
                r, g, b = [int(n) for n in line.split()]
                Color.objects.get_or_create(red=r, green=g, blue=b)
    query = Color.objects.filter(categorytype=None)
    if query:
        return query[0]
    else:
        # return random color
        i = random.randrange(Color.objects.count())
        return Color.objects.all()[i]


class CategoryType(models.Model):
    category_name = models.CharField(default='unknown', max_length=100, unique=True)
    pub_date = models.DateTimeField(default=datetime.now, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True)
    label_type_enum = (
        ("R", "Rectangle"),
        ("C", "Circle"),
        ("P", "Polygon"),
        ("A", "Any")
    )
    label_type = models.CharField(
        max_length=1,
        choices=label_type_enum,
        default="C"
    )

    def __str__(self):
        return 'Category name: ' + self.category_name


class ImageSourceType(models.Model):
    description = models.CharField(default='unknown', max_length=200, unique=True)
    pub_date = models.DateTimeField(default=datetime.now, blank=True)

    def __str__(self):
        return 'Description: ' + self.description


class Image(models.Model):
    name = models.CharField(max_length=200)
    path = models.CharField(max_length=500)
    description = models.CharField(max_length=500)
    source = models.ForeignKey(ImageSourceType, on_delete=models.CASCADE)
    pub_date = models.DateTimeField(default=datetime.now, blank=True)
    width = models.PositiveSmallIntegerField(default=1920)
    height = models.PositiveSmallIntegerField(default=1080)
    # TODO: Cascade if last entry is deleted
    categoryType = models.ManyToManyField(CategoryType)

    class Meta:
        unique_together = ('name', 'path')

    def __str__(self):
        return 'Name: ' + self.name


class Labeler(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user)


class ImageWindow(models.Model):
    x = models.PositiveSmallIntegerField()
    y = models.PositiveSmallIntegerField()
    width = models.PositiveSmallIntegerField()
    height = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ('x', 'y', 'width', 'height')

    def __str__(self):
        return '(x,y)=(%d,%d), width: %d, height: %d' % (self.x, self.y, self.width, self.height)


def getDefaultImageWindowId():
    defaultImageWindowList = ImageWindow.objects.all().filter(x=0, y=0, width=1920, height=1080)
    if defaultImageWindowList:
        defaultImageWindow = defaultImageWindowList[0]
    else:
        defaultImageWindow = ImageWindow(x=0, y=0, width=1920, height=1080)
        defaultImageWindow.save()
    return defaultImageWindow.id


class ImageLabel(models.Model):
    parentImage = models.ForeignKey(Image, on_delete=models.CASCADE)
    combined_labelShapes = models.TextField(max_length=100000)
    pub_date = models.DateTimeField(default=datetime.now, blank=True)
    labeler = models.ForeignKey(Labeler, on_delete=models.CASCADE, null=True, blank=True, default=None)
    imageWindow = models.ForeignKey(ImageWindow, on_delete=models.CASCADE, default=getDefaultImageWindowId)
    timeTaken = models.PositiveIntegerField(null=True, default=None)

    def __str__(self):
        return 'Image: ' + self.parentImage.name + ' | Labeler: ' + str(self.labeler) + ' | Date: ' + str(self.pub_date)


class CategoryLabel(models.Model):
    categoryType = models.ForeignKey(CategoryType, on_delete=models.CASCADE)
    labelShapes = models.TextField(max_length=100000)
    parent_label = models.ForeignKey(ImageLabel, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.parent_label) + " | Category: {}".format(str(self.categoryType))


class ImageFilter(models.Model):
    brightness = models.DecimalField(max_digits=3, decimal_places=1, default=1)
    contrast = models.DecimalField(max_digits=3, decimal_places=1, default=1)
    saturation = models.DecimalField(max_digits=3, decimal_places=1, default=1)
    imageLabel = models.ForeignKey(ImageLabel, on_delete=models.CASCADE, null=True, blank=True, default=None)
    labeler = models.ForeignKey(Labeler, on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
        return 'ImageFilter: brightness:' + str(self.brightness) + ' contrast: ' + str(self.contrast) \
               + ' saturation: ' + str(self.saturation) + ' labeler: ' + str(self.labeler)

class SHPFile(models.Model):
    name = models.CharField(max_length=250)
    file = models.FileField(upload_to='shp_file/')

    def __str__(self):
        return str(self.name)


class TiledLabel(models.Model):
    northeast_Lat = models.DecimalField(max_digits=17, decimal_places=14)
    northeast_Lng = models.DecimalField(max_digits=17, decimal_places=14)
    southwest_Lat = models.DecimalField(max_digits=17, decimal_places=14)
    southwest_Lng = models.DecimalField(max_digits=17, decimal_places=14)
    zoom_level = models.PositiveSmallIntegerField(default=23)
    category = models.ForeignKey(CategoryType, on_delete=models.CASCADE, max_length=100, null=True, blank=True)
    
    label_json = JSONField()

    label_type_enum = (
        ("R", "Rectangle"),
        ("C", "Circle"),
        ("P", "Polygon"),
        ("A", "Any")
    )
    label_type = models.CharField(
        max_length=1,
        choices=label_type_enum,
        default="R"
    )


class TileSet(models.Model):
    base_location = models.CharField(max_length=600)


class Tile(models.Model):
    zoom_level = models.IntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    tile_set = models.ForeignKey(TileSet, on_delete=models.CASCADE)


class RasterImage(models.Model):
    name = models.CharField(max_length=5000, unique=True)
    path = models.CharField(max_length=5000)
    attribution = models.CharField(max_length=5000)
    minZoom = models.FloatField()
    maxZoom = models.FloatField()
    resolution = models.FloatField(default=-1)
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    has_bands = models.BooleanField(default = False)
    max_bands = models.IntegerField(default = 0)

    def __str__(self):
        return str(self.name)

    def bandAvailable(self, band_number):
        return self.has_bands and band_number >= 1 and band_number <= self.max_bands

    def getURL(self, band_number = 1):
        if self.has_bands == False:
            return self.path + "/{z}/{x}/{y}.png"
        elif self.bandAvailable(band_number):
            return self.path + "_" + str(band_number) + "/{z}/{x}/{y}.png"
        else:
            raise Exception("Not correct band_number")

    def getRaster(self, band_number = 1):
        if self.bandAvailable(band_number):
            name = self.name + "_" + str(band_number)
        else:
            name = self.name
        return {    "name": name,
                    "path": self.getURL(band_number),
                    "attribution": self.attribution,
                    "minZoom": self.minZoom,
                    "maxZoom": self.maxZoom,
                    "resolution": self.resolution,
                    "lat_lng": [self.latitude, self.longitude] 
                }

    def getLat_long(self):
        return [self.latitude, self.longitude]
    
    def getMaxZoom(self):
        return self.maxZoom


class TiledGISLabel(models.Model):
    northeast_Lat = models.DecimalField(max_digits=17, decimal_places=14)
    northeast_Lng = models.DecimalField(max_digits=17, decimal_places=14)
    southwest_Lat = models.DecimalField(max_digits=17, decimal_places=14)
    southwest_Lng = models.DecimalField(max_digits=17, decimal_places=14)
    parent_raster = models.ForeignKey(RasterImage, on_delete=models.CASCADE, null=True, blank=True, default=None)
    pub_date = models.DateTimeField(default=datetime.now, blank=True)
    labeler = models.ForeignKey(Labeler, on_delete=models.CASCADE, null=True, blank=True, default=None)
    zoom_level = models.PositiveSmallIntegerField(default=23)
    category = models.ForeignKey(CategoryType, on_delete=models.CASCADE, max_length=100, null=True, blank=True)
    shp_file = models.ForeignKey(SHPFile, on_delete=models.CASCADE, max_length=100, null=True, blank=True)

    label_json = JSONField()

    label_type_enum = (
        ("R", "Rectangle"),
        ("C", "Circle"),
        ("P", "Polygon"),
        ("A", "Any")
    )
    label_type = models.CharField(
        max_length=1,
        choices=label_type_enum,
        default="R"
    )
    geometry = models.GeometryField()


class VectorTileImage(models.Model):
    name = models.CharField(max_length=5000, unique=True)
    path = models.CharField(max_length=5000)
    attribution = models.CharField(max_length=5000)
    minZoom = models.FloatField()
    maxZoom = models.FloatField()
    resolution = models.FloatField(default=-1)
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)

    def __str__(self):
        return str(self.name)

    def getURL(self):
        return self.path + "/{z}/{x}/{y}.pbf"

    def getInfo(self):
        return {    "name": self.name,
                    "path": self.getURL(),
                    "attribution": self.attribution,
                    "minZoom": self.minZoom,
                    "maxZoom": self.maxZoom,
                    "resolution": self.resolution,
                    "lat_lng": [self.latitude, self.longitude] 
                }
