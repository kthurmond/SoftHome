from django.db import models
from django.apps import apps
from MachineInterface.models import Light


CONNECTION_TYPES = ((1, 'Wall'), (2, 'Door'), (3, 'Open Space'), (4, 'Counter/Half-wall'))
SIDES = ((1, 'Left'), (2, 'Right'), (3, 'Top'), (4, 'Bottom'))


class Group(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, null=True, blank=True)
    action_state = models.BooleanField(default=False)
    all_on = models.BooleanField(default=False)
    any_on = models.BooleanField(default=False)
    controller = models.ForeignKey("Portal.Device", related_name="group_controller", null=True, blank=True)
    controller_index = models.PositiveSmallIntegerField(default=0)   # #pk used by 3rd party controller
    subgroups = models.ManyToManyField("self",
                                       symmetrical=False,
                                       related_name='get_subgroups',
                                       related_query_name='get_super_groups'
                                       )

    def __str__(self):
        return self.name


class LightGroup(Group):
    group = models.OneToOneField(Group, parent_link=True, related_name='light_group')
    lights = models.ManyToManyField("Portal.Device", related_name='lights')
    brightness = models.PositiveSmallIntegerField(default=0)
    colormode = models.CharField(max_length=100, default='ct')
    color_temperature = models.PositiveIntegerField(default=153)
    color_cie_xy = models.CharField(max_length=100, default='[0.31306, 0.32318]')
    alert = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name

    @classmethod
    def import_all(cls, api, controller):
        new_groups = []
        if api == 'philips':
            groups = controller.get_group()
            for group in groups:
                color_ct = 153
                color_cie = '[0.31306, 0.32318]'
                if 'ct' in groups[group]['action']:
                    color_ct = int(groups[group]['action']['ct'])
                    color_cie = Light.convert_color(groups[group]['action']['ct'])
                elif 'xy' in groups[group]['action']:
                    color_cie = groups[group]['action']['xy']
                    color_ct = Light.convert_color(int(groups[group]['action']['xy']))

                new_group, created = cls.objects.update_or_create(
                    type='DeviceGroup',
                    controller=controller.philips_device,
                    controller_index=int(group),
                    name=groups[group]['name'],
                    defaults={
                        'action_state': groups[group]['action']['on'],
                        'all_on': groups[group]['state']['all_on'],
                        'any_on': groups[group]['state']['any_on'],
                        'brightness': int(groups[group]['action']['bri']),
                        'color_temperature': color_ct,
                        'color_cie_xy': color_cie,
                        'colormode': groups[group]['action']['colormode'],
                        'alert': groups[group]['action']['alert'],
                    }
                    )

                new_groups.append(new_group)
                new_groups[-1].save()

                new_groups[-1].lights.clear()
                for light in groups[group]['lights']:
                    new_light = Light.objects.filter(controller_index=int(light), controller=controller.philips_device)
                    if new_light.count()>0:
                        new_groups[-1].lights.add(new_light[0].light_device)

        return new_groups


class Room(Group):
    group = models.ForeignKey(Group, parent_link=True, related_name='room_group')
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
        connection = RoomConnection(
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
    get_state = models.CharField(max_length=30)
    operator = models.CharField(max_length=5)
    value = models.PositiveSmallIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.device.name


class Rule(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)
    recycle = models.BooleanField(default=True)
    status = models.BooleanField(default=False)
    conditions = models.ManyToManyField(Condition, related_name='conditions')
    condition_relations = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Action(models.Model):
    rule = models.ForeignKey(Rule)
    device = models.ForeignKey("Portal.Device")
    set_state = models.CharField(max_length=30)
    action = models.CharField(max_length=200, default="0")

    def __str__(self):
        return self.rule.name
