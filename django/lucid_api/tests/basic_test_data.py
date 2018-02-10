'''
Basic Test Data
Handles generic test data

K Bjordahl
6/21/17
'''

import pytest
import make_envs


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

    project['project_id'] = random.randint(1000, 9999)
    project['project_title'] = "{} {}".format(
        random_names.random_nick(gender='f').capitalize(),
        random_words.random_word().capitalize()
        )
    
    return project