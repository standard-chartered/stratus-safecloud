from tests.test_vamp import client, user_password, user_username, aladdin_user_username, aladdin_user_password
from flask import session, request, g
from db_models import db, UserModel, ProjectModel, ContactModel, AwsAccountModel
from werkzeug.security import generate_password_hash
login_path = '/login'

# test access to SCV Tooling PAge
def test_login_user(client):
    client.get(login_path)
    client.post(login_path, data = dict(email=aladdin_user_username,password=aladdin_user_password,csrf_token=g.csrf_token), follow_redirects=True)
    
    rv = client.get('/aladdin', follow_redirects=True)
    assert b'You are not authorized to view this page'  not in rv.data
    

 # add new user and check whether he has permissions to view aladdin

def test_admin_user(client):
    client.get(login_path)
    password = 'password'
    username = 'admin@sc.com'
    hash_password = generate_password_hash(password)
    new_user = UserModel(username=username,password=hash_password,isAdmin=True)
    db.session.add(new_user)
    db.session.commit()

    new_contact1 = ContactModel(name='contact1', email='contact1@sc.com')
    new_contact2 = ContactModel(name='contact2', email='contact2@sc.com')

    new_account1 = AwsAccountModel(account_name='Aladdin Tooling', env='tooling', account_number='991937040196', profile='AladdinTooling')
    new_account2 = AwsAccountModel(account_name='Aladdin Dev', env='dev', account_number='235410405967', profile='AladdinDev')
    new_account3 = AwsAccountModel(account_name='Aladdin Pre-Prod', env='preprod', account_number='310234620425', profile='AladdinPreProd')

    new_project = ProjectModel(name='Aladdin') 
    new_project.contacts.append(new_contact1)
    new_project.contacts.append(new_contact2)
    new_project.aws_accounts.append(new_account1)
    new_project.aws_accounts.append(new_account2)
    new_project.aws_accounts.append(new_account3)
    
    db.session.add(new_project)
    db.session.commit()

    client.post(login_path, data = dict(email=username, password=password,csrf_token=g.csrf_token), follow_redirects=True)
    rv = client.get('/projects/aladdin', follow_redirects=True)
    assert b'You are not authorized to view this page'  not in rv.data
    assert b'Aladdin - Project Description' in rv.data
    assert b'Contact' in rv.data
    assert b'contact1' in rv.data
    assert b'contact2' in rv.data
    assert b'contact1@sc.com' in rv.data
    assert b'contact2@sc.com' in rv.data


    assert b'AWS Platform Security' in rv.data

    assert b'Aladdin Tooling' in rv.data
    assert b'Aladdin Dev' in rv.data
    assert b'Aladdin Pre-Prod' in rv.data

    assert b'AWS Resources' in rv.data

