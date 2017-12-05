from django.conf.urls import url

from . import views

app_name = "slack_commands"
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^slack/create/$', views.create, name="Slack Create"),
    url(r'^slack/rename/$', views.create, name="Slack Rename"),
    url(r'^slack/archive/$', views.archive, name="Slack Archive"),
    url(r'^slack/action-response/$', views.action_response,
        name="Slack Action Response")
]
