from django.urls import path
from .views import index, devices_map
from .views import send_sms_view

urlpatterns = [
    path('', index),
    path('send/', send_sms_view),
    path('map/', devices_map, name='devices_map'),

]
