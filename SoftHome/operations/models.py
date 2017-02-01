from django.db import models
from django.apps import apps


class Group(models.Model):
    name = models.CharField(max_length=50)
    controller_index = models.PositiveSmallIntegerField(default=0)   # #pk used by 3rd party controller
    manufacturer = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    all_on = models.BooleanField(default=False)
    any_on = models.BooleanField(default=False)
    classification = models.CharField(max_length=100, null=True, blank=True)
    action_state = models.BooleanField(default=False)
    devices = models.ManyToManyField("Portal.Device", related_name='grouped_in', null=True, blank=True)
    room = models.ForeignKey(Room, related_name='inside', null=True, blank=True)
    lights = models.ManyToManyField("MachineInterface.Light",
                                    through='LightGroup',
                                    related_name='grouped_in',
                                    null=True,
                                    blank=True
                                    )

    def __str__(self):
        return self.name

    @classmethod
    def import_all(cls, brand, controller):
        new_groups = []
        if brand == 'philips':
            groups = controller.get_group()
            for index, group in enumerate(groups):
                new_groups[index] = cls.objects.create(device=controller.device,
                                                       controller_index=group,
                                                       brightness=groups[group]['bri'],
                                                       ct=groups[group]['ct'],
                                                       alert=groups[group]['alert'],
                                                       reacheable=groups[group]['reachable'],
                                                       name=groups[group]['name'],
                                                       model_id=groups[group]['modelid'],
                                                       unique_id=groups[group]['uniqueid'],
                                                       manufacturer=brand
                                                       )
                new_groups[index].save()
        return new_groups

    def add_light(self, light):
        light_group, created = LightGroup.objects.get_or_create(
            group=self,
            light=light
        )
        return light_group

    def remove_light(self, light):
        LightGroup.objects.filter(
            group=self,
            light=light
        ).delete()


class LightGroup(models.Model):
    group = models.ForeignKey(Group, related_name='group')
    light = models.ForeignKey("MachineInterface.Light", related_name='light')
    brightness = models.PositiveSmallIntegerField(default=0)
    ct = models.PositiveIntegerField(default=0)
    alert = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.group.name

CONNECTION_TYPES = ((1, 'Wall'), (2, 'Door'), (3, 'Open Space'), (4, 'Counter/Half-wall'))
SIDES = ((1, 'Left'), (2, 'Right'), (3, 'Top'), (4, 'Bottom'))


class Room(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    windows = models.PositiveSmallIntegerField(default=0)
    outside_doors = models.PositiveSmallIntegerField(default=0)
    skylights = models.PositiveSmallIntegerField(default=0)
    room_connections = models.ManyToManyField("self",
                                              through='RoomConnection',
                                              symmetrical=False,
                                              related_name='connected_to+'
                                              )

    def __str__(self):
        return self.name

    def add_connection(self, room, connection, side, symm=True):
        connection, created = RoomConnection.objects.get_or_create(
            first_room=self,
            second_room=room,
            connection=connection,
            side=side
        )
        if symm:
            # left becomes right, top becomes bottom
            if side == 1:
                other_side = 2
            elif side == 2:
                other_side = 1
            elif side == 3:
                other_side = 4
            else:
                other_side = 3
            room.add_connection(self, connection, other_side, False)
        return connection

    def remove_connection(self, room, symm=True):
        RoomConnection.objects.filter(
            first_room=self,
            second_room=room
        ).delete()
        if symm:
            room.remove_connection(self, False)

    def get_connections(self, side):
        return self.room_connections.filter(
            first_room__side=side,
            first_room=self
        )

    def get_all_connections(self):
        return self.room_connections.filter(
            first_room=self
        )


class RoomConnection(models.Model):
    first_room = models.ForeignKey(Room, related_name='first_room')
    second_room = models.ForeignKey(Room, related_name='second_room')
    connection = models.PositiveSmallIntegerField(choices=CONNECTION_TYPES, default='Door')
    side = models.PositiveSmallIntegerField(choices=SIDES, default='Left')


class Condition(models.Model):
    status = models.BooleanField(default=False)
    device = models.ForeignKey("Portal.Device")
    device_state = models.CharField(max_length=30)
    operator = models.CharField(max_length=5)
    value = models.PositiveSmallIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.device.device.name


class Rule(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)
    recycle = models.BooleanField(default=True)
    status = models.BooleanField(default=False)
    condition_relations = models.CharField(max_length=50)
    conditions = models.ManyToManyField(Condition)

    def __str__(self):
        return self.name


class Action(models.Model):
    rule = models.ForeignKey(Rule)
    device = models.ForeignKey("Portal.Device")
    device_state = models.CharField(max_length=30)
    action = models.CharField(max_length=200, default="0")

    def __str__(self):
        return self.device.device_name
