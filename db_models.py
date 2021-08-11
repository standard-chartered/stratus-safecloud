import os
from functools import total_ordering

from flask_login import UserMixin
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from wtforms.validators import Email

from db import db

association_table = db.Table('project_user',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class UserModel( db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String(128))
    isAdmin = db.Column(db.Boolean)
    projects = db.relationship("ProjectModel", secondary=association_table, viewonly=True)


class ProjectModel( db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    contacts = db.relationship("ContactModel")
    aws_accounts = db.relationship("AwsAccountModel")
    users = db.relationship("UserModel", secondary=association_table)

class ContactModel(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    email = db.Column(db.String(64))
    parent_id = db.Column(db.Integer, db.ForeignKey('project.id'))

class AwsAccountModel(db.Model, UserMixin):
    __tablename__ = 'aws_account'
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(128))
    env = db.Column(db.String(128))
    account_number = db.Column(db.String(128))
    profile = db.Column(db.String(128))
    parent_id = db.Column(db.Integer, db.ForeignKey('project.id'))
   

def find_user_by_username(username):
    user = UserModel.query.filter_by(username=username).first()
    return user

def find_user_by_id(id):
    user = UserModel.query.filter_by(id=id).first()
    return user

def find_project_by_name(projectname):
    project = ProjectModel.query.filter(ProjectModel.name.like(projectname)).first()
    return project

def find_aws_account_model_by_profile(profile):
    aws_account = AwsAccountModel.query.filter_by(profile=profile).first()
    return aws_account

def get_aws_accounts(aws_accounts):
    accounts = []
    for item in aws_accounts:
        account = AwsAccountModel(env=item['env'],
        account_name=item['account_name'],
        account_number=item['account_number'], 
        profile=item['profile']) 
        accounts.append(account)
    return accounts

def get_contacts(config_contacts):
    contacts = []
    for item in config_contacts:
        contact = ContactModel(name=item['name'], email=item['email']) 
        contacts.append(contact)
    return contacts

def get_authorised_users(authorised_users):
    users = []
    for item in authorised_users:
        user = find_user_by_username(item)
        users.append(user)
    return users

def init_db():
    from werkzeug.security import generate_password_hash
    # insert first admin user
    user_username = 'admin@sc.com'
    user_password = 'password'
    if UserModel.query.first() is None:
        hash_password = generate_password_hash(user_password)
        user1 = UserModel(username=user_username, password=hash_password)
        db.session.add(user1)
        db.session.commit()


if __name__ == "__main__":
    

    # load dotenv in the base root
    APP_ROOT = os.path.dirname(__file__)   # refers to application_top
    dotenv_path = os.path.join(APP_ROOT, '.env')
    
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

    from flask import Flask
    from db import db
    app = Flask(__name__)
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    app.config['SQLALCHEMY_DATABASE_URI']=os.environ['SQLALCHEMY_DATABASE_URI']
    
    db.init_app(app)

    app.app_context().push()

    db.drop_all()
    db.create_all()

    
    project_folder_env_name='SSC_PROJ_DIR'

    project_folder_path = os.environ[project_folder_env_name]

    dir_path = '{}/users.py'.format(project_folder_path)
    import importlib.util
    spec = importlib.util.spec_from_file_location("projectconfig", dir_path)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    

    # # todo need to revise for upcoming migration
    for user in foo.USERS:
        password = foo.USERS[user]['password']
        role = foo.USERS[user]['role']
        isAdmin = False
        if role == 'Administrator':
            isAdmin = True
        dbUser = UserModel(username=user, password=password,isAdmin=isAdmin)
        db.session.add(dbUser)
        db.session.commit()
    

    for dir in os.listdir(path='{}/projects'.format(project_folder_path)):
        if dir != '__pycache__':
            dir_path = '{}/projects/{}/config.py'.format(project_folder_path,dir)
            # insert project entry

            import importlib.util
            spec = importlib.util.spec_from_file_location("projectconfig", dir_path)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)

            project_names = ['Aladdin','Autumn','CardsPal','Liberty','Litmus','Lydia','Phoenix','Smile','SolvKenyaDev','ZodiaMarkets', 'SCVentures']
            project_name = ''
            for name in project_names:
                if name.lower() == dir.lower():
                    project_name = name
            
            if project_name == '':
                project_name = 'SC Ventures'

            
            project = ProjectModel(name=project_name)
            aws_accounts = get_aws_accounts(foo.AWS_ACCOUNTS)
            contacts = get_contacts(foo.CONTACTS)
            authorised_users = get_authorised_users(foo.AUTHORISED_VIEWERS)
            project.aws_accounts.extend(aws_accounts)
            project.contacts.extend(contacts)
            project.users.extend(authorised_users)

            db.session.add(project)
            db.session.commit()
        

    print ("Done!")

