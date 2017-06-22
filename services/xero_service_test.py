'''
Xero Service Tests

tests for the Xero Service connector on Lucid Control (Lucid API)

K Bjordahl
6/20/17
'''

import basic_test_data
from basic_test_data import sample_project_data
import pytest
import simplejson as json
import os
from basic_test_data import sample_project_data

from services.xero_service import XeroService, XeroServiceError


@pytest.fixture(scope='session')
def xero(request):
    '''
    Build a Xero Service for tests
    '''
    return XeroService()

@pytest.fixture(scope='module')
def sample_project(request, sample_project_data, xero):

    assert xero.create(
        sample_project_data['project_id'],
        sample_project_data['project_title']
        )

    def fin():
        try:
            xero.archive(sample_project_data['project_id'])
        except:
            #something happened?
            pass

    request.addfinalizer(fin)

    return sample_project_data

def test_xero_prevent_duplicate_create(xero, sample_project):
    with pytest.raises(XeroServiceError):
        xero.create(
            sample_project['project_id'],
            sample_project['project_title']
            )

def test_xero_rename(xero, sample_project):
    assert xero.rename(
        sample_project['project_id'],
        sample_project['project_title'] + "-RENAME"
        )

def test_xero_archive(xero, sample_project):
    assert xero.archive(
        sample_project['project_id'],
        )
