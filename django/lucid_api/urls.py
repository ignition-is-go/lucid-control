from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views


urlpatterns = [
    url(r'^$', views.api_root, name="root"),
    url(r'^projects/$', views.ProjectList.as_view(), name="project_list"),
    url(r'^projects/(?P<pk>[0-9]+)$', views.ProjectDetail.as_view(), name="project_detail"),
    # Slack command handlers
    url(
        r'^slack/action-response/$', 
        views.action_response,
        name="Slack Action Response"
    ),
    url(
        r'^slack/(?P<command>[a-z]+)/$', 
        views.slash_command, 
        name="Slack Command"
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)