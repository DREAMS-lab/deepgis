from django.db import models

# Create your models here.

class EarthPod(models.Model):
    name = models.CharField(max_length=50)
    pod_id = models.IntegerField()
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return "Name:" + str(self.name) + ", Pod ID: " + str(self.pod_id)
        

class EarthPodData(models.Model):
    earth_pod = models.ForeignKey('EarthPod', on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    datetime_pod = models.DateTimeField(null=True, blank=True)
    atmos_temperature = models.FloatField(null=True, blank=True)
    atmos_relative_humidity = models.FloatField(null=True, blank=True)
    atmos_pressure = models.FloatField(null=True, blank=True)
    soil_temperature = models.FloatField(null=True, blank=True)
    soil_relative_humidity = models.FloatField(null=True, blank=True)
    soil_moisture_2cm = models.FloatField(null=True, blank=True)
    soil_moisture_5cm =  models.FloatField(null=True, blank=True)

    def __str__(self):
        return "Name:" + str(self.earth_pod.name) +  ", Datetime: " + str(self.datetime)


    def to_json(self):
        return {
            "earth_pod_name": str(self.earth_pod.name),
            "earth_pod_id": str(self.earth_pod.pod_id),
            "datetime": str(self.datetime),
            "datetime_pod": str(self.datetime_pod),
            "atmos_temperature": str(self.atmos_temperature),
            "atmos_relative_humidity": str(self.atmos_relative_humidity),
            "atmos_pressure" : str(self.atmos_pressure),
            "soil_temperature":str(self.soil_temperature),
            "soil_relative_humidity": str(self.soil_relative_humidity),
            "soil_moisture_2cm": str(self.soil_moisture_2cm),
            "soil_moisture_5cm": str(self.soil_moisture_5cm)
        }