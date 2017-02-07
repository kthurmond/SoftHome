import sys
sys.path.append('/var/www/modules')

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from .models import PhilipsHueBridge
from Portal.models import Device
from django.urls import reverse
import ssdp


def index(request):
    return HttpResponse("Received.")


def third_party_controllers(request):
    context = {}
    if 'delete' in request.POST:
        Device.objects.filter(request.POST['delete']).delete()
    controllers = Device.objects.filter(device_type="controller")
    context['controllers'] = controllers
    return render(request, 'MachineInterface/controller_list.html', context)


def new_controller_form(request, api='philips'):
    discovered = ssdp.discover('Philips Hue')
    ip_addresses = [ssdp.parse_ip_address(discovery.location) for discovery in discovered]
    context = {'api': api, 'ip_addresses': ip_addresses, 'error': 0}
    return render(request, 'MachineInterface/add_controller.html', context)


def add_controller(request, api='philips'):
    # process new_controller_form
    new_bridge = PhilipsHueBridge.register(ip_address=request.POST['ip_address'])
    if isinstance(new_bridge, PhilipsHueBridge):
        return HttpResponseRedirect(reverse('m2m:controller_list'))
    else:
        context = {'api': api, 'ip_address': list(request.POST['ip_address']), 'error': new_bridge}
        return render(request, 'MachineInterface/add_controller.html', context)


def manage_controller(request, device_id):
    device = Device.objects.filter(pk=device_id)[0]
    context = {'device': device}
    if device.api == 'philips':
            context.update(device.philips_device.import_all())
    return render(request, 'MachineInterface/view_controller.html', context)


def update_wifi_location(request, device, signal_strength, speed, gps_dd):
    return HttpResponse("Received.")


def sensor_list(request):
    return HttpResponse("Received.")


def add_sensor(request):
    return HttpResponse("Received.")


def update_sensor_state(request):
    return HttpResponse("Received.")
