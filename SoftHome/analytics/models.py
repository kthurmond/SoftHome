from django.db import models
from django.apps import apps


class WIFIHistory(models.Model):
    device = models.ForeignKey("Portal.Device")
    ip_address = models.GenericIPAddressField(protocol='both')
    signal_strength = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    ssid = models.CharField(max_length=200)
    connection_time = models.DateTimeField(auto_now=True)
    gps_dd = models.CharField(max_length=30)

    def __str__(self):
        return self.device.device_name


class LightHistory(models.Model):
    light = models.ForeignKey("MachineInterface.Light")
    state = models.BooleanField(default=False)
    brightness = models.PositiveSmallIntegerField(default=0)
    ct = models.PositiveSmallIntegerField(default=0)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.light.name


class OutletHistory(models.Model):
    outlet = models.ForeignKey("MachineInterface.Outlet")
    power = models.IntegerField(default=0)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.outlet.name


class MotionSensorHistory(models.Model):
    sensor = models.ForeignKey("MachineInterface.Sensor")
    state = models.BooleanField(default=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sensor.name


class SoundSensorHistory(models.Model):
    sensor = models.ForeignKey("MachineInterface.Sensor")
    level = models.PositiveSmallIntegerField(default=0)
    recording = models.FileField(max_length=200)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sensor.name


class LightSensorHistory(models.Model):
    sensor = models.ForeignKey("MachineInterface.Sensor")
    level = models.PositiveSmallIntegerField(default=0)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sensor.name


class TemperatureSensorHistory(models.Model):
    sensor = models.ForeignKey("MachineInterface.Sensor")
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sensor.name
