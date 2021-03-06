from django.conf.urls import url
from . import views


urlpatterns = [
    url(
        r'^action-response/$', 
        views.action_response,
        name="Slack Action Response"
    ),
    url(
        r'^roll-call/$',
        views.roll_call,
        name="Slack Roll Call"
    ),
    url(
        r'^nag/(?P<user>[a-z]+)/',
        views.test,
        name="Nag Test"
    )
]