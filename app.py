import os
import sys
import json
import spotipy
import spotipy.util as util
import random

import requests
from flask import Flask, request, jsonify

# scope = 'playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private streaming user-library-read'

token='BQBQdYv3_ZoWzieGgiLg-tYv2weboZ6WJW1i_U1TFHoBmWajx9c1HCSktBAxodEjGuNnLSACP54re3IGjPl9SdiBi0ANKfoLvKJGk8jK8pXGovEEXvUsju9hvcQkDVFhwus5ApEPCFIm74f-z1SmeKCk87eKmWHJvc91OdS5KcLRZkV4xegW5wnrhacLQw4Wh4Y_PurFqepaHlJ3xmphwEXNphBcdqwbt07S7HAp6-Yl1nAjfQalfqTdoJK-DFkwtblO8SVLKstSFzkEnB5-luiNxDbtmBMO_JPhvGNzxHpEXbLr'
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
    elif data['result']['metadata']['intentName'] in ['ON-6-Change Music']:
        artist = search_artist(data['result']['parameters']['artist'])
        msg1 = [
            'Of course, Babe, that\'s no Problem.',
            'Sure, Babe.',
            'I am sorry you didn\'t like what I have shown you...'
        ]
        msg2 = [
            'I think {} is what you\'re looking for.',
            '{} should do the trick.',
            'Here is something nice by {}.'
        ]
        if artist is not None:
            fb_msg = {
                # 'text': 'How about something by {}?\n {}'.format(song['artist'], song['url']) 
                "attachment": {
                    "type":"template",
                    "payload": {
                        "template_type":"generic",
                        "elements":[
                            {
                                "title": artist['artist'],
                                "item_url": artist['url'],
                                "image_url": artist['img_url']
                            }
                        ]
                    }
                }
            }
            slack_msg = { 'text': '{}\n{}\n{}'.format(random.choice(msg1), random.choice(msg2).format(artist['artist']), artist['url']) }
            res = {
                'displayText': 'foobar',
                'data': {'facebook': fb_msg, 'slack': slack_msg }
            }
            if data['originalRequest']['source'] == 'facebook':
                sender_id = data['originalRequest']['data']['sender']['id']
                send_fb_message(sender_id, random.choice(msg1))
                send_fb_message(sender_id, random.choice(msg2).format(artist['artist']))
        else:
            res = {
                'displayText': 'Sorry, I have nothing for {}'.format(artist['artist']),
                # 'data': {'facebook': fb_msg, 'slack': slack_msg }
            }

    return jsonify(res)


@app.route('/init', methods=['GET'])
def init():
    uid = request.args.get('uid')
    first = [
        'Sweetheart!',
        'Hey babe.',
        'Hi sweetie!'
    ]
    second = [
        'I was just thinking of you... in a special way ;) Are you in the mood for some play-time?',
        'Are you in the mood for some one-on-one time with me?',
        'I thought you might be in the mood for some special attention today...'
    ]
    res = []
    res.append(send_fb_message(uid, random.choice(first)))
    res.append(send_fb_message(uid, random.choice(second)))
    return '<br>'.join(res)


@app.route('/rec', methods=['GET'])
def rec():
    return jsonify(get_rec())


def search_artist(artist):
    result = sp.search(q=artist, type='artist')
    if len(result['artists']['items']) > 0:
        artist = result['artists']['items'][0]
        return {
            'artist': artist['name'],
            'url': artist['external_urls']['spotify'],
            'img_url': artist['images'][1]['url']
        }
    else:
        return None


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
        return 'sent message "{}" to user_id {}'.format(message_text, recipient_id)


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


if __name__ == '__main__':
    sp = spotipy.Spotify(auth=token)

    app.run(debug=True)
