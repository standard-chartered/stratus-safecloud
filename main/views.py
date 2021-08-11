import fileinput
from functools import total_ordering
import importlib
import json
import os
import pprint as pp
from datetime import datetime, date

from io import StringIO
from pathlib import Path
import csv
from collections import OrderedDict

import flask_login

import yaml
from db import db
from db_models import AwsAccountModel, ProjectModel, UserModel, find_project_by_name, find_user_by_id, find_user_by_username
from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for, make_response)
from flask.helpers import total_seconds
from forms import (AddAccountForm, AddProjectForm, ChangePasswordForm,
                   DeleteAccountForm, DeleteProjectForm, DeleteUserForm,
                   LoginForm, RegistrationForm)
from util.aws_config import ConfigData
from util.aws_resources import ResourceData
from util.aws_security import SecurityData
from util.aws_trusted_advisor import TrustedAdvisorData
from util.ec2_instances import EC2InstanceData
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.urls import url_parse

main = Blueprint("main", __name__,
                 template_folder="templates",
                 static_folder='static',
                 static_url_path='/main/static')

main_home_path = 'main.home'
main_show_users = 'main.show_users'
csv_content_type = "text/csv; charset=utf-8"
date_format = "%b-%d-%Y"
attachment_file_prefix =  "attachment; filename="
json_content_type = 'application/json; charset=utf-8'

def update_aws_files(account_info):
    home = str(Path.home())
    config_file = home + '/.aws/config'
    credentials_file = home + '/.aws/credentials'
    for account in account_info:
        profile_string = '[profile '+ account['profile'] + ']'
        # Check that the entry doesn't exist - can't have repeats
        with open(config_file) as f:
            if  profile_string in f.read():
                continue
        with open(config_file, 'a') as f:
            print(file=f)
            print(profile_string, file=f)
            print('region=' + account['region'], file=f)
            print('output=json', file=f)
        with open(credentials_file, 'a') as f:
            print(file=f)
            print('[' + account['profile'] + ']', file=f)
            print('aws_access_key_id = ' + account['access_key'], file=f)
            print('aws_secret_access_key = ' + account['secret_access_key'], file=f)
        
    return

def update_skew_file(account_info):
    if 'SKEW_CONFIG' in os.environ:
        skew_file = os.environ['SKEW_CONFIG']
    else:
        skew_file = '.skew'

    for account in account_info:
        account_number = str(account['account_number'])
        # Check that the entry doesn't exist - can't have repeats
        with open(skew_file) as f:
            if  account_number in f.read():
                continue
        with open(skew_file, 'a') as f:
            print('    "'+ account_number + '":', file=f)
            print('      profile: ' + account['profile'], file=f)
    return

def clean_up_skew_file(accounts):
    if 'SKEW_CONFIG' in os.environ:
        skew_file = os.environ['SKEW_CONFIG']
    else:
        skew_file = '.skew'
    
    with open(skew_file, 'r') as f:
        lines = f.readlines()
    for account in accounts:
        search_line = account
        for i, line in enumerate(lines):
            if search_line in line:
                del lines[i:i+2]
                break
    with open(skew_file, 'w') as f:
        f.writelines(lines)
    return

def get_account_info_for_project(project):
    account_info = []
    
    return account_info

def clean_up_aws_config_file(profiles):
    home = str(Path.home())
    config_file = home + '/.aws/config'
    with open(config_file, 'r') as f:
        lines = f.readlines()
    for profile in profiles:
        search_line = '[profile ' + profile + ']'
        for i, line in enumerate(lines):
            if search_line in line:
                if i == 0:
                    del lines[i:i+4]
                else:
                    del lines[i-1:i+3]
                break
    with open(config_file, 'w') as f:
        f.writelines(lines)
    return

                      
def clean_up_aws_credentials_file(profiles):
    home = str(Path.home())
    config_file = home + '/.aws/credentials'
    with open(config_file, 'r') as f:
        lines = f.readlines()
    for profile in profiles:
        search_line = '[' + profile + ']'
        for i, line in enumerate(lines):
            if search_line in line:
                if i == 0:
                    del lines[i:i+4]
                else:
                    del lines[i-1:i+3]
                break
    with open(config_file, 'w') as f:
        f.writelines(lines)
    return

                     
