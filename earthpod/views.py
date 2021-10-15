#Python imports
import datetime
import csv

#Django imports
from django.http import HttpResponse

#Django app imports
from .serializers import EarthPodDataSerializers #, EarthPodDataCSVSerializers
from earthpod.models import EarthPodData

# Rest Framework imports
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView


class EarthPodDataView(APIView):
    """
    View to save streaming earthpod data to the Database
    """

    def get(self, request, format=None):
        serializer = EarthPodDataSerializers(data=request.query_params)
        
        if serializer.is_valid():
            return_response = serializer.save()
            return Response(return_response , status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)


class EarthPodDataCSVView(APIView):
    """
    View to return a CSV file with data from Earthpods


    URL Parameters
    from_datetime: IN UNIX Format (Optional, Default is 1st January 2021)
    to_datetime: IN UNIX Format (Optional, Default value is Current Datetime)

    """

    def get(self, request, format=None):

        try:
            from_datetime = request.query_params.get('from_datetime', None)
            if from_datetime is None:
                from_datetime = datetime.datetime(2021, 1, 1, 0, 0, 0, 999999)
            else:
                from_datetime = datetime.datetime.utcfromtimestamp(int(from_datetime))
            
            to_datetime = request.query_params.get('to_datetime', None)
            if to_datetime is None:
                to_datetime = datetime.datetime.now()
            else:
                to_datetime = datetime.datetime.utcfromtimestamp(int(to_datetime))

            items = EarthPodData.objects.filter( datetime__gte = from_datetime ).filter(
                datetime__lte = to_datetime)
        except:
            return Response("Incorrect Datetime values", status=status.HTTP_404_NOT_FOUND)

        if len(items) == 0:
            return Response("No data found for given time", status=status.HTTP_200_OK)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        writer = csv.writer(response, delimiter = "," )

        writer.writerow(['earth_pod_id','datetime', 'datetime_pod', 'atmos_temperature', \
             'atmos_relative_humidity', 'atmos_pressure', 'soil_temperature', 'soil_relative_humidity'\
             'soil_moisture_2cm',  'soil_moisture_5cm', 'battery_voltage', 'light_analog'])

        for o in items:
            writer.writerow([o.earth_pod.pod_id, o.datetime, o.datetime_pod, o.atmos_temperature, \
            o.atmos_relative_humidity, o.atmos_pressure, o.soil_temperature, o.soil_relative_humidity, \
                    o.soil_moisture_2cm, o.soil_moisture_5cm, o.battery_voltage, o.light_analog ])
        return response