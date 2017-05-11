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


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


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
    url = 'http://lucid-pro.herokuapp.com/api/project/{}/?username=admin&api_key=LucyT3st'.format(project_id)
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
    url = 'http://lucid-pro.herokuapp.com/api/project/{}/?username=admin&api_key=LucyT3st'.format(project_id)
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
    url = 'http://lucid-pro.herokuapp.com/api/project/?username=admin&api_key=LucyT3st'
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
    response = requests.get('http://lucid-pro.herokuapp.com/api/project/?format=json&username=admin&api_key=LucyT3st&slack_channel={}'.format(channel_id))
    project_id = response.json()['objects'][0]['id']
    return project_id

def get_last_project_id():
    response = requests.get('http://lucid-pro.herokuapp.com/api/lastproject/?format=json&username=admin&api_key=LucyT3st')
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


def connect_to_xero():
    credentials = PrivateCredentials(constants.XERO_CONSUMER_KEY, constants.XERO_API_PRIVATE_KEY)
    xero = Xero(credentials)
    return xero


def create_xero_tracking_category(text):
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    response = xero.TCShow.options.put({'Name': text.lower()})
    return response


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


def archive_xero_tracking_category(name, project_id, text):
    print 'name: {}'.format(name)
    print 'project_id: {}'.format(project_id)
    print 'text: {}'.format(text)
    print 'format_slug: {}'.format(format_slug(project_id, name).lower())
    tracking_id = get_xero_tracking_id(format_slug(project_id, name).lower())
    print 'tracking_id: {}'.format(tracking_id)
    xero = connect_to_xero()
    xero.populate_tracking_categories()
    option = xero.TCShow.options.get(tracking_id)

    option['IsArchived'] = True
    response = xero.TCShow.options.save(option)
    # response = xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'IsArchived': option['IsArchived']})
    return response


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
    option[0]['Name'] = text.lower()
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


def rename_dropbox_folder(channel_name, project_id, text):
    dbx = connect_to_dropbox()
    schema = json.loads(os.environ['DROPBOX_FOLDER_SCHEMA'])
    for folder in schema['folders']:
        print 'from: {}'.format(format_slug(project_id, channel_name))
        print 'text: {}'.format(text)
        print 'to: {}'.format(text)
        response = dbx.files_move(os.path.join(folder['root'], format_slug(project_id, channel_name)), os.path.join(folder['root'], text))
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
        as_user="true",
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
    url = 'http://lucid-pro.herokuapp.com/admin/mission_control/project/{}/change/'.format(project_id)
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


def create_slack_channel(text, token):
    '''
    Creates a slack channel
    '''
    #check to see if there's 'P-00..' on the front of text, and remove it
    if text.lower()[0:2] == "p-":
        text = text.lower().split('-', 2)[2]
        # m = re.search('p-0*-(.*)',text)
        # text = m.group(0)

    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    # url = 'https://slack.com/api/channels.create'

    output = sc.api_call(
        "channels.create",
        name=text
    )

    return output


