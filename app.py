from chalice import Chalice, BadRequestError
from datetime import datetime
import json
import logging
import requests

FIREBASE_DATABASE_ENDPOINT = 'https://gatekeeper-kew.firebaseio.com'
FIREBASE_DATABASE_SECRET = '@@FIREBASE_DATABASE_SECRET@@'
FIREBASE_SERVER_KEY = '@@FIREBASE_SERVER_KEY@@'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app = Chalice(app_name='gatekeeper-event-handler')
app.debug = True


@app.route('/')
def index():
    return "OK"


@app.route('/event', methods=['POST'])
def particle_event():
    logger.debug("Starting event request handling.")

    event = app.current_request.json_body

    logger.info("Recieved Particle event: {}".format(json.dumps(event)))

    # Check we have the required event keys.
    for key in ['name', 'source']:
        if key not in event:
            raise BadRequestError(
                "The `{}` key was missing from the event.".format(key))

    # Store event in the database.
    formatted_event = dict(event, **{
        'published': datetime.utcnow().isoformat(' '),
        'sort': (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * -1
    })

    logger.info("Storing formatted event: {}".format(json.dumps(formatted_event)))

    response = requests.post(
        FIREBASE_DATABASE_ENDPOINT + '/events.json',
        json = formatted_event,
        params = { 'auth': FIREBASE_DATABASE_SECRET }
    )

    logger.info('Database response was: {}'.format(response))
    logger.info('Datebase request took: {}'.format(response.elapsed))

    logger.info('Sending FCM message.')

    # Send FCM message.
    response = requests.post(
        'https://fcm.googleapis.com/fcm/send',
        headers = {
            'Authorization': 'key=' + FIREBASE_SERVER_KEY
        },
        json = {
            'to': '/topics/' + event['name'].partition('/')[2],
            'data': {
                'event': {
                    'name': event['name'],
                    'source': event['source']
                }
            }
        }
    )

    logger.info('FCM response was: {}'.format(response))
    logger.info('FCM request took: {}'.format(response.elapsed))

    return "Thanks!"
