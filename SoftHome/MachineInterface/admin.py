from django.contrib import admin
from .models import Sensor, Light, Scene, WIFILocation, PhilipsHueBridge, Outlet
# Register your models here.


admin.site.register([Sensor, Light, Scene, WIFILocation, PhilipsHueBridge, Outlet])