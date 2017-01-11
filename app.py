import os
from flask import Flask, request, render_template
import requests
import json
from slackclient import SlackClient


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


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
        slack_response = create_slack_channel(text, token)
        print 'Create channel returns: {}'.format(slack_response)

    # json_results = json.dumps(results)
    return results['msg']

if __name__ == '__main__':
    app.run()