@main.route("/")
@flask_login.login_required
def home():
    return render_template("main.html")   

    
@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.email.data.lower()
        existingUser = find_user_by_username(username)
        
        if existingUser is not None:
            my_hash = existingUser.password
            if check_password_hash(my_hash, form.password.data):
                flask_login.login_user(existingUser, remember=False)
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for(main_home_path)
                return redirect(next_page)

        flash('Invalid username or password')
        
    return render_template('login.html', title='Sign In', form=form)
    
@main.route('/add_user', methods=['GET', 'POST'])
@flask_login.login_required
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.email.data.lower()
        existingUser = find_user_by_username(username)
        
        if existingUser is not None:
            flash('User {} already exists'.format(username))
            next_page = url_for(main_home_path)
            return redirect(next_page)
        else:
            my_hash = generate_password_hash(form.password.data)
            project = form.projects.data
            newUser = UserModel(username=username, password=my_hash)
            

            if project == 'Admin':
                newUser.isAdmin = True
                
            else:
                project = find_project_by_name(project)
                project.users.append(newUser)
                db.session.add(project)

            db.session.add(newUser)
            db.session.commit()

            flash('User {} was added successfully'.format(username))
            next_page = url_for(main_show_users)
            return redirect(next_page)           
    return render_template('add_user.html', title='Register', form=form)


@main.route('/change_password', methods=['GET', 'POST'])
@flask_login.login_required
def change_password():
    print(session['_user_id'])
    username = session['_user_id']
    form = ChangePasswordForm()
    if form.validate_on_submit():
        existing_user = find_user_by_id(username)
        
        if existing_user is None:
            flash('User {} does not exist'.format(username))
            next_page = url_for(main_home_path)
            return redirect(next_page)
        else:
            old_hash = existing_user.password
            if check_password_hash(old_hash, form.old_password.data):
                new_hash = generate_password_hash(form.new_password.data)
                existing_user.password = new_hash
                db.session.add(existing_user)
                db.session.commit()
                flash('Password change for user {} was completed successfully'.format(username))
                next_page = url_for(main_home_path)
                return redirect(next_page)
            else:
                flash('Incorrect password entered for user {}'.format(username))
                next_page = url_for(main_home_path)
                return redirect(next_page)                
    else:
        print("Form not validated")          
    return render_template('change_password.html', title='Change Password', form=form)


@main.route('/delete_user', methods=['GET', 'POST'])
@flask_login.login_required
def delete_user():
    form = DeleteUserForm()
    if form.validate_on_submit():
        username = form.email.data
        print('hello'+username)
        existing_user = find_user_by_username(username)
        print(existing_user)
        
        if existing_user is not None:
            db.session.delete(existing_user)
            db.session.commit()
            flash('User {} was deleted successfully'.format(username))
            next_page = url_for(main_show_users)
            return redirect(next_page)           
        else:
            flash('User {} does not exist'.format(form.username.data))
            next_page = url_for(main_show_users)
            return redirect(next_page)           
    return render_template('delete_user.html', title='Delete User', form=form)

@main.route('/show_users', methods=['GET', 'POST'])
@flask_login.login_required
def show_users():
    users = UserModel.query.all()
    return render_template('show_users.html', users=users)


