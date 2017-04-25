import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = 'this-really-needs-to-be-changed'
    INTEGRATION_TOKEN = 'o8fI8r8rMfqgvgxLguStdsQg'
    INTEGRATION_TOKEN_RENAME = 'bx6xdqYRbKfMJlgBSU7U36el'
    INTEGRATION_TOKEN_STATE = 'tGtQScfIATvdJk249yMDcrK1'


class ProductionConfig(Config):
    DEBUG = False


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
