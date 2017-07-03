'''
Slack Service Tests

tests for the slack Service connector on Lucid Control (Lucid API)

K Bjordahl
6/20/17
'''

import basic_test_data
from basic_test_data import sample_project_data
import pytest
import simplejson as json
import os
from lucid_api.services.slack_service import SlackService, SlackServiceError


@pytest.fixture(scope='session')
def slack(request):
    '''
    Build a Slack Service for tests
    '''
    return SlackService()

@pytest.fixture(scope='module')
def sample_project(request, sample_project_data, slack):
    '''Gets a sample project, but then erases it'''
    yield sample_project_data

    try:
        slack.archive(sample_project_data['project_id'])
    except:
        assert 0
        pass


@pytest.fixture(scope='module')
def prebuilt_sample_project(request, sample_project, slack):
    '''builds a sample project, not inviting people to keep from being annoying'''
    assert slack.create(
            sample_project['project_id'],
            sample_project['project_title'],
            silent=False)    
    yield sample_project


def test_slack_prevent_duplicate_create(slack, prebuilt_sample_project):
    
    with pytest.raises(SlackServiceError):
        slack.create(
            prebuilt_sample_project['project_id'],
            prebuilt_sample_project['project_title']
            )


def test_slack_rename(slack, prebuilt_sample_project):
    assert slack.rename(
        prebuilt_sample_project['project_id'],
        "-RENAME"
        )

def test_slack_post_basic(slack,prebuilt_sample_project):
    text = "Basic test post to {}".format(prebuilt_sample_project['project_title'])
    assert slack.post_to_project(
        prebuilt_sample_project['project_id'],
        text
    )

def test_find_channel_by_id(slack, prebuilt_sample_project):
    assert isinstance(slack, SlackService)
    project = prebuilt_sample_project
    channel = slack._find(str(project['project_id']))
    assert channel['name'] == slack._format_slug(
        project['project_id'], project['project_title'])
    

def test_get_id_by_channel_name(slack):
    assert isinstance(slack, SlackService)
    channel_name = "122-purple_potato"
    result_id = slack.get_project_id(slack_channel_name=channel_name)
    print result_id
    assert result_id == 122


def test_slack_archive(slack, prebuilt_sample_project):
    assert slack.archive(
        prebuilt_sample_project['project_id'],
        )

def test_webhook(slack):
    assert isinstance(slack, SlackService)

    url= 'https://hooks.slack.com/services/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'
    print slack.respond_to_url(url, "Hook test", ephemeral=True)

    assert 0