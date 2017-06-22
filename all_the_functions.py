import os
from flask import Flask, request, render_template, make_response
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
import re
from threading import Thread
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def format_slug(project_id, text):
    '''
    Handles the formatting to create a slug from a project_id number and text
    @param project_id: the project's id number
    @param text: the project's short title
    @returns the formatted slug
    '''

    #removed lower case on slug text (only necessary for slack)
    dashed_text = text.replace(' ', '-')
    slug = ''.join(e for e in dashed_text if e.isalnum or e == '-')
    print 'slug: {}'.format(slug)
    print 'project_id: {}'.format(project_id)
    slug = 'P-{}-{}'.format("%04d" % int(project_id), slug)
    return slug


def archive_project(channel_id, text, slug, project_id):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    url = '{}{}/?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], project_id, os.environ['API_USERNAME'], os.environ['API_KEY'])
    payload = {
        'production_state': 'archived',
        'sales_state': 'changes complete',
        'invoice_state': 'closed'
    }
    r = requests.put(url, data=json.dumps(payload), headers=headers)
    print r
    print r.content
    return r


def rename_project(channel_id, text, slug, project_id):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    url = '{}{}/?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], project_id, os.environ['API_USERNAME'], os.environ['API_KEY'])
    payload = {
        'title': text,
        'slug': slug
    }
    r = requests.put(url, data=json.dumps(payload), headers=headers)
    print r
    print r.content
    return r


def create_project_entry(text, slug, channel_id):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    url = '{}?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY'])
    payload = {
        'title': text,
        'slug': slug,
        'slack_channel': channel_id

    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    print r
    print r.content
    return r


def get_project_id_from_channel(channel_id):
    response = requests.get('{}?format=json&username={}&api_key={}&slack_channel={}'.format(os.environ['PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY'], channel_id))
    project_id = response.json()['objects'][0]['id']
    return project_id

def get_last_project_id():
    response = requests.get('{}?format=json&username={}&api_key={}'.format(os.environ['LAST_PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY']))
    last_project_id = response.json()['objects'][0]['id']
    return last_project_id


def create_slug(text):
    '''
    Used to create a slug for a new project
    @params text: the short title of the project
    @returns the slug for the project
    '''
    next_project_id = get_last_project_id() + 1
    slug = format_slug(next_project_id, text)
    return slug


# service done
def connect_to_xero():
    credentials = PrivateCredentials(constants.XERO_CONSUMER_KEY, constants.XERO_API_PRIVATE_KEY)
    xero = Xero(credentials)
    return xero



# service done
def create_xero_tracking_category(text):
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    response = xero.TCShow.options.put({'Name': text.lower()})
    return response


# service done
def get_xero_tracking_id(text):
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    option_id = None
    for option in xero.TCShow.options.all():
        print 'text: {}'.format(text)
        print 'option: {}'.format(option)
        print 'option name: {}'.format(option['Name'])
        if option['Name'] == text:
            print 'match'
            option_id = option['TrackingOptionID']
        else:
            print 'no match'
    return option_id


# service done
def archive_xero_tracking_category(name, project_id, text):
    print 'name: {}'.format(name)
    print 'project_id: {}'.format(project_id)
    print 'text: {}'.format(text)
    print 'format_slug: {}'.format(format_slug(project_id, name).lower())
    tracking_id = get_xero_tracking_id(format_slug(project_id, name).lower())
    print 'tracking_id: {}'.format(tracking_id)
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    option = xero.TCShow.options.get(tracking_id)[0]

    option['IsArchived'] = True
    response = xero.TCShow.options.delete(option['TrackingOptionID'])
    # response = xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'IsArchived': option['IsArchived']})
    return response


# service done
def rename_xero_tracking_category(name, project_id, text):
    print 'name: {}'.format(name)
    print 'project_id: {}'.format(project_id)
    print 'text: {}'.format(text)
    print 'format_slug: {}'.format(format_slug(project_id, name).lower())
    tracking_id = get_xero_tracking_id(format_slug(project_id, name).lower())
    print 'tracking_id: {}'.format(tracking_id)
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    option = xero.TCShow.options.get(tracking_id)[0]
    print 'option: {}'.format(option)
    option['Name'] = text.lower()
    response = xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'Name': option['Name']})
    return response


def connect_to_dropbox():
    dbx = dropbox.Dropbox(constants.DROPBOX_ACCESS_TOKEN)
    return dbx


def create_dropbox_folder(text):
    dbx = connect_to_dropbox()
    print "dropbox_folder_schema: {}".format(os.environ['DROPBOX_FOLDER_SCHEMA'])
    dfs = os.environ['DROPBOX_FOLDER_SCHEMA']
    print dfs
    print type(dfs)
    dfs = dfs.strip()
    schema = json.loads(dfs)
    print "schema: {}".format(schema)
    for folder in schema['folders']:
        print 'folder: {}'.format(folder)
        print 'attempting to make: {}'.format(os.path.join(folder['root'], text))
        response = dbx.files_create_folder(os.path.join(folder['root'], text))
        print response
        for subfolder in folder['subfolders']:
            print 'subfolder: {}'.format(subfolder)
            print 'attempting to make: {}'.format(os.path.join(folder['root'], text, subfolder))
            response = dbx.files_create_folder(os.path.join(folder['root'], text, subfolder))
            print response
    return response


