from django.conf.urls import url
from . import views


app_name = 'm2m'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'controllers/$', views.third_party_controllers, name='controller_list'),
    url(r'controllers/new/(?P<api>[\w-]+)/$', views.new_controller_form, name='new_controller_form'),
    url(r'controllers/add/(?P<api>[\w-]+)/$', views.add_controller, name='add_controller'),
    url(r'controllers/update/(?P<device_id>[0-9]+)/$', views.manage_controller, name='update_controller'),
    url(r'controllers/view/(?P<device_id>[0-9]+)/$', views.manage_controller, name='manage_controller')
]
