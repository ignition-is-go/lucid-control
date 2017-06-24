'''
dropbox service tests
'''

import basic_test_data
from basic_test_data import sample_project_data
import dropbox_service
import os
import pytest
import random
from dropbox import Dropbox


@pytest.fixture(scope='session')
def dropbox():
    return dropbox_service.DropboxService()

@pytest.fixture(scope='module')
def sample_project_with_teardown(dropbox, sample_project_data): 
    yield sample_project_data

    project_id = sample_project_data['project_id']
    title = sample_project_data['project_title']
    schema = dropbox._find_schema(project_id, title=title) 
    for s in schema['folders']:
        for f in s['matches']:
            dropbox._dbx.files_delete(f.path_lower)

@pytest.fixture(scope='module')
def sample_project_with_setup_and_teardown(dropbox, sample_project_with_teardown): 
    dropbox.create(
        sample_project_with_teardown['project_id'],
        sample_project_with_teardown['project_title']
    )
    return sample_project_with_teardown

def test_dropbox_create_slug(dropbox):
    assert isinstance(dropbox, dropbox_service.DropboxService)
    test_id = random.randint(1,9999)
    test_title = "Purple Cow"

    test_slug = dropbox._format_slug(test_id,test_title)
    test_project_code = dropbox._format_slug(test_id,"")

    expected_slug = "P-{}-purple-cow".format(test_id)
    assert test_slug == expected_slug
    assert test_project_code == "P-{}-".format(test_id)

def test_dropbox_create(dropbox, sample_project_with_teardown):
    project = sample_project_with_teardown

    assert dropbox.create(
        project['project_id'],
        project['project_title']
    )

    
def test_dropbox_rename(dropbox, sample_project_with_setup_and_teardown):
    project = sample_project_with_setup_and_teardown
    rename = project['project_title'] + "-RENAME"

    assert dropbox.rename(
        project['project_id'],
        rename     
        )

    check = dropbox._find_schema(project['project_id'])

def test_dropbox_links(dropbox):

    links = dropbox.get_link_dict(118)

    print links
    assert 0
    
