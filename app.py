import os
from flask import Flask, request, render_template
import requests
import json
from slackclient import SlackClient
import datetime

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


def create_mindmeister_project(text):
    url = 'https://www.mindmeister.com/api/projects'
    payload = {
        'name': text
    }
    headers = {
        'content-type': 'application/json',
        'authorization': 'Bearer {}'.format(os.environ['MEISTERTASK_API_TOKEN'])
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
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
        mindmeister_response = create_mindmeister_project(text)
        print 'Create mindmeister project returns: {}'.format(mindmeister_response)

    return results['msg']

if __name__ == '__main__':
    app.run()