@main.route('/add_project', methods=['GET', 'POST'])
@flask_login.login_required
def add_new_project():
    form = AddProjectForm()
    if form.validate_on_submit():
        project = form.project.data
        project_model = find_project_by_name(project)
        if project_model is not None:
            flash('Project {} already exists'.format(project))
            next_page = url_for(main_home_path)
            return redirect(next_page)
        else:
            project_model = ProjectModel(name=project)
            
            account_info = []
            # Dev Environment details
            tmp = {}
            tmp['env'] = 'dev'
            tmp['account_name'] = form.dev_account_name.data
            tmp['account_number'] = form.dev_account_number.data
            tmp['region'] = form.dev_account_region.data
            tmp['profile'] = form.dev_profile_name.data
            tmp['access_key'] = form.dev_access_key.data
            tmp['secret_access_key'] = form.dev_secret_access_key.data
            account_info.append(tmp)

            dev_aws_account = AwsAccountModel(
                account_name=form.dev_account_name.data,
                env='dev',
                account_number=form.dev_account_number.data,
                profile=form.dev_profile_name.data
            )

            project_model.aws_accounts.append(dev_aws_account)
        
            # Tooling account details - only add these if all fields have data
            if (len(form.tooling_account_name.data) > 0 and
                len(form.tooling_account_number.data) > 0 and
                len(form.tooling_profile_name.data) > 0 and
                len(form.tooling_access_key.data) > 0 and
                len(form.tooling_secret_access_key.data) > 0):
                tmp = {}
                tmp['env'] = 'tooling'
                tmp['account_name'] = form.tooling_account_name.data
                tmp['account_number'] = form.tooling_account_number.data
                tmp['region'] = form.tooling_account_region.data
                tmp['profile'] = form.tooling_profile_name.data
                tmp['access_key'] = form.tooling_access_key.data
                tmp['secret_access_key'] = form.tooling_secret_access_key.data
                tooling_aws_account = AwsAccountModel(
                account_name=form.tooling_account_name.data,
                env='tooling',
                account_number=form.tooling_account_number.data,
                profile=form.tooling_profile_name.data
                )
                project_model.aws_accounts.append(tooling_aws_account)
                account_info.append(tmp)
        
            # PreProd account details - only add these if all fields have data
            if (len(form.pre_prod_account_name.data) > 0 and
                len(form.pre_prod_account_number.data) > 0 and
                len(form.pre_prod_profile_name.data) > 0 and
                len(form.pre_prod_access_key.data) > 0 and
                len(form.pre_prod_secret_access_key.data) > 0):
                tmp = {}
                tmp['env'] = 'preprod'
                tmp['account_name'] = form.pre_prod_account_name.data
                tmp['account_number'] = form.pre_prod_account_number.data
                tmp['region'] = form.pre_prod_account_region.data
                tmp['profile'] = form.pre_prod_profile_name.data
                tmp['access_key'] = form.pre_prod_access_key.data
                tmp['secret_access_key'] = form.pre_prod_secret_access_key.data
                pre_prod_aws_account = AwsAccountModel(
                account_name=form.pre_prod_account_name.data,
                env='pre_prod',
                account_number=form.pre_prod_account_number.data,
                profile=form.pre_prod_profile_name.data
                )
                project_model.aws_accounts.append(pre_prod_aws_account)
                account_info.append(tmp)

            db.session.add(project_model)
            db.session.commit()

            update_aws_files(account_info)
            update_skew_file(account_info) 
            flash('Project {} was added successfully'.format(project))
            next_page = url_for(main_home_path)
        return redirect(next_page)           
    return render_template('add_project.html', title='Add Project', form=form)


@main.route('/delete_project', methods=['GET', 'POST'])
@flask_login.login_required
def delete_a_project():
    form = DeleteProjectForm()
    if form.validate_on_submit():
        project = form.project.data
        project_confirm = form.project_confirm.data
        project_model = ProjectModel.query.filter_by(name=project).first()
        
        if project_model is not None:
            
            profiles = [d.profile for d in project_model.aws_accounts]
            accounts = [d.account_number for d in project_model.aws_accounts]
            print('Deleting project:', project)              
            # Remove entries from the ~/.aws.config and ~/.aws/credentials files
            clean_up_aws_config_file(profiles)
            clean_up_aws_credentials_file(profiles)
            clean_up_skew_file(accounts)
            flash('Project {} was deleted successfully'.format(project))
            next_page = url_for(main_home_path)
            db.session.delete(project_model)
            db.session.commit()
            return redirect(next_page)           
        else:
            flash('Project {} does not exist'.format(form.project.data))
            next_page = url_for(main_home_path)
            return redirect(next_page)           
    return render_template('delete_project.html', title='Delete Project', form=form)


