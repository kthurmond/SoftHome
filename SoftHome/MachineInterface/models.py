import json
import socket
import http.client as httplib
from decimal import *
from django.db import models
from django.apps import apps
from django.contrib.auth.models import User
from Portal.models import Device


class WIFILocation(Device):
    device = models.OneToOneField(Device, parent_link=True, related_name='wifi_device')
    ssid = models.CharField(max_length=200, null=True, blank=True)
    signal_strength = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)
    gps_dd = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Sensor(Device):
    device = models.OneToOneField(Device, parent_link=True, related_name='sensor_device')
    state = models.DecimalField(max_digits=8, decimal_places=2)
    type = models.CharField(max_length=100)
    timelapse = models.FileField(max_length=200, null=True, blank=True)
    reachable = models.BooleanField(default=False)
    model_id = models.CharField(max_length=100)
    unique_id = models.CharField(max_length=100, null=True, blank=True)
    controller = models.ForeignKey("Portal.Device", related_name='sensor_controller', null=True, blank=True)
    controller_index = models.PositiveSmallIntegerField(default=0)   # #pk used by 3rd party controller

    def __str__(self):
        return self.name

    @classmethod
    def import_all(cls, api, controller):
        new_sensors = []
        if api == 'philips':
            sensors = controller.get_sensor()
            for sensor in sensors:
                state_value = 0
                for key in sensors[sensor]['state']:
                    if key != 'lastupdated':
                        state = key
                        if sensors[sensor]['state'][state] == 'false':
                            state_value = 0
                        elif sensors[sensor]['state'][state] == 'true':
                            state_value = 1
                        else:
                            state_value = Decimal(sensors[sensor]['state'][state])
                        break

                new_sensor, created = cls.objects.update_or_create(
                    user=controller.user,
                    type=sensors[sensor]['type'],
                    model_id=sensors[sensor]['modelid'],
                    unique_id=sensors[sensor].get('uniqueid'),
                    controller=controller.philips_device,
                    controller_index=int(sensor),
                    name=sensors[sensor]['name'],
                    device_type='sensor',
                    api=api,
                    defaults={
                        'state': state_value,
                        'reachable': True,
                        'ip_address': controller.ip_address,
                        'mac_address': controller.mac_address,
                    }
                    )

                new_sensors.append(new_sensor)
                new_sensors[-1].save()
        return new_sensors


