from django.contrib import admin
from .models import Group, LightGroup, Room, RoomConnection, Condition, Rule, Action
# Register your models here.


admin.site.register([Group, LightGroup, Room, RoomConnection, Condition, Rule, Action])