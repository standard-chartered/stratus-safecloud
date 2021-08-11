from logging.handlers import RotatingFileHandler
import os
import datetime
from flask import Flask, session, g

import flask_login

from db import db
from db_models import UserModel, init_db

import pymysql
pymysql.install_as_MySQLdb()


class User(flask_login.UserMixin):
    pass


def create_app():
    import logging
    if 'DEBUG' in os.environ and os.environ['DEBUG'] is True:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    handler = RotatingFileHandler('update_script.log', maxBytes=10000000, backupCount=5)
    logging.basicConfig(level=log_level, force=True, handlers=[handler])

    app = Flask(__name__)
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    app.config.update(
        # a default secret that should be overridden by instance config
        SECRET_KEY=os.urandom(12)
    )
    app.config['SQLALCHEMY_DATABASE_URI']=os.environ['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

    db.init_app(app)
    with app.app_context():
        db.create_all()
        init_db()

    app.app_context().push()

    # Set up the login manager
    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.refresh_view = 'relogin'
    login_manager.needs_refresh_message = (u"Session timed out, please re-login")
    login_manager.needs_refresh_message_category = "info"

    # Set it up so that the login session will timeout after 15 minutes
    # of inactivity
    @app.before_request
    def before_request():
        session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(minutes=60)
        session.modified = True
        g.user = flask_login.current_user
        if 'projects' not in g:
            from db_models import ProjectModel
            projects = ProjectModel.query.all()
            g.projects = projects

    @login_manager.user_loader
    def user_loader(id_str):
        if id_str is not None:
            id_as_int = int(id_str)
            existing_user = UserModel.query.filter_by(id=id_as_int).first()
            print(existing_user)
            if existing_user is not None:
                return existing_user
            return
        else:
            return

    # Register main blueprint

    # blueprint imports
    from main.views import main
    app.register_blueprint(main)
    return app

if __name__ == "__main__":
    # load dotenv in the base root
    APP_ROOT = os.path.dirname(__file__)   # refers to application_top
    dotenv_path = os.path.join(APP_ROOT, '.env')

    from dotenv import load_dotenv
    load_dotenv(dotenv_path)
    print(dotenv_path)

    print("OS ENVIRONMENT:"+os.environ['SQLALCHEMY_DATABASE_URI'])
    app = create_app()

    app.run(host=os.environ['SERVER'],port=os.environ['PORT'])