import pickle
from matplotlib import pyplot as plot
import osr
import gdal
from descartes import PolygonPatch
import pylab as pl
from shapely.ops import cascaded_union, polygonize
from scipy.spatial import Delaunay
import numpy as np
import math
import shapely.geometry as geometry
from geojson import Polygon, Point, MultiPoint, GeometryCollection, Feature, FeatureCollection
import geojson
# Shell Plus Model Imports
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission, User
from django.contrib.sessions.models import Session
from webclient.models import CategoryLabel, CategoryType, Color, Image, ImageFilter, ImageLabel, ImageSourceType, ImageWindow, Labeler, Tile, TileSet, TiledLabel
# Shell Plus Django Imports
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField, ArrayField

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Avg, Case, Count, F, Max, Min, Prefetch, Q, Sum, When, Exists, OuterRef, Subquery
from django.db import transaction
from django.urls import reverse
import agdss.settings.common

plot.ion()
p = pickle.load(open("/home/jdas/registered_instances_v3.pickle","rb"))
ds = gdal.Open('/home/jdas/rock-tiles/C3_mask_v3.tif')
xoffset, px_w, rot1, yoffset, rot2, px_h = ds.GetGeoTransform()
crs = osr.SpatialReference()
crs.ImportFromWkt(ds.GetProjectionRef())
crsGeo = osr.SpatialReference()
crsGeo.ImportFromEPSG(4326)  # 4326 is the EPSG id of lat/long crs
t = osr.CoordinateTransformation(crs, crsGeo)



def xy2geo(y, x):

    posX = px_w * x + rot1 * y + xoffset
    posY = rot2 * x + px_h * y + yoffset
    posX += px_w / 2.0
    posY += px_h / 2.0
    return t.TransformPoint(posX, posY)

def bounding_box(iterable):
    min_x, min_y = np.min(iterable, axis=0)
    max_x, max_y = np.max(iterable, axis=0)
    return np.array([(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)])

def alpha_shape(points, alpha):
    """
    Compute the alpha shape (concave hull) of a set
    of points.
    @param points: Iterable container of points.
    @param alpha: alpha value to influence the
        gooeyness of the border. Smaller numbers
        don't fall inward as much as larger numbers.
        Too large, and you lose everything!
    """
    if len(points) < 4:
        # When you have a triangle, there is no sense
        # in computing an alpha shape.
        return geometry.MultiPoint(list(points)).convex_hull

    coords = points
    tri = Delaunay(coords)
    triangles = coords[tri.vertices]
    a = ((triangles[:,0,0] - triangles[:,1,0]) ** 2 + (triangles[:,0,1] - triangles[:,1,1]) ** 2) ** 0.5
    b = ((triangles[:,1,0] - triangles[:,2,0]) ** 2 + (triangles[:,1,1] - triangles[:,2,1]) ** 2) ** 0.5
    c = ((triangles[:,2,0] - triangles[:,0,0]) ** 2 + (triangles[:,2,1] - triangles[:,0,1]) ** 2) ** 0.5
    s = ( a + b + c ) / 2.0
    areas = (s*(s-a)*(s-b)*(s-c)) ** 0.5
    circums = a * b * c / (4.0 * areas)
    filtered = triangles[circums < (1.0 / alpha)]
    edge1 = filtered[:,(0,1)]
    edge2 = filtered[:,(1,2)]
    edge3 = filtered[:,(2,0)]
    edge_points = np.unique(np.concatenate((edge1,edge2,edge3)), axis = 0).tolist()
    m = geometry.MultiLineString(edge_points)
    triangles = list(polygonize(m))
    return cascaded_union(triangles), edge_points



for i in range(0,len(p)):

    new_points=p[i]['mask']
    alpha = .4
    try:
        concave_hull, edge_points = alpha_shape(new_points, alpha=alpha)
        xC, yC = concave_hull.exterior.coords.xy

        polyList = []
        for j in range(0,len(xC)):
            (long, lat, z) = xy2geo(xC[j], yC[j])
            polyList.append((float(long),float(lat)))

        properties = {"options": {"color": "rgb(255, 0, 0)", "weight": 0.5}}

        poly = Polygon([polyList])
        bbox = bounding_box(polyList)
        polyFeature = Feature(geometry=poly,properties=properties)
        label_json = geojson.dumps(polyFeature)
        northeast_Lat = bbox[0][1]
        northeast_Lng = bbox[0][0]
        southwest_Lat = bbox[1][1]
        southwest_Lng = bbox[1][0]
        zoom_level =23
        category = CategoryType.objects.filter(category_name='ai-annotation')[0]
        label_type = "P"
        tl = TiledLabel(label_json=geojson.loads(label_json), label_type=label_type, northeast_Lat=northeast_Lat,northeast_Lng=northeast_Lng,southwest_Lat=southwest_Lat,southwest_Lng=southwest_Lng,zoom_level=zoom_level,category=category)
        tl.save()
    except:
            print('skipping: ', i)



