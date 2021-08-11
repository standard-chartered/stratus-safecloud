import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from db_models import UserModel, db

user_username = 'user@sc.com'
user_password = 'password'
aladdin_user_username = 'aladdin'
aladdin_user_password = 'aladdin'

import logging




@pytest.fixture
def client():

    APP_ROOT = os.path.join(os.path.dirname(__file__), '.')   # refers to application_top
    dotenv_path = os.path.join(APP_ROOT, '.env')
    
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

    app = create_app()

    with app.test_client() as client:
        
        with app.app_context():
            init_users()
        yield client

def init_users():
    db.create_all()
    user1 = UserModel.query.filter_by(username=user_username).first()

    if user1 is None:
        hash_password = generate_password_hash(user_password)
        user1 = UserModel(username=user_username, password=hash_password)
        db.session.add(user1)
        db.session.commit()
    
    user1 = UserModel.query.filter_by(username=aladdin_user_username).first()
    if user1 is None:
        hash_password = generate_password_hash(aladdin_user_password)
        user1 = UserModel(username=aladdin_user_username, password=hash_password)
        db.session.add(user1)
        db.session.commit()
