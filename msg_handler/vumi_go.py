import json
from datetime import datetime
from msg_handler import logger
import requests


class VumiMessage():

    def __init__(self, msg_dict):
        try:
            self.msg_type = msg_dict['transport_type']  # either 'ussd' or 'sms'
            self.content = msg_dict['content']
            self.message_id = msg_dict['message_id']
            self.conversation_key = msg_dict['helper_metadata']['go']['conversation_key']
            self.from_addr = msg_dict['from_addr']
            self.timestamp = msg_dict['timestamp']  # e.g. "2013-12-02 06:28:07.430549"
            self.datetime = datetime.strptime(self.timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError, e:
            logger.exception("Could not create VumiMessage instance.")
        return

    def reply(self, content, access_token, account_key, session_event="resume"):
        conversation_key = self.conversation_key
        message_url = 'http://go.vumi.org/api/v1/go/http_api/' + conversation_key + '/messages.json'
        payload = {
            "in_reply_to": self.message_id,
            "content": content,
            "session_event": session_event,
            }
        r = requests.put(message_url, auth=(account_key, access_token),
                     data=json.dumps(payload))
        if not r.status_code == 200:
            logger.error("HTTP error encountered while trying to send message though VumiGo API.")
        return r.text

    def __repr__(self):

        tmp = {
            'msg_type': self.msg_type,
            'content': self.content,
            'message_id': self.message_id,
            'conversation_key': self.conversation_key,
            'from_addr': self.from_addr,
            'timestamp': self.timestamp,
        }
        return json.dumps(tmp, indent=4)