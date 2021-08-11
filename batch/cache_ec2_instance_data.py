"""
Usage: ec2.py [options]

Options:
  --profile PROFILE     profile to use for AWS access.  Note that you can 
                        update multiple accounts by using a wildcard '*' in
                        the profile name, like this:  
                        
                        python ec2.py --profile Autumn*
                        
                        This will check for ec2 instances in all regions for Autumn accounts

"""
import importlib
import importlib.util
import os
import platform
import pprint
import time
from datetime import datetime
import batch
import getpass

import boto3
import urllib3
import yaml
from docopt import docopt

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pp = pprint.PrettyPrinter(indent=4)


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

def get_regions():
    session = boto3.session.Session(profile_name=profile)
    client = session.client('ec2', verify=False)
    response = client.describe_regions()
    regions = [d['RegionName'] for d in response['Regions']]
    return regions

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

def check_one_profile(profile, regions):
    results = {}
    session = boto3.session.Session(profile_name=profile)
    for region in regions:
        results[region] = {}
        results[region]['instances'] = []
        results[region]['ssm_managed'] = 0
        results[region]['not_ssm_managed'] = 0
        results[region]['instance_count'] = 0

        print('\tChecking region:', region)
        try:
            ec2_client = session.client('ec2', region_name=region, verify=False)
            ssm_client = session.client('ssm', region_name=region, verify=False)
            response = ec2_client.describe_instances()
            managed_instances = get_ssm_managed_instances(profile, region)
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    patches = []
                    if 'running' not in instance['State']['Name']:
                        # Don't care about non-running instances
                        continue
                    ssm_response = ssm_client.describe_instance_patches(InstanceId=instance['InstanceId'])
                    patches = ssm_response['Patches']
                    i = 1
                    while True:
                        i = i + 1
                        if 'NextToken' in ssm_response:
                            ssm_response = ssm_client.describe_instance_patches(InstanceId=instance['InstanceId'],
                                                                                NextToken=ssm_response['NextToken']) 
                            patches += ssm_response['Patches']
                        else:
                            break
                    non_compliant_patches = [d for d in patches if d['State'] in ['Installed Pending Reboot',
                                                                                  'Installed Rejected',
                                                                                  'Missing',
                                                                                  'Failed']]

                    compliant_patches = [d for d in patches if d['State'] in ['Installed',
                                                                              'Installed Other']]
                    tmp = {}
                    tmp['region'] = region
                    tmp['instance_id'] = instance['InstanceId']
                    tmp['instance_type'] = instance['InstanceType']
                    tmp['patch_compliance'] = non_compliant_patches
                    tmp['non_compliant_patch_count'] = len(non_compliant_patches)
                    tmp['compliant_patch_count'] = len(compliant_patches)
                    if 'PublicIpAddress' in instance:
                        tmp['public_ip'] = instance['PublicIpAddress']
                    else:
                        tmp['public_ip'] = 'Not Present'
                    tmp['private_ip'] = instance['PrivateIpAddress']
                    tmp['state'] = instance['State']['Name']
                    if instance['InstanceId'] in managed_instances:
                        tmp['ssm_managed'] = True
                    else:
                        tmp['ssm_managed'] = False
                    results[region]['instances'].append(tmp)
            results[region]['instance_count'] = len(results[region]['instances'])
            ssm_managed = [d['instance_id'] for d in results[region]['instances'] if d['ssm_managed'] == True]
            results[region]['ssm_managed'] = len(ssm_managed)
            results[region]['not_ssm_managed'] = results[region]['instance_count'] - results[region]['ssm_managed']
            
        except Exception as e:
            print(str(e))
    batch.write_data_to_cache('ec2', results, profile, 'details')    
    return results

def get_ssm_managed_instances(profile, region):
    instances = []
    session = boto3.session.Session(profile_name=profile)
    print('\tCollecting SSM managed instances:', region)
    ssm_client = session.client('ssm', region_name=region, verify=False)
    try:
        response = ssm_client.describe_instance_information()
        instances = [d['InstanceId'] for d in response['InstanceInformationList'] if d['ResourceType'] == 'EC2Instance']
    except Exception as e:
        print(str(e))
    return instances
    
def check_profiles(profiles, regions):
    results = {}
    for profile in profiles:
        results[profile] = []
        if 'default' in profile:
            continue
        if 'personal' in profile:
            continue
        print('\nChecking for EC2 instances for account', profile)
        details = check_one_profile(profile, regions)
        results[profile].append(details)
    pp.pprint(results)

            
if __name__ == '__main__':
     # load dotenv in the base root
    APP_ROOT = os.path.dirname(__file__)   # refers to application_top
    dotenv_path = os.path.join(APP_ROOT, '../.env')
    
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

    args = docopt(__doc__, version='1.0')
    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'all'
        
    # Time how long the update takes
    start = time.time()
    
    # credentials is the aws credentials file that contains the AWS access key id
    # and secret access key for the various AWS accounts.

    credentials = get_credentials()
    all_profiles = get_all_profiles(credentials)
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'ap-southeast-1', 'eu-central-1']
    if profile == 'all':
        check_profiles(all_profiles, regions)
    elif '*' in profile:
        group = profile.split('*')
        profiles = [i for i in all_profiles if i.startswith(group[0])]
        print(profiles)
        check_profiles(profiles, regions)
    else:
        check_one_profile(profile, regions)

    end = time.time()
    seconds = int(end - start)
    duration = batch.format_seconds_to_hhmmss(seconds)
    print('Time to complete ec2 instance data collection:', duration)

    



