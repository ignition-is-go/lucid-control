import os
from flask import Flask, request, render_template, make_response, jsonify
import requests
import simplejson as json
import datetime
import hashlib
import xml.etree.ElementTree as ET
import dropbox
import constants
from xero import Xero
from xero.auth import PrivateCredentials
import re
from threading import Thread
import logging
import sys

# derp-a-derp import. sorry python gods.
import lucid_api.lucid_api as lucid_api

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

# to fix buffered logging:
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

logger = logging.getLogger(__name__)
logger.setLevel(constants.LOG_LEVEL_TYPE)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) 



@app.route('/')
def hello():
    errors = []
    results = {}
    return "Welcome to Lucid"

@app.route('/lucid-create', methods=['POST'])
def lucid_create():
    '''This screens to confirm the trigger came from slack, then sends to lucid_api'''
    
    token = request.form.get('token')
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this didn't come from slack
        return (
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable in Heroku/LucidControl'
        )
    
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")
        
        command_text = request.form.get('text')
        channel_name = request.form.get('channel_name')
        callback_url = request.form.get('response_url')
        logger.debug("Preparing to thread lucid_api.create(%s)", command_text)
        t = Thread(target=lucid_api.create_from_slack, args=[request.form])
        t.start()
        logger.info("Lucid API Create Thread Away, returning 200 to Slack")

        # waiting_message = {'text': '...', 'response_type': 'ephemeral'}
        # return jsonify(waiting_message)
        return "", 200, {'ContentType':'application/json'}
    

@app.route('/lucid-rename', methods=['POST'])
def lucid_rename():
    '''This screens to confirm the trigger came from slack, then sends to lucid_api'''
    
    token = request.form.get('token')
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this didn't come from slack
        return (
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable in Heroku/LucidControl'
        )
    
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        command_text = request.form.get('text')
        channel_name = request.form.get('channel_name')
        logger.debug("Preparing to thread lucid_api.rename(%s, %s)", channel_name, command_text)
        t = Thread(target=lucid_api.rename_from_slack, args=[request.form]) 
        t.start()
        logger.info("Lucid API Rename Thread Away, returning 200 to Slack")
        waiting_message = {'text': 'Working to rename now...', 'response_type': 'ephemeral'}
        return jsonify(waiting_message)
        # return "", 200, {'ContentType':'application/json'}


@app.route('/lucid-archive', methods=['POST'])
def lucid_archive():
    '''This screens to confirm the trigger came from slack, then sends to lucid_api'''
    
    token = request.form.get('token')
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this didn't come from slack
        return (
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable in Heroku/LucidControl'
        )
    
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        channel_name = request.form.get('channel_name')
        print "Preparing to thread lucid_api.archive(%s)" % channel_name

        logger.debug("Preparing to thread lucid_api.archive(%s)", channel_name)
        t = Thread(target=lucid_api.archive_from_slack, args=[request.form]) 
        t.start()    
        
        logger.info("Lucid API Archive Thread Away, returning 200 to Slack")
        waiting_message = {'text': 'Working to archive now...', 'response_type': 'ephemeral'}
        return jsonify(waiting_message)
        # return "{", 200, {'ContentType':'application/json'}

@app.route("/lucid-action-response", methods=['POST'])
def lucid_action_handler():
    slack_data = json.loads(request.form.get('payload'))
    token = slack_data['token']
    if token is None:
        token = request.form.get("token")
    logger.info("Verification token sent=%s", token)

    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this didn't come from slack
        return (
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable in Heroku/LucidControl'
        )
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        if "challenge" in slack_data.keys():
            logger.info("Responding to challenge: %s", slack_data['challenge'])
            return slack_data['challenge']
        
        elif "callback_id" in slack_data.keys():
            logger.info("Routing Action: %s", slack_data['callback_id'])
            func_name = slack_data['callback_id']
            func = getattr(lucid_api, func_name)

            logger.debug("Preparing to thread %s for action:%s - %s", func_name, slack_data['channel']['name'],slack_data['actions'])
            t = Thread(target=func,args=[slack_data])
            t.start()
            logger.debug("Thread started!")
            return "", 200, {'ContentType':'application/json'}

            
@app.route("/lead", methods=['POST'])
def new_lead():
    '''This screens to confirm the trigger came from slack, then sends to lucid_api'''
    
    token = request.form.get('token')
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this didn't come from slack
        return (
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable in Heroku/LucidControl'
        )
    
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        channel_name = request.form.get('channel_name')

        logger.debug("Preparing to thread lucid_api.archive(%s)", channel_name)
        t = Thread(target=lucid_api.lead_create, args=[request.form]) 
        t.start()    
        
        logger.info("Lucid API lead_create Thread Away, returning 200 to Slack")
        waiting_message = {'text': 'Working on that lead...', 'response_type': 'ephemeral'}
        return jsonify(waiting_message)
        # return "{", 200, {'ContentType':'application/json'}

@app.route("/test")
def test():
    return "Test good"
    
if __name__ == '__main__':
    app.run()
