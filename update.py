"""
Usage: update.py [options]

Options:
  --profile PROFILE     profile to use for AWS access.  Note that you can 
                        update multiple accounts by using a wildcard '*' in
                        the profile name, like this:  
                        
                        python update.py --profile Autumn*
                        
                        This will run the update for all the Autumn accounts

"""
import botocore.config
from docopt import docopt
import batch.cache_aws_security_data as aws_security
import batch.cache_aws_infra as aws_infra
import batch.cache_aws_trusted_advisor_data as aws_trusted_advisor
import batch.cache_ec2_instance_data as ec2_instance_data
import batch.cache_aws_config_data as aws_config_data
import os
import time
import platform
import getpass
import logging
import sys

log = logging.getLogger(__name__)


def format_seconds_to_hhmmss(seconds):
    hours = seconds // (60 * 60)
    seconds %= (60 * 60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)


def get_credentials():
    
    my_platform = platform.system()

    user = getpass.getuser()

    if user == '':
        if 'USER' in os.environ:
            user = os.environ['USER']
        else:
            user = 'ubuntu'

    skew_config = ''
    if 'SKEW_CONFIG' in os.environ:
        skew_config = os.environ['SKEW_CONFIG']

    if not skew_config:
        if os.path.exists('./.skew'):
            os.environ['SKEW_CONFIG'] = os.path.abspath('./.skew')
        if my_platform == 'Darwin':
            os.environ['SKEW_CONFIG'] = '/Users/{user}/Workspace/ssc/.skew'.format(user=user)
        else:
            os.environ['SKEW_CONFIG'] = '/home/{user}/Workspace/ssc/.skew'.format(user=user)
    if my_platform == 'Darwin':
        return_credentials = '/Users/{user}/.aws/credentials'.format(user=user)
    elif my_platform == 'Windows':
        return_credentials = 'C:\\users\\{user}/.aws/credentials'.format(user=user)
    else:
        return_credentials = '/home/{user}/.aws/credentials'.format(user=user)
    return return_credentials


def get_all_profiles(credentials):
    with open(credentials, 'r') as infile:
        filedata = infile.readlines()
    profiles = []
    for line in filedata:
        if line.startswith('['):
            line = line.replace('[', '')
            line = line.replace(']', '')
            profiles.append(line.rstrip())
    return profiles


def update_one_profile(profile):
    log.debug('\nCollecting AWS security data for profile: {}'.format(profile))
    aws_security.cache_security_data(profile)
    log.debug('Collecting AWS resource data for profile: {}'.format(profile))
    aws_infra.cache_infra_data(profile)
    log.debug('Collecting AWS Trusted Advisor data for profile: {}'.format(profile))
    aws_trusted_advisor.cache_trusted_advisor_data(profile)
    log.debug('Collecting AWS Config data for profile: {}'.format(profile))
    aws_config_data.cache_config_data(profile)

def update_some_profiles(profile):
    group = profile.split('*')

    log.debug('\nCollecting AWS security data for profile: {}'.format(profile))
    aws_security.cache_security_data(profile)
    log.debug('Collecting AWS resource data for profile: {}'.format(profile))
    aws_infra.cache_infra_data(profile)
    log.debug('Collecting AWS Trusted Advisor data for profile: {}'.format(profile))
    aws_trusted_advisor.cache_trusted_advisor_data(profile)
    log.debug('Collecting AWS Config data for profile: {}'.format(profile))
    aws_config_data.cache_config_data(profile)


def update_profiles(profiles):
    for profile in profiles:
        if 'default' in profile:
            continue
        if 'personal' in profile:
            continue
        log.debug('\nCollecting AWS security data for profile:{}'.format(profile))
        aws_security.cache_security_data(profile)
        log.debug('Collecting AWS resource data for profile:{}'.format(profile))
        aws_infra.cache_infra_data(profile)
        log.debug('Collecting AWS Trusted Advisor data for profile:{}'.format(profile))
        aws_trusted_advisor.cache_trusted_advisor_data(profile)
        log.debug('Collecting AWS Config data for profile:{}'.format(profile) )
        aws_config_data.cache_config_data(profile)


if __name__ == '__main__':
    # todo to load env file for update

    # load dotenv in the base root
    APP_ROOT = os.path.dirname(__file__)   # refers to application_top
    dotenv_path = os.path.join(APP_ROOT, '.env')
    
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)
    print(dotenv_path)

    from flask import Flask
    from db import db
    app = Flask(__name__)
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    app.config['SQLALCHEMY_DATABASE_URI']=os.environ['SQLALCHEMY_DATABASE_URI']
    db.init_app(app)

    app.app_context().push()


    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler('update_script.log', maxBytes=10000000, backupCount=5)
    logging.basicConfig(level=logging.WARN, handlers=[handler], force=True)

    args = docopt(__doc__, version='1.0')
    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'all'

    # credentials is the aws credentials file that contains the AWS access key id
    # and secret access key for the various AWS accounts.

    credentials = get_credentials()
    all_profiles = get_all_profiles(credentials)

    # Is portal running in EC2 ?  Let's get the IP address
    vamp_ip = aws_security.get_ec2_instance_ip()
    if vamp_ip:
        log.debug('\Project is running at {} on port 5000'.format(vamp_ip))
    else:
        log.debug('\nCannot get IP address for portal.  Please check the EC2 instance is running')

    # Time how long the update takes
    start = time.time()

    if profile == 'all':
        update_profiles(all_profiles)
    elif '*' in profile:
        group = profile.split('*')
        profiles = [i for i in all_profiles if i.startswith(group[0])]
        update_profiles(profiles)
    else:
        update_one_profile(profile)

    end = time.time()
    seconds = int(end - start)
    duration = format_seconds_to_hhmmss(seconds)
    log.debug('Time to complete updates:{}'.format( duration))
