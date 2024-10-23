from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.generics import CreateAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import status, viewsets
from rest_framework.views import APIView
from .models import Preference, Drink
from .serializers import CreateUserSerializer, PreferenceSerializer,    DrinkSerializer
from rest_framework.permissions import IsAuthenticated

#Custom login to so that it get's a token but also the user's first name and the user id
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'first_name': user.first_name,
            
        })

#Code to create a user in the database
class CreateUserAPIView(CreateAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # We create a token than will be used for future auth
        token = Token.objects.create(user=serializer.instance)
        token_data = {"token": token.key}
        return Response(
            {**serializer.data, **token_data},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class LogoutUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Delete the token to log out the user
        request.user.auth_token.delete()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
    
class PreferencesOperations(viewsets.ModelViewSet):
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer

    def create(self, request, *args, **kwargs):
        # Custom logic for creating a drink can go here
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Custom logic for updating a drink can go here
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Custom logic for deleting a drink can go here
        return super().destroy(request, *args, **kwargs)

class UserPreferenceLookup(ListAPIView):
    serializer_class = PreferenceSerializer

    # Override get_queryset to filter preferences by the provided UserID
    def get_queryset(self):
        user_id = self.kwargs['user_id']  # Retrieve the 'user_id' from the URL
        # Check if the user exists first, and raise a 404 if not
        user = get_object_or_404(User, pk=user_id)
        return Preference.objects.filter(UserID=user_id)
    
class DrinkOperations(viewsets.ModelViewSet):
    queryset = Drink.objects.all()
    serializer_class = DrinkSerializer

    def get_queryset(self):
        # Modify the basic GET request behavior so it only returns drinks not user created
        return Drink.objects.filter(User_Created=False)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Only authenticated users can create, update, or delete a drink.
        """
        if self.action in ['create', 'update', 'destroy']:
            # Require authentication for create, update, and destroy actions
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        # Custom logic for creating a drink
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Custom logic for updating a drink
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Custom logic for deleting a drink
        return super().destroy(request, *args, **kwargs)

class UserDrinksLookup(ListAPIView):
    serializer_class = DrinkSerializer
    permission_classes = [IsAuthenticated]

    # Override get_queryset to filter preferences by the provided UserID
    def get_queryset(self):
        user_id = self.kwargs['user_id']  # Retrieve the 'user_id' from the URL
        # Check if the user exists first, and raise a 404 if not
        user = get_object_or_404(User, pk=user_id)
        return Drink.objects.filter(Favorite=user_id)