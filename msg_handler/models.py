from msg_handler import db
from sqlalchemy.orm import backref


# Create user model.
class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.email


class Query(db.Model):

    query_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(180))
    vumi_message_id = db.Column(db.String(100), unique=True)
    conversation_key = db.Column(db.String(100))
    from_addr = db.Column(db.String(100))
    datetime = db.Column(db.DateTime())


class Response(db.Model):

    response_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(180), nullable=False)
    datetime = db.Column(db.DateTime())

    query_id = db.Column(db.Integer, db.ForeignKey('query.query_id'))
    query = db.relationship('Query', backref=backref("responses", order_by=datetime))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')