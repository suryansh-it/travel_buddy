

# Create your views here.
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['GET'])
def homepage_view(request):
    return Response({"message": "Welcome to Travel App Curator!"})