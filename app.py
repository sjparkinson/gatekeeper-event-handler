from chalice import Chalice, BadRequestError
from datetime import datetime
import json
import logging
import requests

FCM_ENDPOINT = 'https://fcm.googleapis.com/fcm/send'
FIREBASE_DATABASE_ENDPOINT = 'https://gatekeeper-kew.firebaseio.com'
FIREBASE_DATABASE_SECRET = '@@FIREBASE_DATABASE_SECRET@@'
FIREBASE_SERVER_KEY = '@@FIREBASE_SERVER_KEY@@'

PARTICLE_ENDPOINT = 'https://api.particle.io/v1/devices/'
PARTICLE_AUTH = '@@PARTICLE_AUTH@@'
PARTICLE_DEVICE = '@@PARTICLE_DEVICE@@'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app = Chalice(app_name='gatekeeper-event-handler')
app.debug = True


@app.route('/event', methods=['POST'])
def particle_event():
    now = datetime.utcnow()
    event = app.current_request.json_body

    logger.info("Recieved Particle event: {}".format(json.dumps(event)))

    # Check we have the required event keys.
    for key in ['name', 'source']:
        if key not in event:
            raise BadRequestError("The `{}` key was missing from the event.".format(key))

    # Store event in the database.
    formatted_event = dict(event, **{
        'published': now.isoformat(' '),
        'sort': (now - datetime(1970, 1, 1)).total_seconds() * -1
    })

    logger.info("Storing formatted event: {}".format(json.dumps(formatted_event)))

    response = requests.post(
        FIREBASE_DATABASE_ENDPOINT + '/events.json',
        json=formatted_event,
        params={'auth': FIREBASE_DATABASE_SECRET}
    )

    logger.info('Database response was: {} {}'.format(response.status_code, response.reason))
    logger.info('Datebase request took: {}'.format(response.elapsed))

    logger.info('Sending FCM message.')

    # Send FCM message.
    response = requests.post(
        FCM_ENDPOINT,
        headers={'Authorization': 'key=' + FIREBASE_SERVER_KEY},
        json={
            'to': '/topics/' + event['name'].partition('/')[2],
            'data': {
                'event': {
                    'name': event['name'],
                    'source': event['source']
                }
            }
        }
    )

    logger.info('FCM response was: {} {}'.format(response.status_code, response.reason))
    logger.info('FCM request took: {}'.format(response.elapsed))

    return "Thanks!"


@app.route('/assistant-action', methods=['POST'])
def assistant_action():
    action = app.current_request.json_body

    command = '/unlock' if action['result']['action'] == 'unlock' else '/prime'

    # Send particle command
    response = requests.post(
        PARTICLE_ENDPOINT + PARTICLE_DEVICE + command,
        headers={'Authorization': 'Bearer ' + PARTICLE_AUTH},
    )

    logger.info('particle response was: {} {}'.format(response.status_code, response.reason))
    logger.info('particle request took: {}'.format(response.elapsed))

    return "Thanks!"
