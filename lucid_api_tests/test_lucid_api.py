'''
Lucid API Tests
tests for the combined usage of the Service connectors on Lucid Control (Lucid API)

K Bjordahl
6/20/17
'''

import basic_test_data
from basic_test_data import sample_project_data
from test_slack_service import slack
from test_ftrack_service import ftrack
from test_xero_service import xero
from test_dropbox_service import dropbox
import pytest
import simplejson as json
import os

import lucid_api

cleanup_ids = []

@pytest.fixture(scope='module')
def sample_project(request, sample_project_data):
    yield sample_project_data

    #need to archive here!
    cleanup_ids = getattr(request.module, 'cleanup_ids', [])
    print cleanup_ids
    for id in cleanup_ids:
        lucid_api.archive(id)

@pytest.fixture(scope='module')
def sample_project_with_setup_and_teardown(request, sample_project_data):
    project = sample_project_data
    project_id = lucid_api.create(project['project_title'], silent=True)
    sample_project_data['project_id'] = project_id
    yield sample_project_data

    #need to archive here!
    lucid_api.archive(project_id)

def test_create_with_teardown( sample_project, slack, ftrack, xero ):

    title = sample_project['project_title']
    project_id = lucid_api.create(title, silent=True)
    
    try:
        assert slack._find(project_id)['name'] == slack._format_slug(project_id, title)
        assert xero._find(project_id)['Name'] == xero._format_slug(project_id, title)
        assert ftrack._find(project_id)['full_name'] == ftrack._format_slug(project_id, title)
        # need to test dropbox
    finally:
        assert lucid_api.archive(project_id)

def test_rename(sample_project_with_setup_and_teardown, slack, ftrack, xero):
    project = sample_project_with_setup_and_teardown
    project['rename_title'] = project['project_title'] + "-RENAME"

    rename_success = lucid_api.rename(project['project_id'], project['rename_title'])

    assert rename_success

def test_direct_archive():

    project_id = 118
    tests = lucid_api.archive(project_id, return_individual = True)

    assert len(tests['failtures'].items()) == 0

def test_do_links():

    lucid_api.do_project_links(118,create=False)