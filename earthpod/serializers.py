# # Python imports
from datetime import datetime

# # Django imports
from rest_framework import serializers
from django.core.validators import MaxValueValidator, MinValueValidator
from django.http import Http404

# #Django app imports
from .models import EarthPodData, EarthPod


class EarthPodDataSerializers(serializers.Serializer):
    id = serializers.CharField()
    datetime_pod = serializers.IntegerField(required=False, validators=[MaxValueValidator(2147483647), MinValueValidator(1)])
    atmos_temperature = serializers.FloatField(required=False)
    atmos_relative_humidity = serializers.FloatField(required=False)
    atmos_pressure = serializers.FloatField(required=False)
    soil_temperature = serializers.FloatField(required=False)
    soil_relative_humidity = serializers.FloatField(required=False)
    soil_moisture_2cm = serializers.FloatField(required=False)
    soil_moisture_5cm =  serializers.FloatField(required=False)
    battery_voltage = serializers.FloatField(required=False)
    light_analog = serializers.FloatField(required=False)

    def save(self):
        try:
            earth_pod = EarthPod.objects.get(pod_id = self.validated_data.pop('id'))
        except:
            raise Http404("Earth Pod does not exist")

        datetime_pod = self.validated_data.pop('datetime_pod', None)
        if datetime_pod is not None:
            datetime_pod = datetime.fromtimestamp(datetime_pod)

        earth_pod_data_obj = EarthPodData.objects.create(
            earth_pod = earth_pod,
            datetime = datetime.now(),
            datetime_pod = datetime_pod,
            atmos_temperature = self.validated_data.pop('atmos_temperature', None),
            atmos_relative_humidity = self.validated_data.pop('atmos_relative_humidity', None),
            atmos_pressure = self.validated_data.pop('atmos_pressure', None),
            soil_temperature = self.validated_data.pop('soil_temperature', None), 
            soil_relative_humidity = self.validated_data.pop('soil_relative_humidity', None), 
            soil_moisture_2cm = self.validated_data.pop('soil_moisture_2cm', None), 
            soil_moisture_5cm = self.validated_data.pop('soil_moisture_5cm', None),
            battery_voltage = self.validated_data.pop('battery_voltage', None),
            light_analog = self.validated_data.pop('light_analog', None),
        )
        return earth_pod_data_obj.to_json()


# class EarthPodDataCSVSerializers(serializers.Serializer):
#     from_datetime = serializers.IntegerField(required=False, validators=[MaxValueValidator(2147483647), MinValueValidator(1)])
#     to_datetime = serializers.IntegerField(required=False, validators=[MaxValueValidator(2147483647), MinValueValidator(1)])()

#     def validate_from_datetime(self, value):
#         """
#         Validate from Datetime Field
#         """
#         return datetime.utcfromtimestamp(value)

#     def validate_from_datetime(self, value):
#         """
#         Validate from Datetime Field
#         """
#         return datetime.utcfromtimestamp(value)
