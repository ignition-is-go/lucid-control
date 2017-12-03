from django.conf.urls import url

from . import views, slack_handler

app_name = "lucid_api"
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^slack/create/$', slack_handler.create, name="Slack Create"),
    url(r'^slack/rename/$', slack_handler.create, name="Slack Rename"),
    url(r'^slack/archive/$', slack_handler.archive, name="Slack Archive"),
    url(r'^slack/action-response/$', slack_handler.action_response,
        name="Slack Action Response")

]