def create_all(text, response_url, token, results):
    issues = {}
    codes = {
        'entry': None,
        'slack': None,
        'pin': None,
        'dropbox': None,
        'xero': None
    }
    try:

        print "Creating Slug from Title"
        slug = create_slug(text)
        message = (
            'Successfully Created New Project: {}'.format(slug)
        )
        results['text'] = message
        print "Create Slug returns: {}".format(slug)

        print 'This is the response_url: {}. This is the text: {}'.format(response_url, slug)
        slack_response = create_slack_channel(slug, token)
        if slack_response.get('ok'):
            codes['slack'] = 'OK'
        else:
            codes['slack'] = 'ISSUE'
        print 'Create channel returns: {}'.format(slack_response)
        channel_id = slack_response['channel']['id']
        project_entry_response = create_project_entry(text, slug, channel_id)

        if str(project_entry_response.status_code).startswith('2'):
            codes['entry'] = 'OK'
        else:
            codes['entry'] = 'ISSUE'

        print "Create Project Entry returns: {}".format(project_entry_response)
        slack_pin_response = create_slack_pin(slug, channel_id)
        if slack_pin_response.get('ok'):
            codes['pin'] = 'OK'
        else:
            codes['pin'] = 'ISSUE'
        print 'Create pin returns: {}'.format(slack_pin_response)
        # airtable_response = create_airtable_entry(text)
        # print 'Create airtable entry returns: {}'.format(airtable_response)
        # # meistertask_response = create_meistertask_project(text)
        # print 'Create meistertask project returns: {}'.format(meistertask_response)
        # mindmeister_response = create_mindmeister_folder(text)
        # print 'Create mindmeister folder returns: {}'.format(mindmeister_response)
        # root = ET.fromstring(mindmeister_response.content)
        # folder_id = root[0].attrib['id']
        # mindmeister_response2 = create_mindmeister_map(text)
        # print 'Create mindmeister map returns: {}'.format(mindmeister_response2)
        # root = ET.fromstring(mindmeister_response2.content)
        # map_id = root[0].attrib['id']
        # mindmeister_response3 = move_mindmeister_map(folder_id, map_id)
        # print 'Move mindmeister map returns: {}'.format(mindmeister_response3)
        try:
            create_dropbox_folder_response = create_dropbox_folder(slug)
            print 'Crete dropbox folder returns: {}'.format(create_dropbox_folder_response)
            codes['dropbox'] = 'OK'
        except Exception as e:
            print "Dropbox issues: {}".format(e)
            codes['dropbox'] = 'ISSUE'
            issues['dropbox'] = '{}'.format(e)
            pass


        try:
            xero_trackingcategory_response = create_xero_tracking_category(slug)
            print 'Create xero tracking category returns: {}'.format(xero_trackingcategory_response)
            codes['xero'] = 'OK'
        except Exception as e:
            print "Xero issues: {}".format(e)
            issues['xero'] = '{}'.format(e)
            codes['xero'] = 'ISSUE'

    except Exception as e:
        print "Woops! Looks like we got an exception! {}".format(e)

        pass
    print "These are the codes: {}".format(codes)
    description = ''
    for code in codes:
        description += '{}: {}, '.format(code.upper(), codes[code])
    if issues:
        reason = ''
        for issue in issues:
            reason += '{}: {}, '.format(issue.upper(), issues[issue])
        reason = reason.strip(', ')
        results['attachments'].append({'text': reason})
    description = description.strip(', ')
    results['attachments'][0]['text'] = description
    headers = {'Content-Type': 'application/json'}
    requests.post(response_url, data=json.dumps(results), headers=headers)


def archive_all(text, response_url, channel_id, channel_name, token, results):
    issues = {}
    codes = {
        'entry': None,
        'slack': None,
        'dropbox': None,
        'xero': None
    }
    try:
        description = 'Everything looks good!'
        project_id = get_project_id_from_channel(channel_id)
        slug = format_slug(project_id, text)
        print slug
        archive_project_response = archive_project(channel_id, text, slug, project_id)
        message = (
            'Successfully Archived Project in Database'
        )
        results['text'] = message
        print 'Archive project returns: {}'.format(archive_project_response)
        if str(archive_project_response.status_code).startswith('2'):
            codes['entry'] = 'OK'
        else:
            codes['entry'] = 'ISSUE'
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
        slack_response = archive_slack_channel(text, token, channel_id)
        if slack_response.get('ok'):
            codes['slack'] = 'OK'
        else:
            codes['slack'] = 'ISSUE'
        print 'Archive channel returns: {}'.format(slack_response)

        try:
            archive_dropbox_folder_response = archive_dropbox_folder(channel_name, project_id, slug)
            print 'Archive dropbox folder returns: {}'.format(archive_dropbox_folder_response)
            codes['dropbox'] = 'OK'
        except Exception as e:
            print "Dropbox issues: {}".format(e)
            codes['dropbox'] = 'ISSUE'
            issues['dropbox'] = '{}'.format(e)
            pass

        try:
            xero_trackingcategory_response = archive_xero_tracking_category(channel_name, project_id, slug)
            print 'Archive xero tracking category returns: {}'.format(xero_trackingcategory_response)
            codes['xero'] = 'OK'
        except Exception as e:
            print "Xero issues: {}".format(e)
            codes['xero'] = 'ISSUE'
            issues['xero'] = '{}'.format(e)
    except Exception as e:
        print "Woops! Looks like we got an exception! {}".format(e)
        description = "Woops! Looks like we got an exception! {}".format(e)
    print "These are the codes: {}".format(codes)
    description = ''
    for code in codes:
        description += '{}: {}, '.format(code.upper(), codes[code])
    if issues:
        reason = ''
        for issue in issues:
            reason += '{}: {}, '.format(issue.upper(), issues[issue])
        reason = reason.strip(', ')
        results['attachments'].append({'text': reason})
    description = description.strip(', ')
    results['attachments'][0]['text'] = description
    headers = {'Content-Type': 'application/json'}
    requests.post(response_url, data=json.dumps(results), headers=headers)


