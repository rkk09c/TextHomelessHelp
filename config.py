import os

# Flask Config
BASEDIR = os.path.abspath(os.path.dirname(__file__))
CSRF_ENABLED = os.environ.get('CSRF_ENABLED', True)
DEBUG = os.environ.get('DEBUG', False)
ENV = os.environ.get('ENV')
SECRET_KEY = os.environ.get('SECRET_KEY', 'secret_key')

# SQLAlchemy Config
DATABASE_QUERY_TIMEOUT = 0.5
SQLALCHEMY_MIGRATE_REPO = os.path.join(BASEDIR, 'db_repository')
SQLALCHEMY_RECORD_QUERIES = True
SQLALCHEMY_TRACK_MODIFICATIONS = False
# It's DATABASE_URL in heroku, which is a pain
SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

# TWILIO Config
try:
    TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
    TWILIO_ACCOUNT_AUTH = os.environ['TWILIO_ACCOUNT_AUTH']
except KeyError:
    raise ('Missing Twilio environ variables')
