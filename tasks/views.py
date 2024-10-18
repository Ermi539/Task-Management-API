
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from .models import Task
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from . import serializers
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

TaskSerializer = serializers.TaskSerializer
UserSerializer = serializers.UserSerializer

class StandardResultsSetPagination(PageNumberPagination):
  page_size = 10
  page_size_query_param = 'page_size'
  max_page_size = 100


class TaskList(generics.ListCreateAPIView):
  queryset = Task.objects.all()
  serializer_class = TaskSerializer
  permission_classes = [IsAuthenticated]
  pagination_class = StandardResultsSetPagination

  def get_queryset(self):
    user = self.request.user
    return Task.objects.filter(user=user)

  def perform_create(self, serializer):
    serializer.save(user=self.request.user)


class TaskDetail(generics.RetrieveUpdateDestroyAPIView):
  serializer_class = TaskSerializer
  permission_classes = [IsAuthenticated]
  lookup_field = 'pk'

  def get_queryset(self):
    user = self.request.user
    return Task.objects.filter(user=user)

  def perform_update(self, serializer):
    instance = serializer.instance
    if instance.status == 'C' and serializer.validated_data.get('status') == 'P':
      instance.mark_incomplete()
      serializer.save()
    else:
      serializer.save()


class TaskComplete(APIView):
  authentication_classes = [JWTAuthentication]
  permission_classes = [IsAuthenticated]

  def post(self, request, pk):
    try:
      task = Task.objects.get(pk=pk, user=request.user)
      if task.status == 'P':
        task.mark_complete()
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)
      else:
        return Response({"message": "Task is already completed."}, status=status.HTTP_400_BAD_REQUEST)
    except Task.DoesNotExist:
      return Response({"message": "Task not found."}, status=status.HTTP_404_NOT_FOUND)


class TaskIncomplete(APIView):
  authentication_classes = [JWTAuthentication]
  permission_classes = [IsAuthenticated]

  def post(self, request, pk):
    try:
      task = Task.objects.get(pk=pk, user=request.user)
      if task.status == 'C':
        task.mark_incomplete()
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)
      else:
        return Response({"message": "Task is already incomplete."}, status=status.HTTP_400_BAD_REQUEST)
    except Task.DoesNotExist:
      return Response({"message": "Task not found."}, status=status.HTTP_404_NOT_FOUND)


class UserList(generics.ListCreateAPIView):
  queryset = User.objects.all()
  serializer_class = UserSerializer
  permission_classes = [permissions.AllowAny]


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
  queryset = User.objects.all()
  serializer_class = UserSerializer
  permission_classes = [permissions.AllowAny]

  def perform_update(self, serializer):
    user = serializer.save()
    token = Token.objects.get_or_create(user=user)[0]
    data = serializer.data
    data['token'] = token.key
    return Response(data)


class CustomAuthToken(ObtainAuthToken):
  def post(self, request, *args, **kwargs):
    serializer = self.serializer_class(data=request.data,
                     context={'request': request})
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    token = Token.objects.get_or_create(user=user)[0]
    refresh = RefreshToken.for_user(user)
    return Response({
      'token': token.key,
      'refresh': str(refresh),
      'user': UserSerializer(user).data
    })

@require_GET
def api_root(request):
    return JsonResponse({
        "message": "Welcome to the Task Management API",
        "available_endpoints": [
            "/api/tasks/",
            "/api/users/",
            "/api/auth/token/",
            "/api/auth/token/refresh/"
        ]

    })

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all()
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        task = self.get_object()
        if task.status == 'Completed':
            raise serializers.ValidationError("Cannot edit a completed task.")
        serializer.save()

    