@main.route('/add_account', methods=['GET', 'POST'])
@flask_login.login_required
def add_new_account():
    form = AddAccountForm()
    if form.validate_on_submit():
        project = form.project.data
        project_model = find_project_by_name(project)
        if project_model is None:
            flash('Project {} does not exist'.format(project))
            next_page = url_for(main_home_path)
            return redirect(next_page)
        else:
            account_info = []
            # New Account details
            tmp = {}
            tmp['env'] = form.account_env.data
            tmp['account_name'] = form.account_name.data
            tmp['account_number'] = form.account_number.data
            tmp['region'] = form.account_region.data
            tmp['profile'] = form.profile_name.data
            tmp['access_key'] = form.access_key.data
            tmp['secret_access_key'] = form.secret_access_key.data
            account_info.append(tmp)        
            update_aws_files(account_info)
            update_skew_file(account_info)
            aws_account = AwsAccountModel(
                account_name=form.account_name.data,
                env=form.account_env.data,
                account_number=form.account_number.data,
                profile=form.profile_name.data
            )
            project_model.aws_accounts.append(aws_account)
            db.session.add(project_model)
            db.session.commit()
            
            # if success:
            flash('Account {} was added successfully to project {}'.format(form.account_name.data, project))
            # else:
            #     flash('Account {} already exists in project {}'.format(form.account_name.data, project))
            next_page = url_for(main_home_path)
        return redirect(next_page)           
    return render_template('add_account.html', title='Add Account', form=form)


@main.route('/delete_account', methods=['GET', 'POST'])
@flask_login.login_required
def delete_an_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        project = form.project.data
        project_model = find_project_by_name(project)
        if project_model is not None:
            account = form.account_name.data
            account_name = form.account_name.data
            account_number = form.account_number.data
            profile = form.profile_name.data
            profiles = [profile]
            print('Deleting account:', account)
            is_success = False
            for account in project_model.aws_accounts:
                if account.account_name == account_name and account.profile == profile and account.account_number == account_number :
                    db.session.delete(account)
                    db.session.commit()
                    is_success = True
                    break
            
            if is_success:            
                # Remove entries from the ~/.aws.config and ~/.aws/credentials files
                clean_up_aws_config_file(profiles)
                clean_up_aws_credentials_file(profiles)
                clean_up_skew_file([account_number])
                flash('Account {} was deleted successfully'.format(account))
            else:
                flash('Account {} does not exist in project {}'.format(account, project))
            next_page = url_for(main_home_path)
            return redirect(next_page)           
        else:
            flash('Account {} does not exist'.format(form.account_name.data))
            next_page = url_for(main_home_path)
            return redirect(next_page)           
    return render_template('delete_account.html', title='Delete Account', form=form)


@main.route("/work-in-progress")
@flask_login.login_required
def work_in_progress():
    return render_template("work-in-progress.html")

@main.route("/about")
@flask_login.login_required
def about():
    return render_template("about.html")

@main.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect('/login')

@main.route("/projects/<string:project_name>")    
@flask_login.login_required
def project_main_view(project_name):
    
    project = find_project_by_name(project_name)
    scores = {}
    ta_results = {}
    config_data = {}
    ec2_data = {}

    
    ta = TrustedAdvisorData()
    sd = SecurityData()
    config = ConfigData()
    ec2 = EC2InstanceData()

    for item in project.aws_accounts:
        env = item.env
        profile = item.profile
        scores[env] = sd.get_scores(profile)
        ta_results[env] = ta.get_results(profile)
        config_data[env] = config.get_data(profile)
        ec2_data[env] = ec2.get_data(profile)

    stuff = []
    for account in config_data:
        if config_data[account]['data']:
            for region in config_data[account]['data']:
                if len(config_data[account]['data'][region]['non_compliant']) > 0:
                    for rule in config_data[account]['data'][region]['non_compliant']:
                        tmp = {}
                        #print(region, rule, config_data[account]['account_name'])
                        tmp['rule_name'] = rule
                        tmp['resources'] = config_data[account]['data'][region]['non_compliant'][rule]
                        tmp['region'] = region
                        tmp['account'] = account
                        tmp['account_name'] = config_data[account]['account_name']
                        stuff.append(tmp)
    
    last_update = scores[list(scores)[0]]['last_update']
    return render_template("project_main.html",project=project, 
    scores=scores, ta_results=ta_results, config_data=stuff, ec2_data=ec2_data, last_update=last_update)


