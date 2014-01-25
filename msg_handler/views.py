from flask import request, make_response, render_template, redirect
from msg_handler import app, redis
from msg_handler.menu import menu
import json
import time
from msg_handler import logger
from msg_handler.vumi_go import VumiMessage


# TODO: move these authentication variables out of the git repo
ACCESS_TOKEN = app.config['ACCESS_TOKEN']
ACCOUNT_KEY = app.config['ACCOUNT_KEY']


def mark_online(user_id):
    now = int(time.time())
    expires = now + (app.config['ONLINE_LAST_MINUTES'] * 60) + 10
    all_users_key = 'online-users/%d' % (now // 60)
    user_key = 'user-activity/%s' % user_id
    p = redis.pipeline()
    p.sadd(all_users_key, user_id)
    p.set(user_key, now)
    p.expireat(all_users_key, expires)
    p.expireat(user_key, expires)
    p.execute()


def mark_menu(user_id, menu_marker):
    try:
        tmp = int(menu_marker)
    except Exception:
        menu_marker = None
        pass
    now = int(time.time())
    expires = now + (app.config['ONLINE_LAST_MINUTES'] * 60) + 10
    user_key = 'user-menu/%s' % user_id
    p = redis.pipeline()
    p.set(user_key, menu_marker)
    p.expireat(user_key, expires)
    p.execute()


def get_user_menu(user_id):
    """
    Retrieve stored session info.
    """

    menu_marker = redis.get('user-menu/%s' % user_id)
    if not menu_marker in [None, 'None']:  # the serializer may return a string
        try:
            # ensure the retrieved item can be converted to int
            tmp = int(menu_marker)
        except Exception:
            logger.exception("Bad session data encountered.")
            menu_marker = None
            pass
    return menu_marker


def get_online_users():
    current = int(time.time()) // 60
    minutes = xrange(app.config['ONLINE_LAST_MINUTES'])
    return redis.sunion(['online-users/%d' % (current - x)
                         for x in minutes])


def serialize_options(sub_menu, selected_endpoint=None):
    """
    Return a string representation of a given menu.
    """

    title = sub_menu['title']
    items = sub_menu['content']

    # add title
    options_str = title

    # add 'back' option
    if not sub_menu == menu:
        options_str += "\n0: Back"

    # add menu items
    try:
        for i in range(len(items)):
            item = items[i]
            options_str += "\n" + str(i+1) + ": " + item['title']
    except TypeError:
        # this is an endpoint list
        next = 2
        item = items[0]
        if selected_endpoint:
            try:
                item = items[selected_endpoint]
                next = selected_endpoint + 2
            except IndexError:
                selected_endpoint = 0
        options_str += "\n" + str(next) + ": Next"
        options_str += "\n" + item
    return options_str


def generate_output(user_id, selected_item=None):
    """
    Find the relevant menu to display, based on user input and saved session info.
    """

    # retrieve user's session, if available
    previous_menu = get_user_menu(user_id)
    logger.debug("PREVIOUS MENU: " + str(previous_menu))

    # handle 'back' links
    if previous_menu and selected_item == 0:
        if len(previous_menu) == 1:
            previous_menu = None
        else:
            previous_menu = previous_menu[0:-1]
        selected_item = None

    sub_menu = menu
    selected_endpoint = None
    try:
        # select user's previous menu
        if previous_menu:
            try:
                for i in previous_menu:
                    sub_menu = sub_menu['content'][int(i)]
            except Exception:
                logger.error("Could not retrieve previous menu: " + str(previous_menu))
                previous_menu = None
                pass

        # select the given option
        if selected_item:
            index = selected_item - 1
            try:
                if type(sub_menu['content'][index]) == dict:
                    sub_menu = sub_menu['content'][index]
                    if previous_menu:
                        previous_menu += str(index)
                    else:
                        previous_menu = str(index)
                else:
                    selected_endpoint = index
            except TypeError:
                # This is not a new menu, but an endpoint
                logger.debug("endpoint")
                pass
            except IndexError:
                # The selected option is not available
                logger.debug("out of bounds")
                pass

    except Exception:
        previous_menu = None
        pass

    # save user's menu to the session
    mark_menu(user_id, previous_menu)

    # return the menu's string representation
    str_out = serialize_options(sub_menu, selected_endpoint)
    return str_out


@app.route('/')
def index():
    """
    Redirect to admin.
    """

    return redirect('admin/')


@app.route('/message/', methods=['GET', 'POST'])
def message():
    """
    Handle incoming USSD messages, passed as HTTP requests via the vumi HTTP API.
    """

    logger.debug("MESSAGE endpoint called")

    if request.method == 'POST':

        tmp = request.get_json()
        msg = VumiMessage(tmp)
        if msg.content == "state: wait_ussrc":
            logger.debug("End of session message received.")
        else:
            logger.debug(msg)
            try:
                user_id = msg.from_addr  # user's cellphone number
                content = msg.content  # selected menu item, if any
                mark_online(user_id)
                selected_item = None
                try:
                    selected_item = int(content)
                except (ValueError, TypeError):
                    pass
                reply_content = generate_output(user_id, selected_item)
                if app.debug:
                    logger.debug(reply_content)
                else:
                    msg.reply(reply_content, ACCESS_TOKEN, ACCOUNT_KEY)
            except Exception as e:
                logger.exception(e)
                pass
    return make_response("OK")


@app.route('/event/', methods=['GET', 'POST'])
def event():
    """

    """

    logger.debug("EVENT endpoint called")
    tmp = request.get_json()
    logger.debug(json.dumps(tmp, indent=4))
    return make_response("OK")