class Light(Device):
    device = models.OneToOneField(Device, parent_link=True, related_name='light_device')
    state = models.BooleanField(default=False)
    brightness = models.PositiveSmallIntegerField(default=0)
    colormode = models.CharField(max_length=100, default='ct')
    type = models.CharField(max_length=100, default='Color temperature light')
    color_temperature = models.PositiveSmallIntegerField(default=153)
    color_cie_xy = models.CharField(max_length=100, default='[0.31306, 0.32318]')
    alert = models.CharField(max_length=50, null=True, blank=True)
    reachable = models.BooleanField(default=False)
    model_id = models.CharField(max_length=100)
    unique_id = models.CharField(max_length=100)
    controller = models.ForeignKey("Portal.Device", related_name='light_controller', null=True, blank=True)
    controller_index = models.PositiveSmallIntegerField(default=0)   # #pk used by 3rd party controller

    def __str__(self):
        return self.name

    @classmethod
    def import_all(cls, api, controller):
        new_lights = []
        if api == 'philips':
            lights = controller.get_light()
            for light in lights:
                color_ct = 153
                color_cie = '[0.31306, 0.32318]'
                if 'ct' in lights[light]['state']:
                    color_ct = int(lights[light]['state']['ct'])
                    color_cie = cls.convert_color(lights[light]['state']['ct'])
                elif 'xy' in lights[light]['state']:
                    color_cie = lights[light]['state']['xy']
                    color_ct = cls.convert_color(int(lights[light]['state']['xy']))

                new_light, created = cls.objects.update_or_create(
                    user=controller.user,
                    model_id=lights[light]['modelid'],
                    unique_id=lights[light]['uniqueid'],
                    controller=controller.philips_device,
                    controller_index=int(light),
                    name=lights[light]['name'],
                    device_type='light bulb',
                    api=api,
                    defaults={
                        'state': lights[light]['state']['on'],
                        'brightness': int(lights[light]['state']['bri']),
                        'color_temperature': color_ct,
                        'color_cie_xy': color_cie,
                        'colormode': lights[light]['state']['colormode'],
                        'alert': lights[light]['state']['alert'],
                        'reachable': lights[light]['state']['reachable'],
                        'type': lights[light]['type'],
                        'ip_address': controller.ip_address,
                        'mac_address': controller.mac_address,
                    }
                    )
                new_lights.append(new_light)
                new_lights[-1].save()
        return new_lights

    def on(self, transition_time=None):
        if self.api == 'philips':
            hub = PhilipsHueBridge.objects.get(device=self.controller.philips_device)
            result = hub.set_light(self.controller_index, 'on', True, transition_time)
            if 'error' in list(result[-1][0].keys()):
                return False
            else:
                self.state = True
                self.save()
                return True

    def off(self, transition_time=None):
        if self.api == 'philips':
            hub = PhilipsHueBridge.objects.get(device=self.controller.philips_device)
            result = hub.set_light(self.controller_index, 'on', False, transition_time)
            if 'error' in list(result[-1][0].keys()):
                return False
            else:
                self.state = False
                self.save()
                return True

    def set_brightness(self, brightness, percentage=False, transition_time=None):
        if percentage is True:
            brightness = brightness*255/100
        if self.api == 'philips':
            hub = PhilipsHueBridge.objects.get(device=self.controller.philips_device)
            result = hub.set_light(self.controller_index, 'bri', brightness, transition_time)
            if 'error' in list(result[-1][0].keys()):
                return False
            else:
                self.brightness = brightness
                self.save()
                return True

    def set_color(self, ct, transition_time=None):
        if self.api == 'philips':
            hub = PhilipsHueBridge.objects.get(device=self.controller.philips_device)
            result = hub.set_light(self.controller_index, 'ct', ct, transition_time)
            if 'error' in list(result[-1][0].keys()):
                return False
            else:
                self.ct = ct
                self.save()
                return True

    @staticmethod
    def convert_color(color):
        if isinstance(color, str):
            # TODO Complete function
            # xy to Color temperature
            xy = color[1:-1].split(',')
            y = Decimal(xy[1])
            x = Decimal(xy[0])
            return x + y
        elif isinstance(color, int):
            # Color temperature to xy
            T = 1000000/color  # #Mired to temperature (K)
            x = -4.607*10**9/T**3 + 2.9678*10**6/T**2 + 0.09911*10**3/T + 0.244063
            y = -3*x**2 + 2.87*x - 0.275
            return '[{0}, {1}]'.format(x, y)
        return False


