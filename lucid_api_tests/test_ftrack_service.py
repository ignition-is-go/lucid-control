'''
Ftrack service tests

'''

from basic_test_data import sample_project_data
import os, random
import pytest
import ftrack_api
import simplejson as json
from lucid_api.services.ftrack_service import FtrackService



#load env vars
with open("env.json") as fp:
    jstring = fp.read().decode('utf-16-le')
    envs = json.loads(jstring)
    for key, value in envs.items():
        os.environ[key] = value

def test_env_variables():
    '''
    test to make sure we're importing env vars
    '''
    assert os.environ.get('FTRACK_SERVER') == "https://lucid.ftrackapp.com"


@pytest.fixture(scope='session')
def ftrack():
    '''
    creates a testing ftrack service instance
    '''

    return FtrackService()

@pytest.fixture(scope='function')
def local_ftrack():
    local = ftrack_api.Session()
    return local


@pytest.fixture(scope='module')
def sample_project_with_teardown(request, sample_project_data):
    '''
    creates test project for use
    '''
    project_id = str(sample_project_data['project_id'])
    project_title = sample_project_data['project_title']

    def fin():
        '''
        Cleanup any project created by this
        '''
        print('Cleaning up after {}!'.format(project_title))
        local_ftrack = ftrack_api.Session()
        project = local_ftrack.query(
            'Project where name is "{id}"'.format(
                id=project_id
            )).one()

        if project['name'] == project_id:
            local_ftrack.delete(project)
            local_ftrack.commit()
        else:
            print("Couldn't find project ({}) {} to delete".format(
                project_id, project_title
            ))


    request.addfinalizer(fin)
    return {'project_id': project_id, 'title': project_title}



@pytest.fixture(scope='module')
def sample_project_with_setup_and_teardown(ftrack, sample_project_with_teardown):
    ftrack.create(
        sample_project_with_teardown['project_id'],
        sample_project_with_teardown['title']
    )
    return sample_project_with_teardown

def test_connection(ftrack):
    '''
    tests to confirm that the ftrackService object connects
    '''
    assert ftrack.is_connected()

def test_create_project(ftrack, local_ftrack, sample_project_with_teardown):
    '''
    tests the project creation process
    '''
    
    ftrack.create(
        sample_project_with_teardown['project_id'], 
        sample_project_with_teardown['title'])

    # now we go look in ftrack for it

    try:
        project = local_ftrack.query('Project where name is "{id}"'.format(
            id=sample_project_with_teardown['project_id'],
            )).one()
    except:
        assert 0

    slug = ftrack._format_slug(
        sample_project_with_teardown['project_id'], 
        sample_project_with_teardown['title']
    )
    assert project['name'] == sample_project_with_teardown['project_id']
    assert project['full_name'] == slug

def test_rename_project(ftrack, local_ftrack, sample_project_with_setup_and_teardown):
    '''
    Tests the rename function
    '''
    project = sample_project_with_setup_and_teardown
    rename_title = project['title']+"-RENAME"

    assert ftrack.rename(project['project_id'], rename_title) is True

    renamed_project = local_ftrack.query('Project where name is "{id}"'.format(
        id=project['project_id']
        )).one()

    slug = ftrack._format_slug(
        project['project_id'], 
        rename_title
    )
    assert renamed_project['name'] == project['project_id']
    assert renamed_project['full_name'] == slug

def test_archive_project(ftrack, local_ftrack, sample_project_with_teardown):
    '''
    Test the archive function
    '''

    assert ftrack.archive(sample_project_with_teardown['project_id']) is True

    project = local_ftrack.query('Project where name is "{id}"'.format(
        id=sample_project_with_teardown['project_id']
        )).one()


    assert project['status'] == 'hidden'

    assert ftrack.archive(sample_project_with_teardown['project_id'], unarchive=True)

def test_get_link(ftrack,sample_project_with_teardown):
    '''
    Test getting a url
    '''
    url = ftrack.get_link(sample_project_with_teardown['project_id'])
    print url

    assert isinstance(url, str)

# EOF