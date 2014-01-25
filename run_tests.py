import msg_handler
import unittest
import simplejson
import requests


class MsgHandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.base_url = 'http://localhost:5000/'
        # self.base_url = 'http://ec2-54-194-198-122.eu-west-1.compute.amazonaws.com/'

    def send_msg(self, msg_type="USSD", content="1"):
        filename = 'example_messages/ussd_example.json'
        if msg_type == "SMS":
            filename = 'example_messages/sms_example.json'
        f = open(filename, 'r')
        msg = simplejson.loads(f.read())
        msg['content'] = content
        msg_str = simplejson.dumps(msg)

        headers = {'content-type': 'application/json'}
        r = requests.post(self.base_url + 'message/', data=msg_str, headers=headers)

        assert r.status_code == 200
        return r.text


    def test_message_handler(self):
        """
        Check the contents of the response, after hitting the server with a message.
        """
        assert 'OK' in self.send_msg("USSD", "1")
        assert 'OK' in self.send_msg("SMS", "test")


    def test_populated_cache(self):
        """
        Check that a user's details are retained in the cache, after sending a message.
        """
        tmp = self.send_msg("USSD", "1")
        print tmp

        r = requests.get(self.base_url)
        assert r.status_code == 200
        print r.text
        assert '+27738257667' in r.text


if __name__ == '__main__':
    unittest.main()