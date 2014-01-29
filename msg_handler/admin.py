from flask import Flask, url_for, redirect, render_template, request
from wtforms import form, fields, validators
from wtforms.fields import SelectField, TextAreaField
from flask.ext import admin, login
from flask.ext.admin.contrib import sqla
from flask.ext.admin import helpers, expose
from flask.ext.admin.model.template import macro
from flask.ext.admin.form import rules
from flask.ext.login import current_user
from msg_handler import app, db, logger
from msg_handler.models import *
from vumi_go import VumiMessage
import json

# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    email = fields.TextField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        if user.password != hash(self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(email=self.email.data).first()


class RegistrationForm(form.Form):
    email = fields.TextField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(email=self.email.data).count() > 0:
            raise validators.ValidationError('Duplicate users')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated()


# Create customized index view class that handles login & registration
class MyAdminIndexView(admin.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated():
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated():
            return redirect(url_for('.index'))
        link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = User()

            # hash password, before populating User object
            form.password.data = hash(form.password.data)
            form.populate_obj(user)

            db.session.add(user)
            db.session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


class QueryView(MyModelView):

    # disable manual editing / deletion of messages
    can_create = False
    can_edit = False
    can_delete = False
    column_list = (
        'starred',
        'datetime',
        'from_addr',
        'status',
        'content',
        'notes',
        'responses'
    )
    column_labels = dict(
        datetime='Date',
        from_addr='From',
        content='Message'
    )
    column_formatters = dict(
        starred=macro('render_star'),
        datetime=macro('render_date'),
        status=macro('render_status'),
        content=macro('render_content'),
        notes=macro('render_notes'),
        responses=macro('render_responses')
    )
    column_sortable_list = ('starred', 'datetime', 'from_addr', 'status')
    column_searchable_list = ('content', Response.content)
    column_default_sort = ('datetime', True)
    list_template = 'query_list_template.html'
    form_overrides = dict(
        content=TextAreaField,
        )
    form_args = dict(
        status=dict(
            choices=[
                ('pending', 'pending'),
                ('in_progress', 'in progress'),
                ('finished', 'finished')
            ]
        )
    )
    inline_models = [(Response, dict(form_label='Reply', ))]


class UserView(MyModelView):

    can_create = False
    column_list = (
        'email',
        'first_name',
        'last_name'
    )


class UpdateView(MyModelView):

    can_delete = False
    can_edit = False
    list_template = 'update_list_template.html'
    column_list = (
        'datetime',
        'user',
        'content',
        'notes'
    )
    column_labels = dict(
        datetime='Date',
        user='User',
        content='Message',
        notes='Notes'
    )
    column_default_sort = ('datetime', True)
    column_formatters = dict(
        datetime=macro('render_date'),
        user=macro('render_user'),
    )
    form_overrides = dict(
        content=TextAreaField,
    )
    form_create_rules = [
        rules.Field('content'),
    ]

    def on_model_change(self, form, model, is_created):

        # send SMS notifications before saving message to database
        msg = VumiMessage({"content": model.content})
        count_tot = 0
        model.user = current_user

        try:
            with app.open_instance_resource('notification_list.json', mode='r') as f:
                try:
                    notification_list = json.loads(f.read())
                except ValueError:
                    # start with clean list, if the file does not yet contain a list
                    notification_list = []
                    pass
                for number in notification_list:
                    logger.debug("sending update to: " + number)
                    msg.send(number)
                    count_tot += 1
            model.notes = "Update sent to " + str(count_tot) + " user(s)."
        except Exception:
            tmp = "Error sending update broadcast via SMS."
            logger.exception(tmp)
            model.notes = tmp
        return


# Initialize flask-login
init_login()

# Create admin
admin = admin.Admin(app, 'Ford Housing', index_view=MyAdminIndexView(), base_template='my_master.html')

# Add views
admin.add_view(UserView(User, db.session))
admin.add_view(QueryView(Query, db.session))
admin.add_view(UpdateView(Update, db.session))