class Scene(models.Model):
    name = models.CharField(max_length=100)
    ct = models.PositiveSmallIntegerField(default=0)
    brightness = models.PositiveSmallIntegerField(default=0)
    picture = models.FileField(max_length=200, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PhilipsHueBridge(Device):
    device = models.OneToOneField(Device, parent_link=True, related_name='philips_device')
    bridge_user = models.CharField(max_length=100, default='None')
    bridge_id = models.CharField(max_length=100, default='None')
    swversion = models.CharField(max_length=50, default='None')

    def __str__(self):
        return self.name

    @classmethod
    def register(cls, ip_address):
        try:
            user = User.objects.get(username='default_machine')
        except User.DoesNotExist:
            user = User.objects.create_user('default_machine', password='default_machine')
            user.save()

        bridge = cls.objects.create(user=user,
                                    name='Philips Hue Bridge',
                                    ip_address=ip_address,
                                    device_type='controller',
                                    api='philips'
                                    )

        registration_request = {"devicetype": "python_hue"}
        response = bridge.request('POST', '/api', registration_request)
        for line in response:
            for key in line:
                if 'success' in key:
                    bridge.bridge_user = line['success']['username']
                    bridge.save()
                if 'error' in key:
                    error_type = line['error']['type']
                    if error_type == 101:
                        return error_type
            # raise HueRegistrationException(error_type, 'The link button has not been pressed in the last 30 seconds.')
                    if error_type == 7:
                        return error_type
                        # raise HueException(error_type, 'Unknown username')

        bridge.update_config()
        return bridge

    def request(self, mode='GET', address=None, data=None):
        """ Utility function for HTTP GET/PUT requests for the API"""
        connection = httplib.HTTPConnection(self.ip_address, timeout=10)

        try:
            if mode == 'GET' or mode == 'DELETE':
                connection.request(mode, address)
            if mode == 'PUT' or mode == 'POST':
                connection.request(mode, address, json.dumps(data))

        except socket.timeout:
            error = "{} Request to {}{} timed out.".format(mode, self.ip, address)
            raise TimeoutError(None, error)

        result = connection.getresponse()
        connection.close()

        return json.loads(str(result.read(), encoding='utf-8'))

    def import_all(self):
        LightGroup = apps.get_model('operations', 'LightGroup')
        lights = Light.import_all(self.api, self)
        sensors = Sensor.import_all(self.api, self)
        groups = LightGroup.import_all(self.api, self)
        return {'lights': lights, 'sensors': sensors, 'groups': groups}

    def update_config(self):
        address = '/api/' + self.bridge_user + '/config/'
        response = self.request(mode='GET', address=address)

        self.swversion = response['swversion']
        self.bridge_id = response['bridgeid']
        self.mac_address = response['mac']
        self.save()

    #  Lights
    def get_light(self, light_id=None, parameter=None):
        """ Gets state by light_id and parameter"""

        if isinstance(light_id, str):
            light_id = self.get_light_id_by_name(light_id)
        if light_id is None:
            return self.request('GET', '/api/' + self.bridge_user + '/lights/')
        state = self.request('GET', '/api/' + self.bridge_user + '/lights/' + str(light_id))
        if parameter is None:
            return state
        if parameter in ['name', 'type', 'uniqueid', 'swversion']:
            return state[parameter]
        else:
            try:
                return state['state'][parameter]
            except KeyError:
                return False

    def get_light_id_by_name(self, name):
        """ Lookup a light id based on string name. Case-sensitive. """
        lights = self.get_light()
        for light_id in lights:
            if name == lights[light_id]['name']:
                return light_id
        return False

    def set_light(self, light_id, parameter, value=None, transitiontime=None):
        """ Adjust properties of one or more lights.
        light_id can be a single lamp or an array of lamps
        parameters: 'on' : True|False , 'bri' : 0-254, 'sat' : 0-254, 'ct': 154-500
        transitiontime : in **deciseconds**, time for this transition to take place
                         Note that transitiontime only applies to *this* light
                         command, it is not saved as a setting for use in the future!
                         Use the Light class' transitiontime attribute if you want
                         persistent time settings.
        """
        if isinstance(parameter, dict):
            data = parameter
        else:
            data = {parameter: value}

        if transitiontime is not None:
            data['transitiontime'] = int(round(transitiontime))  # must be int for request format

        light_id_array = light_id
        if isinstance(light_id, int) or isinstance(light_id, str):
            light_id_array = [light_id]
        result = []
        for light in light_id_array:
            if parameter == 'name':
                result.append(self.request('PUT', '/api/' + self.bridge_user + '/lights/' + str(light_id), data))
            else:
                if isinstance(light, str):
                    converted_light = self.get_light_id_by_name(light)
                else:
                    converted_light = light
                result.append(self.request(
                    'PUT', '/api/' + self.bridge_user + '/lights/' + str(converted_light) + '/state', data))

        return result

    #  Sensors
    def get_sensor_id_by_name(self, name):
        """ Lookup a sensor id based on string name. Case-sensitive. """
        sensors = self.get_sensor()
        for sensor_id in sensors:
            if name == sensors[sensor_id]['name']:
                return sensor_id
        return False

    def create_sensor(self, name, modelid, swversion, sensor_type,
                      uniqueid, manufacturername, state, config, recycle=False):
        """ Create a new sensor in the bridge. Returns (ID,None) of the new sensor or (None,message)
        if creation failed. """
        data = {
            "name": name,
            "modelid": modelid,
            "swversion": swversion,
            "type": sensor_type,
            "uniqueid": uniqueid,
            "manufacturername": manufacturername,
            "recycle": recycle
        }
        if isinstance(state, dict) and state != {}:
            data["state"] = state

        if isinstance(config, dict) and config != {}:
            data["config"] = config

        result = self.request('POST', '/api/' + self.bridge_user + '/sensors/', data)

        if "success" in result[0].keys():
            new_id = result[0]["success"]["id"]
            return new_id, None
        else:
            return None, result[0]

    def get_sensor(self, sensor_id=None, parameter=None):
        """ Gets state by sensor_id and parameter"""

        if isinstance(sensor_id, str):
            sensor_id = self.get_sensor_id_by_name(sensor_id)
        if sensor_id is None:
            return self.request('GET', '/api/' + self.bridge_user + '/sensors/')
        data = self.request('GET', '/api/' + self.bridge_user + '/sensors/' + str(sensor_id))

        if isinstance(data, list):
            return None

        if parameter is None:
            return data
        return data[parameter]

    def set_sensor(self, sensor_id, parameter, value=None):
        """ Adjust properties of a sensor
        sensor_id must be a single sensor.
        parameters: 'name' : string
        """
        if isinstance(parameter, dict):
            data = parameter
        else:
            data = {parameter: value}

        result = self.request('PUT', '/api/' + self.bridge_user + '/sensors/' + str(sensor_id), data)
        return result

    def set_sensor_content(self, sensor_id, parameter, value=None, structure="state"):
        """ Adjust the "state" or "config" structures of a sensor"""

        if structure != "state" and structure != "config":
            # logger.debug("set_sensor_current expects structure 'state' or 'config'.")
            return False

        if isinstance(parameter, dict):
            data = parameter.copy()
        else:
            data = {parameter: value}

        # Attempting to set this causes an error.
        del data["lastupdated"]

        result = self.request('PUT', '/api/' + self.bridge_user + '/sensors/' + str(sensor_id) + "/" + structure, data)
        # if 'error' in list(result[0].keys()):
        # logger.warn("ERROR: {0} for sensor {1}".format(result[0]['error']['description'], sensor_id))
        return result

    def delete_sensor(self, sensor_id):
        try:
            return self.request('DELETE', '/api/' + self.bridge_user + '/sensors/' + str(sensor_id))
        except:
            return None

    # Groups
    def get_group(self, group_id=None, parameter=None):
        if isinstance(group_id, str):
            group_id = self.get_group_id_by_name(group_id)
        if group_id is False:
            # logger.error('Group name does not exit')
            return
        if group_id is None:
            return self.request('GET', '/api/' + self.bridge_user + '/groups/')
        if parameter is None:
            return self.request('GET', '/api/' + self.bridge_user + '/groups/' + str(group_id))
        elif parameter == 'name' or parameter == 'lights':
            return self.request('GET', '/api/' + self.bridge_user + '/groups/' + str(group_id))[parameter]
        else:
            return self.request('GET', '/api/' + self.bridge_user + '/groups/' + str(group_id))['action'][parameter]

    def get_group_id_by_name(self, name):
        """ Lookup a group id based on string name. Case-sensitive. """
        groups = self.get_group()
        for group_id in groups:
            if name == groups[group_id]['name']:
                return group_id
        return False

    def set_group(self, group_id, parameter, value=None, transitiontime=None):
        """ Change light settings for a group
        group_id : int, id number for group
        parameter : 'name' or 'lights'
        value: string, or list of light IDs if you're setting the lights
        """

        if isinstance(parameter, dict):
            data = parameter
        elif parameter == 'lights' and (isinstance(value, list) or isinstance(value, int)):
            if isinstance(value, int):
                value = [value]
            data = {parameter: [str(x) for x in value]}
        else:
            data = {parameter: value}

        if transitiontime is not None:
            # must be int for request format
            data['transitiontime'] = int(round(transitiontime))

        group_id_array = group_id
        if isinstance(group_id, int) or isinstance(group_id, str):
            group_id_array = [group_id]
        result = []
        for group in group_id_array:
            if isinstance(group, str):
                converted_group = self.get_group_id_by_name(group)
            else:
                converted_group = group
            if converted_group is False:
                # logger.error('Group name does not exit')
                return
            if parameter == 'name' or parameter == 'lights':
                result.append(self.request('PUT', '/api/' + self.bridge_user + '/groups/' + str(converted_group), data))
            else:
                result.append(self.request('PUT', '/api/' + self.bridge_user + '/groups/' +
                                           str(converted_group) + '/action', data))

        # if 'error' in list(result[-1][0].keys()):
            # logger.warn("ERROR: {0} for group {1}".format(result[-1][0]['error']['description'], group))
        return result

    def create_group(self, name, lights=None):
        """ Create a group of lights
        Parameters
        ------------
        name : string
            Name for this group of lights
        lights : list
            List of lights to be in the group.
        """
        data = {'lights': [str(x) for x in lights], 'name': name}
        return self.request('POST', '/api/' + self.bridge_user + '/groups/', data)

    def delete_group(self, group_id):
        return self.request('DELETE', '/api/' + self.bridge_user + '/groups/' + str(group_id))

    # Scenes #####
    def get_scene(self):
        return self.request('GET', '/api/' + self.bridge_user + '/scenes')

    def activate_scene(self, group_id, scene_id):
        return self.request('PUT', '/api/' + self.bridge_user + '/groups/' +
                            str(group_id) + '/action',
                            {"scene": scene_id})

    def run_scene(self, group_name, scene_name):
        """Run a scene by group and scene name.
        As of 1.11 of the Hue API the scenes are accessable in the
        API. With the gen 2 of the official HUE app everything is
        organized by room groups.
        This provides a convenience way of activating scenes by group
        name and scene name. If we find exactly 1 group and 1 scene
        with the matching names, we run them.
        If we find more than one we run the first scene who has
        exactly the same lights defined as the group. This is far from
        perfect, but is convenient for setting lights symbolically (and
        can be improved later).
        """
        groups = [x for x in self.groups if x.name == group_name]
        scenes = [x for x in self.scenes if x.name == scene_name]
        if len(groups) != 1:
            # logger.warn("run_scene: More than 1 group found by name %s", group_name)
            return
        group = groups[0]
        if len(scenes) == 0:
            # logger.warn("run_scene: No scene found %s", scene_name)
            return
        if len(scenes) == 1:
            self.activate_scene(group.group_id, scenes[0].scene_id)
            return True
        # otherwise, lets figure out if one of the named scenes uses
        # all the lights of the group
        group_lights = sorted([x.light_id for x in group.lights])
        for scene in scenes:
            if group_lights == scene.lights:
                self.activate_scene(group.group_id, scene.scene_id)
                return True

    # Schedules #####
    def get_schedule(self, schedule_id=None, parameter=None):
        if schedule_id is None:
            return self.request('GET', '/api/' + self.bridge_user + '/schedules')
        if parameter is None:
            return self.request('GET', '/api/' + self.bridge_user + '/schedules/' + str(schedule_id))

    def create_schedule(self, name, time, light_id, data, description=' '):
        schedule = {
            'name': name,
            'localtime': time,
            'description': description,
            'command':
            {
                'method': 'PUT',
                'address': ('/api/' + self.bridge_user +
                            '/lights/' + str(light_id) + '/state'),
                'body': data
            }
        }
        return self.request('POST', '/api/' + self.bridge_user + '/schedules', schedule)

    def create_group_schedule(self, name, time, group_id, data, description=' '):
        schedule = {
            'name': name,
            'localtime': time,
            'description': description,
            'command':
            {
                'method': 'PUT',
                'address': ('/api/' + self.bridge_user +
                            '/groups/' + str(group_id) + '/action'),
                'body': data
            }
        }
        return self.request('POST', '/api/' + self.bridge_user + '/schedules', schedule)

    def delete_schedule(self, schedule_id):
        return self.request('DELETE', '/api/' + self.bridge_user + '/schedules/' + str(schedule_id))


class Outlet(Device):
    device = models.OneToOneField(Device, parent_link=True, related_name='outlet_device')
    controller = models.ForeignKey("Portal.Device", related_name='get_outlet', null=True, blank=True)
    primary_controller = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.name


class HueException(Exception):

    def __init__(self, new_id, new_message):
        self.id = new_id
        self.message = new_message


class HueRegistrationException(HueException):
    pass
