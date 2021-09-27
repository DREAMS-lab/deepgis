#Django app imports
from .serializers import EarthPodDataSerializers

#
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView


class EarthPodDataView(APIView):

    def get(self, request, format=None):
        serializer = EarthPodDataSerializers(data=request.query_params)
        
        if serializer.is_valid():
            return_response = serializer.save()
            return Response(return_response , status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)