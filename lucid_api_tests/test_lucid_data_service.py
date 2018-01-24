'''
Lucid data service tests

K Bjordahl 6/25/17
'''

import basic_test_data
from basic_test_data import sample_project_data
from lucid_api.services import lucid_data_service
import requests
import pytest

@pytest.fixture(scope='function')
def lucid_data():
    yield lucid_data_service.LucidDataService()

def test_create_project(sample_project_data, lucid_data):
    assert isinstance(lucid_data, lucid_data_service.LucidDataService)
    project = sample_project_data

    response = lucid_data.create(project['project_title'])
    
    assert 0