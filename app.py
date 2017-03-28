import os
from flask import Flask, request, render_template
import requests
import json
from slackclient import SlackClient
import datetime
import hashlib
import xml.etree.ElementTree as ET
import dropbox
import constants
from xero import Xero
from xero.auth import PrivateCredentials


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


def connect_to_xero():
    credentials = PrivateCredentials(constants.XERO_CONSUMER_KEY, constants.XERO_API_PRIVATE_KEY)
    xero = Xero(credentials)
    return xero


def create_xero_tracking_category(text):
    xero = connect_to_xero()
    response = xero.trackingcategories.put({'Name': text})
    return response


def connect_to_dropbox():
    dbx = dropbox.Dropbox(constants.DROPBOX_ACCESS_TOKEN)
    return dbx


def create_dropbox_folder(text):
    dbx = connect_to_dropbox()
    response = dbx.files_create_folder(os.path.join('/', text))
    return response


def move_mindmeister_map(folder_id, map_id):
    url = 'http://www.mindmeister.com/services/rest/'
    secret = os.environ['MINDMEISTER_SECRET']
    payload = {
        'api_key': os.environ['MINDMEISTER_API_KEY'],
        'auth_token': os.environ['MINDMEISTER_AUTH_TOKEN'],
        'folder_id': folder_id,
        'map_id': map_id,
        'method': 'mm.maps.move',
        'response_format': 'xml',
        }
    hash_string = '{}api_key{}auth_token{}folder_id{}map_id{}method{}response_format{}'.format(
        secret,
        os.environ['MINDMEISTER_API_KEY'],
        os.environ['MINDMEISTER_AUTH_TOKEN'],
        folder_id,
        map_id,
        'mm.maps.move',
        'xml'
    )
    print hash_string
    hash_object = hashlib.md5(bytes(hash_string))

    api_sig = hash_object.hexdigest()
    print api_sig
    payload['api_sig'] = api_sig

    # headers = {
    #     'content-type': 'application/xml'
    #
    # }
    response = requests.get(url, params=payload)
    print response.text
    # response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def create_mindmeister_map(text):
    url = 'http://www.mindmeister.com/services/rest/'
    secret = os.environ['MINDMEISTER_SECRET']
    payload = {
        'api_key': os.environ['MINDMEISTER_API_KEY'],
        'auth_token': os.environ['MINDMEISTER_AUTH_TOKEN'],
        'method': 'mm.maps.add',
        'response_format': 'xml'
        }
    hash_string = '{}api_key{}auth_token{}method{}response_format{}'.format(
        secret,
        os.environ['MINDMEISTER_API_KEY'],
        os.environ['MINDMEISTER_AUTH_TOKEN'],
        'mm.maps.add',
        'xml'
    )
    print hash_string
    hash_object = hashlib.md5(bytes(hash_string))

    api_sig = hash_object.hexdigest()
    print api_sig
    payload['api_sig'] = api_sig

    # headers = {
    #     'content-type': 'application/xml'
    #
    # }
    response = requests.get(url, params=payload)
    print response.text
    # response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def create_mindmeister_folder(text):
    url = 'http://www.mindmeister.com/services/rest/'
    secret = os.environ['MINDMEISTER_SECRET']
    payload = {
        'api_key': os.environ['MINDMEISTER_API_KEY'],
        'auth_token': os.environ['MINDMEISTER_AUTH_TOKEN'],
        'method': 'mm.folders.add',
        'name': text,
        'response_format': 'xml',
        }
    hash_string = '{}api_key{}auth_token{}method{}name{}response_format{}'.format(
        secret,
        os.environ['MINDMEISTER_API_KEY'],
        os.environ['MINDMEISTER_AUTH_TOKEN'],
        'mm.folders.add',
        text,
        'xml'
    )
    print hash_string
    hash_object = hashlib.md5(bytes(hash_string))

    api_sig = hash_object.hexdigest()
    print api_sig
    payload['api_sig'] = api_sig

    # headers = {
    #     'content-type': 'application/xml'
    #
    # }
    response = requests.get(url, params=payload)
    print response.text
    # response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response

def rename_meistertask_project(text, name):
    url = 'https://www.meistertask.com/api/projects'

    headers = {
        'content-type': 'application/json',
        'authorization': 'Bearer {}'.format(os.environ['MEISTERTASK_API_TOKEN'])
    }
    response = requests.get(url, headers=headers)
    result = json.loads(response)
    project_id = None
    for item in result:
        if item['name'] == name:
            project_id = item['id']
    payload = {
        'name': text
    }
    url += '/' + project_id + '/'
    response = requests.get(url, data=json.dumps(payload), headers=headers)
    return response