def rename_all(text, response_url, channel_id, channel_name, token, results):
    issues = {}
    codes = {
        'entry': None,
        'slack': None,
        'dropbox': None,
        'xero': None
    }
    try:
        description = 'Everything looks good!'
        project_id = get_project_id_from_channel(channel_id)
        slug = format_slug(project_id, text)
        print slug
        rename_project_response = rename_project(channel_id, text, slug, project_id)
        message = (
            'Successfully Renamed {} to: {}'.format(channel_name, slug)
        )
        results['text'] = message
        print 'Rename project returns: {}'.format(rename_project_response)
        if str(rename_project_response.status_code).startswith('2'):
            codes['entry'] = 'OK'
        else:
            codes['entry'] = 'ISSUE'
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
        slack_response = rename_slack_channel(text, token, channel_id)
        if slack_response.get('ok'):
            codes['slack'] = 'OK'
        else:
            codes['slack'] = 'ISSUE'
        print 'Rename channel returns: {}'.format(slack_response)

        try:
            rename_dropbox_folder_response = rename_dropbox_folder(channel_name, project_id, slug)
            print 'Rename dropbox folder returns: {}'.format(rename_dropbox_folder_response)
            codes['dropbox'] = 'OK'
        except Exception as e:
            print "Dropbox issues: {}".format(e)
            codes['dropbox'] = 'ISSUE'
            issues['dropbox'] = '{}'.format(e)
            pass

        try:
            xero_trackingcategory_response = rename_xero_tracking_category(channel_name, project_id, slug)
            print 'Rename xero tracking category returns: {}'.format(xero_trackingcategory_response)
            codes['xero'] = 'OK'
        except Exception as e:
            print "Xero issues: {}".format(e)
            codes['xero'] = 'ISSUE'
            issues['xero'] = '{}'.format(e)
    except Exception as e:
        print "Woops! Looks like we got an exception! {}".format(e)
        description = "Woops! Looks like we got an exception! {}".format(e)
    print "These are the codes: {}".format(codes)
    description = ''
    for code in codes:
        description += '{}: {}, '.format(code.upper(), codes[code])
    if issues:
        reason = ''
        for issue in issues:
            reason += '{}: {}, '.format(issue.upper(), issues[issue])
        reason = reason.strip(', ')
        results['attachments'].append({'text': reason})
    description = description.strip(', ')
    results['attachments'][0]['text'] = description
    headers = {'Content-Type': 'application/json'}
    requests.post(response_url, data=json.dumps(results), headers=headers)


def get_status(response_url, channel_name, channel_id, status):
    project_id = get_project_id_from_channel(channel_id)
    field = None
    options = []
    if status.lower() == 'p':
        field = 'production_state'
    if status.lower() == 's':
        field = 'sales_state'
    if status.lower() == 'i':
        field = 'invoice_state'
    print "this is project_id: {}".format(project_id)
    response = requests.get('http://lucid-pro.herokuapp.com/api/project/{}/?format=json&username=admin&api_key=LucyT3st'.format(project_id))
    print "this is the response: {}".format(response)
    options_response = requests.get('http://lucid-pro.herokuapp.com/api/project/schema/?format=json&username=admin&api_key=LucyT3st')
    choices = options_response.json()['fields'][field]['choices']
    for choice in choices:
        options.append({'text': choice[1], 'value': choice[0]})
    status_value = response.json()[field]
    results = {'text': 'Current {}: {}'.format(field.replace('_', ' ').upper(), status_value)}
    headers = {'Content-Type': 'application/json'}
    results['attachments'] = [
        {
            'text': 'Change {}'.format(field.replace('_', ' ').upper()),
            "color": "#3AA3E3",
            "attachment_type": "default",
            "callback_id": field,
            'fallback': "If you could read this message, you'd be choosing a new state right now.",
            "actions": [
                {
                    "name": "{}_choice".format(field),
                    "text": "Set New State...",
                    "type": "select",
                    "options": options
                }
            ]

        }
    ]
    response = send_slack_state_menu(channel_id, results)


