import os
import sys
import json
import spotipy
import spotipy.util as util
import random

import requests
from flask import Flask, request, jsonify

# scope = 'playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private streaming user-library-read'
token = 'BQAyN5tuFrseBW657giCP0RsJ9DQnut49bQgT0v_e0wJ6CzhtTt8g5CAaHo-apiQAB3JYkGyR94zNRN8HOzAuZTmPJv3A0tNuISErumFLgNFlKm9blsH4FY7t71YSvKaHoFywmh59gsFQD1OxyZxETJhGQ2PF2atprX_wqr6IRoaerg9qPzjM6OHvS6wa25OODZfGYbC2yCg4-yhgGSQsknBLM4SQtORXCB5Ir1M8cszFqMhFEKE7YenVhlizuWqaooTVJTb0soOkajn8XEDembaD2HX6Uj2XfeMhBBN_lJmpJoo'
app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events
    data = request.get_json()
    log(json.dumps(data, indent=4))  # you may not want to log every incoming message in production, but it's good for testing

    if data['result']['metadata']['intentName'] in ['ON-6-No Headphones', 'ON-6-Headphones']:
        log('go get spotify stuff')
        song = get_rec()

        pre_message = 'OK, then you\'re all set for some sexy tunes' if data['result']['metadata']['intentName'] == 'ON-6-Headphones' else 'You really need to put them on if you want to hear what I am about to play to you.'

        if data['originalRequest']['source'] == 'facebook':
            sender_id = data['originalRequest']['data']['sender']['id']
            send_fb_message(sender_id, pre_message)
            send_fb_message(sender_id, 'How about something by {}?'.format(song['artist']))

        fb_msg = {
            # 'text': 'How about something by {}?\n {}'.format(song['artist'], song['url']) 
            "attachment": {
                "type":"template",
                "payload": {
                    "template_type":"generic",
                    "elements":[
                        {
                            "title": song['title'],
                            "item_url": song['url'],
                            "image_url": song['img_url'],
                            "subtitle": song['artist']
                        }
                    ]
                }
            }
        }
        slack_msg = { 'text': '{}\nHow about something by {}?\n {}'.format(pre_message, song['artist'], song['url']) }
        res = {
            'displayText': 'foobar',
            'data': {'facebook': fb_msg, 'slack': slack_msg }
        }

    return jsonify(res)


@app.route('/init', methods=['GET'])
def init():
    return send_fb_message('1130764070353241', 'buh')


@app.route('/rec', methods=['GET'])
def rec():
    return jsonify(get_rec())





def get_rec():
    results = sp.recommendations(seed_tracks=['4WGENqnUmbv0Ml9NwXMlsD'], limit=20)
    track = random.choice(results['tracks'])


    songs = [{'title': t['name'], 'artist': t['artists'][0]['name']} for t in results['tracks']]
    return {
        'title': track['name'],
        'artist': track['artists'][0]['name'],
        'url': track['external_urls']['spotify'],
        'img_url': track['album']['images'][1]['url'],
        'id': track['id'],
        'preview_url': track['preview_url'],
        'uri': track['uri']
        }


def send_fb_message(recipient_id, message_text):
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
    params = {
        "access_token": "EAAFDBWJmmpoBAAxgZAdXTybkgSd4HNvu08bbiBGogPSvHmYwU6r7pjLmRFEKtoUXx1J8WMR2wd83z5iyFUcEA0lmfKPxpSwjmccedZCDR4IeJYtlbhYQuIyTSLQKsvk5FpaRYigrGMP6d5FSXZCHSINuXQoPiOo3q0qAjhAqwZDZD"
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        return r.text, r.status
    else:
        return 'sent message {} to user_id {}'.format(message_text, recipient_id), 200


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


if __name__ == '__main__':
    sp = spotipy.Spotify(auth=token)

    app.run(debug=True)