def create_meistertask_project(text):
    url = 'https://www.meistertask.com/api/projects'
    payload = {
        'name': text
    }
    headers = {
        'content-type': 'application/json',
        'authorization': 'Bearer {}'.format(os.environ['MEISTERTASK_API_TOKEN'])
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response

def rename_airtable_entry(text, name):
    url = 'https://api.airtable.com/v0/appSGiFYbSDPJBM3k/Imported%20Table?filterByFormula={Title}="' + name + '"'

    headers = {
        'content-type': 'application/json',
        'authorization': 'Bearer {}'.format(os.environ['AIRTABLE_API_TOKEN'])
    }
    response = requests.get(url, headers=headers)
    result = json.loads(response.content)
    entry_id = None
    if result['records']:
        entry_id = result['records'][0]['id']
        url = 'https://api.airtable.com/v0/appSGiFYbSDPJBM3k/Imported%20Table/' + entry_id
        payload = {
            "fields": {
                "Abbreviated Title": text
            }
        }
        response = requests.patch(url, data=json.dumps(payload), headers=headers)
    return response


def create_airtable_entry(text):
    date_now = datetime.datetime.now().strftime("%Y-%m-%d")
    url = 'https://api.airtable.com/v0/appSGiFYbSDPJBM3k/Imported%20Table'
    payload = {
        "fields": {
            "Unique ID": "P-1111",
            "Created on": date_now,
            "Summary": "Coming soon...",
            "Title": text,
            "Slack Channel": 'https://lucidslack.slack.com/messages/{}'.format(
                text
            )
        }
    }
    headers = {
        'content-type': 'application/json',
        'authorization': 'Bearer {}'.format(os.environ['AIRTABLE_API_TOKEN'])
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response

def rename_slack_channel(text, token, channel_id):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    output = sc.api_call(
        "channels.rename",
        channel=channel_id,
        name=text
    )
    return output


def create_slack_channel(text, token):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    # url = 'https://slack.com/api/channels.create'

    output = sc.api_call(
        "channels.create",
        name=text
    )
    return output


@app.route('/')
def hello():
    errors = []
    results = {}
    return render_template('index.html', errors=errors, results=results)


@app.route('/rename', methods=['GET', 'POST'])
def rename():
    results = {'msg': ''}
    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')
        channel_name = request.form.get('channel_name')
        channel_id = request.form.get('channel_id')
        if token != app.config['INTEGRATION_TOKEN_RENAME']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Renamed {} to: {}'.format(channel_name, text)
            )
        results['msg'] = message
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
        slack_response = rename_slack_channel(text, token, channel_id)
        print 'Rename channel returns: {}'.format(slack_response)
        airtable_response = rename_airtable_entry(text, channel_name)
        print 'Rename airtable entry returns: {}'.format(airtable_response)
        meistertask_response = rename_meistertask_project(text)
        print 'Rename meistertask project returns: {}'.format(meistertask_response)
        mindmeister_response = rename_mindmeister_folder(text)
        print 'Rename mindmeister folder returns: {}'.format(mindmeister_response)
        root = ET.fromstring(mindmeister_response.content)
        folder_id = root[0].attrib['id']
        mindmeister_response2 = rename_mindmeister_map(text)
        print 'Rename mindmeister map returns: {}'.format(mindmeister_response2)
        root = ET.fromstring(mindmeister_response2.content)
        map_id = root[0].attrib['id']
        mindmeister_response3 = move_mindmeister_map(folder_id, map_id)
        print 'Move mindmeister map returns: {}'.format(mindmeister_response3)
        rename_dropbox_folder_response = rename_dropbox_folder(text)
        print 'Rename dropbox folder returns: {}'.format(rename_dropbox_folder_response)
        xero_trackingcategory_response = rename_xero_tracking_category(text)
        print 'Rename xero tracking category returns: {}'.format(xero_trackingcategory_response)


    return results['msg']

@app.route('/create', methods=['GET', 'POST'])
def create():
    results = {'msg': ''}
    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')
        if token != app.config['INTEGRATION_TOKEN']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Created New Project: {}'.format(text)
            )
        results['msg'] = message
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
        slack_response = create_slack_channel(text, token)
        print 'Create channel returns: {}'.format(slack_response)
        airtable_response = create_airtable_entry(text)
        print 'Create airtable entry returns: {}'.format(airtable_response)
        meistertask_response = create_meistertask_project(text)
        print 'Create meistertask project returns: {}'.format(meistertask_response)
        mindmeister_response = create_mindmeister_folder(text)
        print 'Create mindmeister folder returns: {}'.format(mindmeister_response)
        root = ET.fromstring(mindmeister_response.content)
        folder_id = root[0].attrib['id']
        mindmeister_response2 = create_mindmeister_map(text)
        print 'Create mindmeister map returns: {}'.format(mindmeister_response2)
        root = ET.fromstring(mindmeister_response2.content)
        map_id = root[0].attrib['id']
        mindmeister_response3 = move_mindmeister_map(folder_id, map_id)
        print 'Move mindmeister map returns: {}'.format(mindmeister_response3)
        create_dropbox_folder_response = create_dropbox_folder(text)
        print 'Crete dropbox folder returns: {}'.format(create_dropbox_folder_response)
        xero_trackingcategory_response = create_xero_tracking_category(text)
        print 'Create xero tracking category returns: {}'.format(xero_trackingcategory_response)

    return results['msg']

if __name__ == '__main__':
    app.run()
