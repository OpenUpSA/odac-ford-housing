import msg_handler
import unittest
import simplejson
import requests


class MsgHandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.base_url = 'http://localhost:5000/'
        # self.base_url = 'http://ford-housing.demo4sa.org/'

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
        assert 'OK' in self.send_msg("SMS", "atest")


if __name__ == '__main__':
    unittest.main()

    # base_url = 'http://localhost:5000/'
    #
    # filename = 'example_messages/ussd_example.json'
    # f = open(filename, 'r')
    # msg = simplejson.loads(f.read())
    # msg['content'] = 3
    # msg_str = simplejson.dumps(msg)
    #
    # headers = {'content-type': 'application/json'}
    # r = requests.post(base_url + 'message/', data=msg_str, headers=headers)
    #
    # assert r.status_code == 200
    # print r.text