@main.route("/projects/<string:project_name>/aws-security/<string:environment>", methods=['GET'])
@flask_login.login_required
def aws_security_details(project_name, environment):

    from db_models import find_project_by_name
    project = find_project_by_name(project_name)

    check_access(project)

    from util.aws_security import SecurityData
    sd = SecurityData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == environment:
            profile = item.profile
            account_name = item.account_name
            account_number = item.account_number
            break
        else:
            continue
    report = sd.get_data(profile)
    data = report['data']
    if data:
        results = {}
        standards = data.keys()
        for standard in standards:
            results[standard] = []
            aws = data[standard]
            for benchmark in aws:
                for item in aws[benchmark]:
                    results[standard].append(item)
    else:
        results = {}
    return render_template("project-details.html",
                           results=results,
                           project=project_name,
                           account=account_name,
                           account_number=account_number)


@main.route("/projects/<string:project_name>/resources/<environment>", methods=['GET'])
@flask_login.login_required
def aws_resources(project_name,environment):
    project = find_project_by_name(project_name)
    check_access(project)

    resources = ResourceData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == environment:
            profile = item.profile
            account_name = item.account_name
            account_number = item.account_number
            break
        else:
            continue
    report = resources.get_data(profile)
    data = report['data']
    if data:
        results = {}
        services = data[account_number].keys()
        for service in services:
            results[service] = data[account_number][service]
    else:
        results = {}
    return render_template("project-resources.html",
                           results=results,
                           project=project_name,
                           account=account_name,
                           account_number=account_number,
                           env=environment)



def check_access(project):
    if not flask_login.current_user.isAdmin and flask_login.current_user.username not in project.users:
        return redirect('/not_authorized')

    
@main.route('/projects/<string:project_name>/not_authorized')
def not_auth(project_name):
    return render_template('not_authorized.html', project=project_name)

@main.route("/api/v1.1/<project_name>/aws-accounts", methods=['GET'])
@flask_login.login_required
def aws_accounts(project_name):
    project = find_project_by_name(project_name)
    check_access(project)

    json_data = json.dumps(project.aws_accounts, indent=4, sort_keys=True)
    
    return json_data, 200, {
        'Content-Type': json_cotent_type
    }

def json_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()
    
