from tests.test_vamp import client, user_password, user_username
from flask import session, request, g

login_path = '/login'
# test redirect when not sign in
def test_home_redirect(client):
    rv = client.get('/', follow_redirects=True)
    assert b'Sign In' in rv.data

# test login page present
def test_login_page(client):
    rv = client.get(login_path)
    assert b'Sign In' in rv.data

# test login to overview page
def test_login_user(client):
    client.get(login_path)
    rv = client.post(login_path, data = dict(email=user_username,password=user_password,csrf_token=g.csrf_token), follow_redirects=True)
    # print(rv.data)
    assert b'Venture projects' in rv.data
    
# test login unsuccessful
def test_invalid_login(client):
    client.get(login_path)
    dummypwd  = 'dumpwd'
    rv = client.post(login_path, data = dict(email=user_username,password=dummypwd,csrf_token=g.csrf_token), follow_redirects=True)
    print(rv.data)
    assert b'Invalid username or password' in rv.data
  