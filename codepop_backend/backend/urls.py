from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import CreateUserAPIView, LogoutUserAPIView, CustomAuthToken
from .views import UserPreferenceLookup, PreferencesOperations
from .views import DrinkOperations, UserDrinksLookup
from .views import InventoryListAPIView, InventoryReportAPIView, InventoryUpdateAPIView
from .views import NotificationOperations, UserNotificationLookup

#this ensures that the url calls the right function from the views for each type of request
preferences_list = PreferencesOperations.as_view({
    'get': 'list',
    'post': 'create'
})
#same as above ^
preferences_detail = PreferencesOperations.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

drink_list = DrinkOperations.as_view({
    'get': 'list',
    'post': 'create'
})

drink_detail = DrinkOperations.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

notification_list = NotificationOperations.as_view({
    'get': 'list',
    'post': 'create'
})

notification_detail = NotificationOperations.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
})

notification_filter_by_time = NotificationOperations.as_view({'get': 'filter_by_time'})


urlpatterns = [
    #Authentication related urls
    path('auth/login/', CustomAuthToken.as_view(), name='auth_user_login'),
    path('auth/register/', CreateUserAPIView.as_view(), name='auth_user_create'),
    path('auth/logout/', LogoutUserAPIView.as_view(), name='auth_user_logout'),

    # Preference-related URLs
    path('preferences/', preferences_list, name='preference_list_create'),  # List and create preferences
    path('preferences/<int:pk>/', preferences_detail, name='preference_detail'),  # Retrieve, update, or delete a preference

    # Retrieve preferences by UserID
    path('users/<int:user_id>/preferences/', UserPreferenceLookup.as_view(), name='user_preferences_list'),

    #Drink URLs
    #1. The /backend/drinks/ endpoint will return a list of
    #2. only the drinks that are not User created if you call it
    #3. with a basic GET request
    path('drinks/', drink_list, name='drink list and create'),
    path('drinks/<int:pk>/', drink_detail, name='drink operations'),

    # Retrieve Drinks by UserID
    path('users/<int:user_id>/drinks/', UserDrinksLookup.as_view(), name='user drink list'),

    #inventory related URLs
    path('inventory/', InventoryListAPIView.as_view(), name='inventory_list'),
    path('inventory/report/', InventoryReportAPIView.as_view(), name='inventory_report'),
    path('inventory/<int:pk>/', InventoryUpdateAPIView.as_view(), name='inventory_update'),

    # Notification related URLs
    path('notifications/', notification_list, name='notification list and create'),
    path('notifications/<int:pk>/', notification_detail, name='notification operations'),

    # Retrieve notifications by UserID
    path('users/<int:user_id>/notifications/', UserNotificationLookup.as_view(), name='user notifications list'),
    
     # Custom time-based notification filter
     # the get request sent in this format /notifications/filter_by_time/?start=2023-10-21T12:00:00Z&end=2023-10-21T18:00:00Z
     # the date should be in ISO 8601 format
    path('notifications/filter_by_time/', notification_filter_by_time, name='notification filter by time'),
]