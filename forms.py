from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, HiddenField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo

import os
import flask_login
import importlib
from db_models import ProjectModel, UserModel, find_user_by_username


def get_projects(project_dir):

    projects = ProjectModel.query.all()
    projects = list(map(get_project_name, projects))

    if projects:
        projects = ['Admin'] + projects
    else:
        projects = {'Admin'}
    return projects

def get_project_name(project):
     return project.name

# todo to change this to db
def get_accounts(project):
    module = 'projects.' + project.lower() + '.config'
    config_data = importlib.import_module(module)
    accounts = [d['account_name'] for d in config_data.AWS_ACCOUNTS]
    return accounts

class LoginForm(FlaskForm):
    email = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')

class DeleteUserForm(FlaskForm):
    email = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Delete')

class DeleteProjectForm(FlaskForm):
    project = StringField('Project Name', validators=[DataRequired()])
    project_confirm = StringField('Please re-enter project name to delete',
                                  validators=[DataRequired(),
                                  EqualTo('project', message='Project names must match to delete')])
    submit = SubmitField('Delete')


class RegistrationForm(FlaskForm):
    available_projects = get_projects('projects')
    projects = SelectField('Project', choices=available_projects, validators=[DataRequired()])
    email = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password', message='Passwords much match')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = find_user_by_username(email.data)
        if user is not None:
            print('User exists already !')
            raise ValidationError('User exists - please use a different email address.')
            
class AddProjectForm(FlaskForm):
    valid_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'ap-southeast-1', 'eu-central-1']
    project = StringField('Project Name', validators=[DataRequired()])
    dev_account_name = StringField('Dev Account Name', validators=[DataRequired()])
    dev_account_number = StringField('Dev Account Number', validators=[DataRequired()])
    dev_account_region = SelectField('Region', choices=valid_regions, validators=[DataRequired()], default='ap-southeast-1')
    dev_profile_name = StringField('Dev Profile Name (no spaces)', validators=[DataRequired()])
    dev_access_key = StringField('Dev Access Key', validators=[DataRequired()])
    dev_secret_access_key = PasswordField('Dev Secret Access Key', validators=[DataRequired()])
    
    tooling_account_name = StringField('Tooling Account Name')
    tooling_account_number = StringField('Tooling Account Number')
    tooling_account_region = SelectField('Region', choices=valid_regions, validators=[DataRequired()], default='ap-southeast-1')
    tooling_profile_name = StringField('Tooling Profile Name (no spaces)')
    tooling_access_key = StringField('Tooling Access Key')
    tooling_secret_access_key = PasswordField('Tooling Secret Access Key')
    
    pre_prod_account_name = StringField('PreProd Account Name')
    pre_prod_account_number = StringField('PreProd Account Number')
    pre_prod_account_region = SelectField('Region', choices=valid_regions, validators=[DataRequired()], default='ap-southeast-1')
    pre_prod_profile_name = StringField('PreProd Profile Name (no spaces)')
    pre_prod_access_key = StringField('PreProd Access Key')
    pre_prod_secret_access_key = PasswordField('PreProd Secret Access Key')    
    submit = SubmitField('Add Project')

    def validate_project(self, project):
        available_projects = get_projects('projects')
        if project._value() in available_projects:
            print('Project exists already !')
            raise ValidationError('Project exists - please use a different project name.')

class DeleteAccountForm(FlaskForm):
    valid_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'ap-southeast-1', 'eu-central-1']
    available_projects = get_projects('projects')
    if ('Admin' in available_projects):
        available_projects.remove('Admin')
    project = SelectField('Select the project you want to remove an account from:', choices=available_projects, validators=[DataRequired()])
    account_name = StringField('Account Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    profile_name = StringField('Profile Name', validators=[DataRequired()])
    submit = SubmitField('Delete Account')

class AddAccountForm(FlaskForm):
    valid_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'ap-southeast-1', 'eu-central-1']
    available_projects = get_projects('projects')
    if ('Admin' in available_projects):
        available_projects.remove('Admin')
    project = SelectField('Select the project you want to add an account to:', choices=available_projects, validators=[DataRequired()])
    account_env = StringField('Environment Name (e.g. dev, test, uat, preprod, prod, etc.)', validators=[DataRequired()])
    account_name = StringField('Account Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    account_region = SelectField('Region', choices=valid_regions, validators=[DataRequired()], default='ap-southeast-1')
    profile_name = StringField('Profile Name (no spaces)', validators=[DataRequired()])
    access_key = StringField('Access Key', validators=[DataRequired()])
    secret_access_key = PasswordField('Secret Access Key', validators=[DataRequired()])    
    submit = SubmitField('Add Account')


