import os
from flask import Flask, request, render_template
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
def index():
    errors = []
    results = {'msg': 'yay!', 'errors': errors}
    if request.method == "POST":
        data = request.data
        print data
    json_results = json.dumps(results)
    return json_results

if __name__ == '__main__':
    app.run()
