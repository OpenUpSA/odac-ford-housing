from flask import request, make_response, render_template, redirect
from msg_handler import app, redis
from msg_handler.menu import menu
import json
import time
from msg_handler import db, logger
from msg_handler.vumi_go import VumiMessage
from flask.ext.login import current_user, login_required
from models import Query, Note

# TODO: move these authentication variables out of the git repo


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
            # don't add a 'next' link on the final screen
        if not(len(items) == 1 or (selected_endpoint and selected_endpoint == len(items) - 1)):
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
    Handle incoming messages, passed as HTTP requests via the vumi HTTP API.
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
                if msg.msg_type == "ussd":
                    user_id = msg.from_addr  # user's cellphone number
                    content = msg.content  # selected menu item, if any
                    mark_online(user_id)
                    selected_item = None
                    try:
                        selected_item = int(content)
                    except (ValueError, TypeError):
                        pass
                    reply_content = generate_output(user_id, selected_item)
                    if "Your number has been added to the list." in reply_content:
                        update_notification_list(msg.from_addr, "add")
                    msg.send_reply(reply_content)
                elif msg.msg_type == "sms":
                    msg.save_query()
                    tmp = "Thank you for submitting your query. It will be attended to as soon as possible."
                    msg.send_reply(tmp)
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


@login_required
@app.route('/response/', methods=['POST',])
def response():
    """
    Send SMS response to an SMS query.
    """

    logger.debug("RESPONSE endpoint called")

    user = current_user
    content = request.form['content']
    query_id = request.form['query_id']

    # send reply
    msg = VumiMessage({'query_id': query_id})
    msg.send_reply(content, session_event=None, user=user)

    # update query status
    qry = Query.query.get(query_id)
    qry.status = "in_progress"
    db.session.add(qry)
    db.session.commit()

    return redirect('/admin/queryview/', code=302)


@login_required
@app.route('/note/', methods=['POST',])
def note():
    """
    Save a note related to a query.
    """

    logger.debug("NOTE endpoint called")

    user = current_user
    content = request.form['content']
    query_id = request.form['query_id']

    # save note
    tmp = Note()
    tmp.user = user
    tmp.content = content
    tmp.query_id = query_id

    db.session.add(tmp)
    db.session.commit()

    return redirect('/admin/queryview/', code=302)


@login_required
@app.route('/toggle_star/', methods=['POST',])
def toggle_star():
    """
    Star / unstar a query.
    """

    logger.debug("TOGGLE STAR endpoint called")

    query_id = request.form['query_id']

    # toggle starred value
    qry = Query.query.get(query_id)
    qry.starred = not qry.starred
    db.session.add(qry)
    db.session.commit()

    return redirect('/admin/queryview/', code=302)


@login_required
@app.route('/update_status/', methods=['POST',])
def update_status():
    """
    Update a query status.
    """

    logger.debug("UPDATE STATUS endpoint called")

    query_id = request.form['query_id']
    status = request.form['status']

    # toggle starred value
    qry = Query.query.get(query_id)
    qry.status = status
    db.session.add(qry)
    db.session.commit()

    return redirect('/admin/queryview/', code=302)


def update_notification_list(number, add_or_remove="add"):
    """
    Add / Remove a user's number from the list of numbers to be notified when sending updates.
    """

    try:
        # read list from JSON file
        with app.open_instance_resource('notification_list.json', mode='r') as f:
            try:
                notification_list = json.loads(f.read())
            except ValueError, e:
                # start with clean list, if the file does not yet contain a list
                notification_list = []
                pass
            # add / remove item
        if add_or_remove == "add":
            if not number in notification_list:
                notification_list.append(number)
        elif add_or_remove == "remove":
            if number in notification_list:
                i = notification_list.index(number)
                notification_list = notification_list[0:i] + notification_list[i+1::]
            # write updated list to file
        with app.open_instance_resource('notification_list.json', mode='w') as f:
            f.write(json.dumps(notification_list, indent=4))
    except Exception, e:
        if add_or_remove == "add":
            logger.exception("Error saving number to the notification list.")
        else:
            logger.exception("Error removing number from the notification list.")
    return
