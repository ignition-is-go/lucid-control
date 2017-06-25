'''
This file makes env vars out of an env.json
'''

import simplejson as json
import os

#load env vars
with open("env.json") as fp:
    jstring = fp.read().decode('utf-16-le')
    envs = json.loads(jstring)
    for key, value in envs.items():
        os.environ[key] = value