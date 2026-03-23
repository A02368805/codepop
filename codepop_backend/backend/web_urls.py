from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.home, name='home'),
    path('login/', web_views.login_view, name='login'),
    path('logout/', web_views.logout_view, name='logout'),
    path('drinks/', web_views.drink_list, name='drink_list'),
    path('drinks/builder/', web_views.drink_builder, name='drink_builder'),
    path('drinks/calculate-price/', web_views.calculate_price, name='calculate_price'),
    path('drinks/create/', web_views.create_drink, name='create_drink'),
    path('drinks/<int:drink_id>/delete/', web_views.delete_drink, name='delete_drink'),
]
