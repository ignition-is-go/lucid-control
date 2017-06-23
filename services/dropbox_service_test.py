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

def test_dropbox_create_slug(dropbox):
    assert isinstance(dropbox, dropbox_service.DropboxService)
    test_id = random.randint(1,9999)
    test_title = "Purple Cow"

    test_slug = dropbox._format_slug(test_id,test_title)
    test_project_code = dropbox._format_slug(test_id,"")

    expected_slug = "P-{}-Purple-Cow".format(test_id)
    assert test_slug == expected_slug
    assert test_project_code == "P-{}-".format(test_id)