def set_status(response_url, channel_name, channel_id, selection, status_type):
    project_id = get_project_id_from_channel(channel_id)
    print 'project_id: {}'.format(project_id)
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    url = 'http://lucid-pro.herokuapp.com/api/project/{}/?username=admin&api_key=LucyT3st'.format(project_id)
    payload = {
        str(status_type): selection
    }
    print 'url: {}'.format(url)
    print 'payload: {}'.format(payload)
    r = requests.put(url, data=json.dumps(payload), headers=headers)
    print 'r: {}'.format(r)
    print 'r.content: {}'.format(r.content)

    results = {'text': 'Successfully Changed State', 'attachments': [{'text': 'Hooray!'}]}
    headers = {'Content-Type': 'application/json'}

    response = send_slack_state_menu(channel_id, results)
    # if response.json()['message']['attachments'][0]['actions'][0]['']
    # requests.post(response_url, data=json.dumps(results), headers=headers)

@app.route('/change_state', methods=['GET', 'POST'])
def change_state():
    results = {
        'text': 'woot'

    }
    # waiting = 'Request Received! Attempting to Change Project State'
    if request.method == "POST":
        form_json = json.loads(request.form['payload'])
        print form_json
        state_type = form_json['callback_id']
        channel_name = form_json['channel']['name']
        channel_id = form_json['channel']['id']
        selection = form_json['actions'][0]['selected_options'][0]['value']
        response_url = form_json['response_url']
        print "selection:"
        print selection
        t = Thread(target=set_status, args=(response_url, channel_name, channel_id, selection, state_type))
        t.start()
    return make_response("Changing State...", 200)
    #     response_url = request.form.get('response_url')
    #     token = request.form.get('token')
    #     if token != os.environ['INTEGRATION_TOKEN_STATE']:
    #         waiting = (
    #             'Invalid Slack Integration Token. Commands disabled '
    #             'until token is corrected. Try setting the '
    #             'SLACK_INTEGRATION_TOKEN environment variable'
    #         )
    # print waiting
    # headers = {'Content-Type': 'application/json'}
    # requests.post(response_url, data=json.dumps(results), headers=headers)
    # return waiting

@app.route('/')
def hello():
    errors = []
    results = {}
    return render_template('index.html', errors=errors, results=results)

@app.route('/state', methods=['GET', 'POST'])
def state():
    waiting = 'Request Received! Checking Project State...'
    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')
        channel_name = request.form.get('channel_name').capitalize()
        channel_id = request.form.get('channel_id')
        if token != os.environ['INTEGRATION_TOKEN_STATE']:
            waiting = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
                'we got this token: {}'.format(token)
            )

    t = Thread(target=get_status, args=(response_url, channel_name, channel_id, text))
    t.start()

    return waiting


@app.route('/archive', methods=['GET', 'POST'])
def archive():
    results = {
        'text': '',
        'response_type': 'ephemeral',
        'attachments': [
            {
                'text': ''
            }
        ]
    }
    waiting = 'Request Received! Attempting to Archive Project...'
    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')
        channel_name = request.form.get('channel_name').capitalize()
        channel_id = request.form.get('channel_id')
        if token != os.environ['INTEGRATION_TOKEN_RENAME']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Renamed {} to: {}'.format(channel_name, text)
            )
        results['text'] = message
        results['attachments'][0]['text'] = message

        t = Thread(target=archive_all, args=(text, response_url, channel_id, channel_name, token, results,))
        t.start()

    return waiting


@app.route('/rename', methods=['GET', 'POST'])
def rename():
    results = {
        'text': '',
        'response_type': 'ephemeral',
        'attachments': [
            {
                'text': ''
            }
        ]
    }
    waiting = 'Request Received! Attempting to Rename Project...'
    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')
        channel_name = request.form.get('channel_name').capitalize()
        channel_id = request.form.get('channel_id')
        if token != os.environ['INTEGRATION_TOKEN_RENAME']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Renamed {} to: {}'.format(channel_name, text)
            )
        results['text'] = message
        results['attachments'][0]['text'] = message

        t = Thread(target=rename_all, args=(text, response_url, channel_id, channel_name, token, results,))
        t.start()

    return waiting

@app.route('/create', methods=['GET', 'POST'])
def create():
    results = {
        'text': '',
        'response_type': 'ephemeral',
        'attachments': [
            {
                'text': ''
            }
        ]
    }
    waiting = 'Request Received! Attempting to Create Project...'

    if request.method == "POST":
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        token = request.form.get('token')

        if token != os.environ['INTEGRATION_TOKEN_CREATE']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Created New Project: {}'.format(text)
            )
        results['text'] = message
        results['attachments'][0]['text'] = message
        # create_all(text, response_url, token, results)
        t = Thread(target=create_all, args=(text, response_url, token, results,))
        t.start()

    return waiting

if __name__ == '__main__':
    app.run()
