
#Django Imports
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import url
from django.urls import path


#Django App imports
from earthpod import views

urlpatterns = [
path('earthpoddata', views.EarthPodDataView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)