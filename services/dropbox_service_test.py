'''
dropbox service tests
'''

import basic_test_data
from basic_test_data import sample_project_data
import dropbox_service
import os
import pytest
import random


@pytest.fixture(scope='session')
def dropbox():
    return dropbox_service.DropboxService()

@pytest.fixture(scope='module')
def sample_project_with_teardown(dropbox, sample_project_data): 
    yield sample_project_data
    try:
        dropbox.archive(sample_project_data['project_id'])
    except dropbox_service.DropboxServiceError:
        print "Already archived {}".format(sample_project_data['project_id'])

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
    assert dropbox.create(
        sample_project_with_teardown['project_id'],
        sample_project_with_teardown['project_title']
    )

    result_search = dropbox._find(sample_project_with_teardown['project_id'])
    schema = dropbox._get_schema()

    assert len(result_search) == len(schema['files'])