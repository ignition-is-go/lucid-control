from django.conf.urls import url

from . import views

app_name = "slack_commands"
urlpatterns = [
    url(
        r'^slack/action-response/$', 
        views.action_response,
        name="Slack Action Response"
    ),
    url(
        r'^slack/<str:command>/$', 
        views.slash_command, 
        name="Slack Command"
    ),
]
