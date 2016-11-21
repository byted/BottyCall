import os
import sys
import json
import spotipy
import base64
import random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

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
    first = random.choice([
        'Sweetheart!',
        'Hey babe.',
        'Hi sweetie!'
    ])
    second = random.choice([
        'I was just thinking of you... in a special way ;) Are you in the mood for some play-time?',
        'Are you in the mood for some one-on-one time with me?',
        'I thought you might be in the mood for some special attention today...'
    ])
    
    res = []
    if send_fb_message(uid, first):
        res.append('sent message "{}" to user_id {}'.format(first, uid))
    if send_fb_message(uid, second):
        res.append('sent message "{}" to user_id {}'.format(first, uid))
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
    results = sp.recommendations(seed_tracks=['4WGENqnUmbv0Ml9NwXMlsD','3XJpQ65m90QFmogv8MH1pG','6CMKxvTzWB53CXrkWAdXul'], limit=20)
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
    params = {'access_token': os.environ['FB_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)
        return r.text, r.status
    else:
        return true


def spotify_auth_client_credentials(client_id, client_secret):
    data = {'grant_type': 'client_credentials'}
    r = requests.post('https://accounts.spotify.com/api/token', data=data, auth=(client_id, client_secret))
    log('Got from Spotify: {}'.format(r.text))
    return json.loads(r.text)['access_token'] if r.status_code == 200 else None


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


client_id, client_secret = os.environ['SPOTIFY_CLIENT_ID'], os.environ['SPOTIFY_CLIENT_SECRET']
log('client_id: ' + client_id + '/ client_secret: ' + client_secret)
token = spotify_auth_client_credentials(client_id, client_secret)
log('spotify token: ' + token)
sp = spotipy.Spotify(auth=token)

if __name__ == '__main__':
    app.run(debug=True)
