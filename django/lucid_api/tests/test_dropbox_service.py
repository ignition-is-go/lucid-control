'''
tests for the dropbox service
'''

import pytest

from lucid_api.services.dropbox_service import Service

@pytest.fixture
def dropbox():
    return Service()

def test_sanitize_but_keep_url_slash(dropbox):
    '''
    test the dropbox sanitizer function to ensure it returns the correct format
    '''
    assert isinstance(dropbox, Service)
    initial = r'/root\fwd slash # folder/backslash%folder/one$with-issues.ext'
    result = dropbox._sanitize_path(initial)

    assert result=="/root/fwd-slash-folder/backslash-folder/one-with-issues.ext"