def archive_dropbox_folder(channel_name, project_id, text):
    dbx = connect_to_dropbox()
    schema = json.loads(os.environ['DROPBOX_FOLDER_SCHEMA'])
    for folder in schema['folders']:
        print 'from: {}'.format(format_slug(project_id, channel_name))
        print 'text: {}'.format(text)
        print 'to: {}'.format(text)
        response = dbx.files_move(os.path.join(folder['root'], format_slug(project_id, channel_name)), os.path.join(folder['root'], 'Archive', format_slug(project_id, channel_name)))
        print response
    return response


def find_dropbox_folder(project_id):
    dbx = connect_to_dropbox()
    schema = json.loads(os.environ['DROPBOX_FOLDER_SCHEMA'])
    matches = []
    print 'Finding dropbox folders starting with: {}'.format(project_id)
    for folder in schema['folders']:
        for f in dbx.files_list_folder(folder['root']).entries:
            if f.name.startswith(str(project_id)):
                print "match:"
                print f.path_lower
                matches.append(f.path_lower)
    return matches


def rename_dropbox_folder(channel_name, project_id, text):
    folder_prefix = format_slug(project_id, '')
    matches = find_dropbox_folder(folder_prefix)
    dbx = connect_to_dropbox()
    response = 'Folder not found'
    for path in matches:
        print 'from: {}'.format(path)
        print 'text: {}'.format(text)
        print 'to: {}'.format(path.rsplit('/', 1)[0] + '/' + text)
        response = dbx.files_move(path, os.path.join(path.rsplit('/', 1)[0], text))
        print response
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
    result = json.loads(response.content)
    project_id = None
    for item in result:
        print item
        print name
        if item['name'] == name:
            project_id = item['id']
    payload = {
        'name': text
    }
    url += '/' + str(project_id) + '/'
    response = requests.get(url, params=payload, headers=headers)
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
        print result['records']
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


def archive_slack_channel(text, token, channel_id):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    output = sc.api_call(
        "channels.archive",
        channel=channel_id
    )
    return output


def rename_slack_channel(text, token, channel_id):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)
    if text.lower()[0:2] == "p-":
        text = text.lower()
        text = re.sub('p-0*', "", text, 1)
    output = sc.api_call(
        "channels.rename",
        channel=channel_id,
        name=text
    )
    return output


def send_slack_state_menu(channel_id, results):
    slack_token = os.environ['SLACK_APP_API_TOKEN']
    sc = SlackClient(slack_token)

    output = sc.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=results['text'],
        as_user="false",
        response_type="ephemeral",
        attachments=results['attachments']

    )
    print output
    return output

def create_slack_message(channel_id, text):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    # url = 'https://slack.com/api/channels.create'

    output = sc.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=text
    )

    return output


def create_slack_pin(slug, channel_id):
    project_id = slug.split('-')[1]
    url = '{}{}/change/'.format(os.environ['PROJECT_EDIT_BASE_URL'], project_id)
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    # url = 'https://slack.com/api/channels.create'
    message = create_slack_message(channel_id, url)
    ts = message['ts']
    output = sc.api_call(
        "pins.add",
        channel=channel_id,
        timestamp=ts
    )

    return output


def create_slack_channel(text):
    '''
    Creates a slack channel
    '''
    #check to see if there's 'P-00..' on the front of text, and remove it
    if text.lower()[0:2] == "p-":
        text = text.lower()
        text = re.sub('p-0*',"",text,1)

    #get rid of any dangling - from the slack character cutoff (21 chars)
    if len(text) > 21:
        text = text[0:21]
        if text[-1:] == "-":
            text = text[0:-1]
    slack_token = os.environ["SLACK_API_TOKEN"]
    bot_user = os.environ["SLACK_APP_BOT_USERID"]
    sc = SlackClient(slack_token)

    # using 'channels.join' will force the calling user to create and join
    # url = 'https://slack.com/api/channels.join'

    output = sc.api_call(
        "channels.join",
        name=text
    )

    # i'm sneaking this in here to add the bot user to the channel
    add_bot_output = sc.api_call(
        'channels.invite',
        user=bot_user,
        channel=output.get('id')
    )

    return output


def post_create_results(results, channel_id):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    output = sc.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=results
    )
    return output




def invite_slack_channel( channel_id, token ):
    '''
    updates the channel list for the slack UserGroup set in the config vars
    this automatically adds the entire group to the channel
    '''

    try:
        slack_token = os.environ["SLACK_APP_API_TOKEN"]
        invite_group = os.environ["SLACK_INVITE_USERGROUP"]
        sc = SlackClient(slack_token)

        # turns out we didn't need to get the group list and update it, just call update with the channel id and it adds everyone

        print "trying to update: usergroup='{}', channels='{}'".format(invite_group, channel_id)

        output = sc.api_call(
            "usergroups.update",
            usergroup = invite_group,
            channels = channel_id
        )

        return output

    except Exception as e:
        raise e