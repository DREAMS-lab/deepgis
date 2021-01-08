from django.conf.urls import url
from webclient import views as views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path


urlpatterns = [
    path('', views.index, name='label_index'),
    path('label', views.label, name='label'),
    path('results', views.results, name='results'),
    path('view_label', views.view_label, name='view_label'),
    path('map_label', views.map_label, name='map_label'),
    path('addImage', views.add_image),
    path('cleanUpAndFixImages', views.clean_and_fix_images),
    path('updateImage', views.update_image),
    path('getInfo', views.get_info),
    path('getNewImage', views.get_new_image),
    path('convertAll', views.convert_all),
    path('unlabeledImages', views.unlabeled_images),
    path('numImageLabels', views.num_image_labels),
    path('combineAllImages', views.combine_all_images),
    path('calculateEntropyMap', views.calculate_entropy_map),
    path('applyLabels', views.apply_labels),
    path('createMasks', views.create_mask),
    path('loadLabels', views.load_labels),
    path('displayAnnotations', views.display_annotations),
    path('displayModels', views.display_models),
    url(r'^getLOLACraterAnnotations/$', views.get_lola_crater_annotations),
    url(r'^getAnnotations/$', views.get_annotations),
    url(r'^selectModels', views.select_models),
    url(r'^editImageLabel', views.edit_image_label),
    path('print_label_data', views.print_label_data),
    url(r'^get_overlayed_combined_image/(?P<image_label_id>[0-9]*)$', views.get_overlayed_combined_image),
    url(r'^get_overlayed_category_image/(?P<category_label_id>[0-9]*)$', views.get_overlayed_category_image),
    url(r'^get_overlayed_combined_gif/(?P<image_label_id>[0-9]*)$', views.get_overlayed_combined_gif),
    url(r'^get_all_tiled_labels/', views.get_all_tiled_labels, name='get_all_tiled_labels'),
    path('addTiledLabel', views.add_tiled_label),
    path('TiledLables', views.get_all_tiled_labels),
    path('WindowTiledLables', views.get_window_tiled_labels),
    path('addTiledImage', views.add_train_image_label),
    path('addTiledCategories', views.add_all_tiled_categories),
    path('deleteTileLabels', views.delete_tile_label),
    path('addCategory', views.add_new_category),
    path('getCategoryInfo', views.get_category_info),
    path('getTiledLabelCoordinates', views.get_tiled_label_coordinates),
    path('getCombinedLabelGeojson', views.get_combined_label_geojson),
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)