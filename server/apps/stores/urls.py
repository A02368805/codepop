from django.urls import path

from .views import StoreIndexView

app_name = "stores"

urlpatterns = [
    path("", StoreIndexView.as_view(), name="index"),
]
