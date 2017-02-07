from django.contrib import admin
from .models import WIFIHistory, LightHistory, SoundSensorHistory, MotionSensorHistory, OutletHistory, \
    LightSensorHistory, TemperatureSensorHistory
# Register your models here.

admin.site.register([WIFIHistory, LightHistory, SoundSensorHistory, MotionSensorHistory, OutletHistory,
                    LightSensorHistory, TemperatureSensorHistory])