@main.route("/api/v1.1/<project_name>/resources/<environment>", methods=['GET'])
@flask_login.login_required
def aws_resources_api(project_name,environment):
    
    project = find_project_by_name(project_name)
    check_access(project)
    resources = ResourceData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == environment:
            profile = item.profile
            break
        else:
            continue
    report = resources.get_data(profile)
    data = report['data']
    json_data = json.dumps(data, default=json_converter, indent=4, sort_keys=True)
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/resources/<environment>/<service>", methods=['GET'])
@flask_login.login_required
def aws_service_api(project_name,environment, service):
    project = find_project_by_name(project_name)
    check_access(project)
    resources = ResourceData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == environment:
            profile = item.profile
            account_name = item.account_name
            account_number = item.account_number
            break
        else:
            continue
    report = resources.get_data(profile)
    data = report['data']
    service = data[account_number][service]
    json_data = json.dumps(service, default=json_converter, indent=4, sort_keys=True)
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/resources/<environment>/<service>/<resource>", methods=['GET'])
@flask_login.login_required
def aws_service_resource_api(project_name,environment, service, resource):
    project = find_project_by_name(project_name)
    check_access(project)
    resources = ResourceData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == environment:
            profile = item.profile
            account_name = item.account_name
            account_number = item.account_number
            break
        else:
            continue
    report = resources.get_data(profile)
    data = report['data']
    service = data[account_number][service][resource]
    json_data = json.dumps(service, default=json_converter, indent=4, sort_keys=True)
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-security/<environment>", methods=['GET'])
@flask_login.login_required
def aws_security_api(project_name,environment):
    project = find_project_by_name(project_name)
    check_access(project)
    sd = SecurityData()
    profile = ""
    for item in project.aws_accounts:
        if item['env'] == environment:
            profile = item['profile']
            account_name = item['account_name']
            account_number = item['account_number']
            break
        else:
            continue
    report = sd.get_data(profile)
    data = report['data']
    if data:
        results = {}
        standards = data.keys()
        for standard in standards:
            results[standard] = []
            aws = data[standard]
            for benchmark in aws:
                for item in aws[benchmark]:
                    results[standard].append(item)
        json_data = json.dumps(results, indent=4, sort_keys=True)        
    else:
        json_data = {}
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-trusted-advisor/<account>", methods=['GET'])
@flask_login.login_required
def aws_trusted_advisor_results_api(project_name,account):
    project = find_project_by_name(project_name)
    check_access(project)
    ta = TrustedAdvisorData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ta.get_results(profile)
    if 'data' in report:
        data = report['data']
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-trusted-advisor/<account>/details", methods=['GET'])
@flask_login.login_required
def aws_trusted_advisor_details_api(project_name,account):
    project = find_project_by_name(project_name)
    check_access(project)
    ta = TrustedAdvisorData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ta.get_data(profile)
    if 'data' in report:
        data = report['data']
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-trusted-advisor/<account>/status/<status>", methods=['GET'])
@flask_login.login_required
def aws_trusted_advisor_status_api(project_name,account, status):
    project = find_project_by_name(project_name)
    check_access(project)
    ta = TrustedAdvisorData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ta.get_data(profile)
    if 'data' in report:
        data = report['data']
        by_status = [d for d in data if d['result']['status'] == status]
    else:
        by_status = {}
    json_data = json.dumps(by_status, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-trusted-advisor/<account>/category/<category>", methods=['GET'])
@flask_login.login_required
def aws_trusted_advisor_category_api(project_name,account, category):
    project = find_project_by_name(project_name)
    check_access(project)
    ta = TrustedAdvisorData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ta.get_data(profile)
    if 'data' in report:
        data = report['data']
        by_status = [d for d in data if d['category'] == category]
    else:
        by_status = {}
    json_data = json.dumps(by_status, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-trusted-advisor/<account>/category/<category>/<status>", methods=['GET'])
@flask_login.login_required
def aws_trusted_advisor_category_status_api(project_name,account, category, status):
    project = find_project_by_name(project_name)
    check_access(project)
    ta = TrustedAdvisorData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ta.get_data(profile)
    if 'data' in report:
        data = report['data']
        categories = [d for d in data if d['category'] == category]
        category_status = [d for d in categories if d['result']['status'] == status]
    else:
        category_status = {}
    json_data = json.dumps(category_status, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-config/<account>", methods=['GET'])
@flask_login.login_required
def aws_config_results_api(project_name,account):
    project = find_project_by_name(project_name)
    check_access(project)
    config = ConfigData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = config.get_data(profile)
    if 'data' in report:
        data = report['data']
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/api/v1.1/<project_name>/aws-config/<account>/<region>/<compliance>", methods=['GET'])
@flask_login.login_required
def aws_config_compliance_results_api(project_name,account, region, compliance):
    project = find_project_by_name(project_name)
    check_access(project)
    config = ConfigData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = config.get_data(profile)
    if 'data' in report:
        if compliance == 'non_compliant':
            data = report['data'][region]['non_compliant']
        else:
            data = report['data'][region]['compliant']
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
    
@main.route("/api/v1.1/<project_name>/aws-config/<account>/<region>/non_compliant/<rule_name>", methods=['GET'])
@flask_login.login_required
def aws_config_non_compliant_results_api(project_name,account, region, rule_name):
    project = find_project_by_name(project_name)
    check_access(project)
    config = ConfigData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = config.get_data(profile)
    if 'data' in report:
        data = report['data'][region]['non_compliant'][rule_name]
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }


@main.route("/api/v1.1/<project_name>/ec2-instances/<account>/details", methods=['GET'])
@flask_login.login_required
def ec2_details_api(project_name,account):
    project = find_project_by_name(project_name)
    check_access(project)
    ec2 = EC2InstanceData()
    profile = ""
    for item in project.aws_accounts:
        if item.env == account:
            profile = item.profile
            break
        else:
            continue
    report = ec2.get_data(profile)
    if 'data' in report:
        data = report['data']
    else:
        data = {}
    json_data = json.dumps(data, indent=4, sort_keys=True)        
    return json_data, 200, {
        'Content-Type': json_content_type
    
    }
    
@main.route("/<project_name>/config.csv", methods=['GET'])
@flask_login.login_required
def config_report_csv(project_name):
    ta = TrustedAdvisorData()
    config = ConfigData()
    project = find_project_by_name(project_name)
    check_access(project)
    
    
    ta_results = {}
    config_data = {}
    for item in project.aws_accounts:
        env = item.env
        profile = item.profile
        ta_results[env] = ta.get_results(profile)
        config_data[env] = config.get_data(profile)

    stuff = []
    for account in config_data:
        if config_data[account]['data']:
            for region in config_data[account]['data']:
                if len(config_data[account]['data'][region]['non_compliant']) > 0:
                    for rule in config_data[account]['data'][region]['non_compliant']:
                        tmp = {}
                        #print(region, rule, config_data[account]['account_name'])
                        tmp['rule_name'] = rule
                        tmp['resources'] = config_data[account]['data'][region]['non_compliant'][rule]
                        tmp['region'] = region
                        tmp['account'] = account
                        tmp['account_name'] = config_data[account]['account_name']
                        stuff.append(tmp)
    #pp.pprint(stuff)
    today = date.today()
    
    content_disposition_string = attachment_file_prefix + project.name + "-aws-config-non-compliance-report-" + today.strftime(date_format) + ".csv"
    csv_data = []
    for item in stuff:        
        for resource in item['resources']:
            cc = OrderedDict()
            cc['Account Name'] = item['account_name']
            cc['Region'] = item['region']
            cc['Rule Name'] = item['rule_name']
            cc['Non-Compliant Resource Id'] = resource['resource_id']
            cc['Resource Type'] = resource['resource_type']
            csv_data.append(cc)
    string_io = StringIO()
    headers = csv_data[0].keys()
    writer = csv.DictWriter(string_io, fieldnames=headers)
    writer.writeheader()
    writer.writerows(csv_data)
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = content_disposition_string
    output.headers["Content-type"] = csv_content_type
    return output

        
@main.route("/<project_name>/trusted-advisor.csv", methods=['GET'])
@flask_login.login_required
def ta_report_csv(project_name):
    ta = TrustedAdvisorData()
    project = find_project_by_name(project_name)
    check_access(project)
    
    ta_data = {}
    config_data = {}
    account_data = {}
    for item in project.aws_accounts:
        env = item.env
        profile = item.profile
        ta_data[env] = ta.get_data(profile)
        account_data[env] = {'name': item.account_name, 'number': item.account_number}

    stuff = []
    for env in ta_data:
        account_name = account_data[env]['name']
        account_number = account_data[env]['number']
        if ta_data[env]['data']:
            for check in ta_data[env]['data']:
                if 'flaggedResources' in check['result']:
                    if check['result']['flaggedResources']:
                        for resource in check['result']['flaggedResources']:
                            tmp = {}
                            tmp['account_name'] = account_name
                            tmp['account_number'] = account_number
                            tmp['category'] = check['category']
                            tmp['name'] = check['name']
                            tmp['suppressed'] = resource['isSuppressed']
                            if 'region' in resource:
                                tmp['region'] = resource['region']
                            else:
                                tmp['region'] = 'global'
                            tmp['resourceId'] = resource['resourceId']
                            tmp['status'] = resource['status']
                            if tmp['status'] == 'error':
                                tmp['colour'] = 'Red'
                            elif tmp['status'] == 'warning':
                                tmp['colour'] = 'Yellow'
                            elif tmp['status'] == 'ok':
                                tmp['colour'] = 'Green'
                            else:
                                tmp['colour'] = 'Blue'
                            #print(account_name, account_number, 
                            #      check['category'], check['name'],
                            #      resource['resourceId'], resource['status'])
                            stuff.append(tmp)
                else:
                    print(account_name, account_number, check['category'], check['name'], check['result']['status'])
    #pp.pprint(stuff)
    today = date.today()
    content_disposition_string = attachment_file_prefix + project.name + "-aws-trusted-advisor-non-compliance-report-" + today.strftime(date_format) + ".csv"
    csv_data = []
    for item in stuff:
        cc = OrderedDict()
        cc['Account Name'] = item['account_name']
        cc['Account Number'] = item['account_number']
        cc['Category'] = item['category']
        cc['Check Name'] = item['name']
        cc['Region'] = item['region']
        cc['Resource Id'] = item['resourceId']
        cc['Suppressed'] = item['suppressed']
        cc['Status'] = item['colour']
        csv_data.append(cc)
    string_io = StringIO()
    headers = csv_data[0].keys()
    writer = csv.DictWriter(string_io, fieldnames=headers)
    writer.writeheader()
    writer.writerows(csv_data)
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = content_disposition_string
    output.headers["Content-type"] = csv_content_type
    return output
        
    
@main.route("/<project_name>/ec2-instances.csv", methods=['GET'])
@flask_login.login_required
def ec2_report_csv(project_name):
    ec2 = EC2InstanceData()
    project = find_project_by_name(project_name)
    check_access(project)
    #pp.pprint(accounts)
    ec2_data = {}
    config_data = {}
    account_data = {}
    for item in project.aws_accounts:
        env = item.env
        profile = item.profile
        ec2_data[env] = ec2.get_data(profile)
        account_data[env] = {'name': item.account_name, 'number': item.account_number}

    stuff = []
    for env in ec2_data:
        account_name = account_data[env]['name']
        account_number = account_data[env]['number']
        if ec2_data[env]['data']:
            for region in ec2_data[env]['data']:
                if len(ec2_data[env]['data'][region]['instances']) > 0:
                    for instance in ec2_data[env]['data'][region]['instances']:
                        tmp = {}
                        tmp['account_name'] = account_name
                        tmp['account_number'] = account_number
                        tmp['region'] = region
                        tmp['instance_type'] = instance['instance_type']
                        tmp['instance_id'] = instance['instance_id']
                        if 'private_ip' in instance:
                            tmp['private_ip'] = instance['private_ip']
                        else:
                            tmp['private_ip'] = 'Unknown'
                        if 'public_ip' in instance:
                            tmp['public_ip'] = instance['public_ip']
                        else:
                            tmp['public_ip'] = 'Unknown'
                        tmp['state'] = instance['state']
                        tmp['ssm_managed'] = instance['ssm_managed']
                        stuff.append(tmp)
                        pp.pprint(tmp)
    today = date.today()
    
    content_disposition_string = attachment_file_prefix + project.name + "-aws-ec2-instance-report-" + today.strftime(date_format) + ".csv"
    csv_data = []
    for item in stuff:
        cc = OrderedDict()
        cc['Account Name'] = item['account_name']
        cc['Account Number'] = item['account_number']
        cc['Region'] = item['region']
        cc['Instance Type'] = item['instance_type']
        cc['Instance Id'] = item['instance_id']
        cc['Private Ip'] = item['private_ip']
        cc['Public Ip'] = item['public_ip']
        cc['State'] = item['state']
        cc['SSM Managed'] = item['ssm_managed']
        csv_data.append(cc)
    string_io = StringIO()
    if csv_data:
        headers = csv_data[0].keys()
    else:
        headers = ['Account Name', 'Account Number', 'Region', 'Instance Type',
                   'Instance Id', 'Private Ip', 'Public Ip', 'State', 'SSM Managed']
    writer = csv.DictWriter(string_io, fieldnames=headers)
    writer.writeheader()
    writer.writerows(csv_data)
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = content_disposition_string
    output.headers["Content-type"] = csv_content_type
    return output
