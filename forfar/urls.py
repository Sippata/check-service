from django.conf.urls import url

from .views import create_checks, get_check_pdf, get_new_checks


app_name = 'forfar'
urlpatterns = [
    url(r'^create_checks/$', create_checks, name='create_checks'),
    url(r'^new_checks/(?P<api_key>\w+)/$', get_new_checks, name='new_checks'),
    url(r'^check/(?P<api_key>\w+)/(?P<check_id>\d+)/$', get_check_pdf, name='check'),
]
