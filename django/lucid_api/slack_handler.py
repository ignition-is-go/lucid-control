import logging
import simplejson as json

from django.http import JsonResponse, HttpResponse
from . import tasks

def create(request):
    assert(isinstance(request, HttpRequest))
    try:
        validate_slack(request.POST['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # we've verified the slack app, let's go!
        tasks.create_from_slack.delay(request.POST)
        return HttpResponse()
    pass

def rename(request):
    pass

def archive(request):
    pass

def action_response(request):
    ''' handles all slack action message responses'''
    logger = logging.getLogger(__name__+": action_handler")
    # slack tends to send json all bundled in the 'payload' form var
    slack_data = json.loads(request.POST['payload'])
    if slack_data is None:
        # just in case slack changes
        slack_data = request.POST

    try:
        validate_slack(slack_data['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        if "challenge" in slack_data.keys():
            logger.info("Responding to challenge: %s", slack_data['challenge'])
            return slack_data['challenge']
        
        elif "callback_id" in slack_data.keys():
            logger.info("Routing Action: %s", slack_data['callback_id'])
            func_name = slack_data['callback_id']
            func = getattr(api, func_name)

            logger.debug("Preparing to thread %s for action:%s - %s", func_name, slack_data['channel']['name'],slack_data['actions'])
            # TODO: celery task here
            # t = Thread(target=func,args=[slack_data])
            # t.start()
            # logger.debug("Thread started!")
            return "", 200, {'ContentType':'application/json'}


def validate_slack(token):
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
        # this token didn't come from slack
        raise InvalidSlackToken(
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable.'
        )
    else:
        return True

class InvalidSlackToken(Exception):
    pass