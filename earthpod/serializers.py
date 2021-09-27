# # Python imports
from datetime import datetime

# # Django imports
from rest_framework import serializers
from django.http import Http404

# #Django app imports
from .models import EarthPodData, EarthPod


class EarthPodDataSerializers(serializers.Serializer):
    id = serializers.CharField()
    atmos_temperature = serializers.FloatField(required=False)
    atmos_relative_humidity = serializers.FloatField(required=False)
    atmos_pressure = serializers.FloatField(required=False)
    soil_temperature = serializers.FloatField(required=False)
    soil_relative_humidity = serializers.FloatField(required=False)
    soil_moisture_2cm = serializers.FloatField(required=False)
    soil_moisture_5cm =  serializers.FloatField(required=False)

    def save(self):
        try:
            earth_pod = EarthPod.objects.get(id = self.validated_data.pop('id'))
        except:
            print("Eroorrrrrrrrrrrrrr")
            raise Http404("Earth Pod does not exist")

        
        earth_pod_data_obj = EarthPodData.objects.create(
            earth_pod = earth_pod,
            datetime = datetime.now(),
            atmos_temperature = self.validated_data.pop('atmos_temperature', None),
            atmos_relative_humidity = self.validated_data.pop('atmos_relative_humidity', None),
            atmos_pressure = self.validated_data.pop('atmos_pressure', None),
            soil_temperature = self.validated_data.pop('soil_temperature', None), 
            soil_relative_humidity = self.validated_data.pop('soil_relative_humidity', None), 
            soil_moisture_2cm = self.validated_data.pop('soil_moisture_2cm', None), 
            soil_moisture_5cm = self.validated_data.pop('soil_moisture_5cm', None)
        )
        return earth_pod_data_obj.to_json()