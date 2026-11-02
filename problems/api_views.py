from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from .api_serializers import ProblemCreateSerializer


class ProblemCreateAPIView(CreateAPIView):
    serializer_class = ProblemCreateSerializer
    permission_classes = (IsAuthenticated,)
