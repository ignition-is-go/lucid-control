import os
from flask import Flask, request, render_template
from config import INTEGRATION_TOKEN
import requests
import json


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])


@app.route('/')
def hello():
    errors = []
    results = {}
    return render_template('index.html', errors=errors, results=results)


@app.route('/create', methods=['GET', 'POST'])
def create():
    errors = []
    results = {'msg': 'yay!', 'errors': errors}
    if request.method == "POST":
        token = request.form.get('token')
        if token != INTEGRATION_TOKEN:
        message = (
            'Invalid Slack Integration Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_INTEGRATION_TOKEN environment variable'
        )
        results['msg'] = message

        response_url = request.form.get('response_url')
        text = request.form.get('text')
        print 'This is the response_url: {}. This is the text: {}'.format(response_url, text)
    json_results = json.dumps(results)
    return json_results

if __name__ == '__main__':
    app.run()
