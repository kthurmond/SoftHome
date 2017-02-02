from django.db import models
from django.conf import settings


class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(protocol='both')
    mac_address = models.CharField(max_length=100, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)
    device_type = models.CharField(max_length=100)
    api = models.CharField(max_length=100, default='softhome')

    def get_user_device_list(self):
        return Device.objects.filter(
            user=self,
            enable=True
        )

    def __str__(self):
        return self.device_name
