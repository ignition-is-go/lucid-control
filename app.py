import os
from flask import Flask, request, render_template
import requests
import json


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


def create_slack_channel(text, token):
    url = 'https://slack.com/api/channels.create'
    payload = {"token": token, "name": text}
    r = requests.post(url, json=json.dumps(payload))
    print r.status_code


@app.route('/')
def hello():
    errors = []
    results = {}
    return render_template('index.html', errors=errors, results=results)


@app.route('/create', methods=['GET', 'POST'])
def create():
    errors = []
    results = {'msg': '', 'errors': errors}
    if request.method == "POST":
        token = request.form.get('token')
        if token != app.config['INTEGRATION_TOKEN']:
            message = (
                'Invalid Slack Integration Token. Commands disabled '
                'until token is corrected. Try setting the '
                'SLACK_INTEGRATION_TOKEN environment variable'
            )

        else:
            message = (
                'Successfully Create New Project!'
            )
        results['msg'] = message
        response_url = request.form.get('response_url')
        text = request.form.get('text')
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
        create_slack_channel(text, token)
    json_results = json.dumps(results)
    return json_results

if __name__ == '__main__':
    app.run()
