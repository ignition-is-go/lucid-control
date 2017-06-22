'''
Basic Test Data
Handles generic test data

K Bjordahl
6/21/17
'''

import pytest
import simplejson as json
import os

#load env vars
with open("env.json") as fp:
    jstring = fp.read().decode('utf-16-le')
    envs = json.loads(jstring)
    for key, value in envs.items():
        os.environ[key] = value


@pytest.fixture(scope='session')
def sample_project_data():
    '''
    Generates a sample project
    '''
    import random
    from random_words import RandomNicknames, RandomWords

    random_names = RandomNicknames()
    random_words = RandomWords()

    project = {}

    project['project_id'] = random.randint(1, 9999)
    project['project_title'] = "{} {}".format(
        random_names.random_nick(gender='f').capitalize(),
        random_words.random_word().capitalize()
        )
    
    return project