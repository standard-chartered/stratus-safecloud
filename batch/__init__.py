from db_models import AwsAccountModel, find_aws_account_model_by_profile
import time
import os
import stat
from datetime import datetime
import yaml


def get_account_number(profile):
    aws_account = find_aws_account_model_by_profile(profile)
    return aws_account.account_number


def get_account_name(profile):
    aws_account = find_aws_account_model_by_profile(profile)
    return aws_account.account_name


def get_account_env(profile):
    aws_account = find_aws_account_model_by_profile(profile)
    return aws_account.env


def get_file_age_seconds(filepath):
    return time.time() - os.stat(filepath)[stat.ST_MTIME]

cache_timeout = 24 * 3600  # 1 day
global_cache_dir = 'cache'


def get_cache_dir(type):
    paths = {
        'config': '/aws-config',
        'infra': '/aws-infra',
        'security': '/aws-security',
        'trusted-advisor': '/aws-trusted-advisor',
        'ec2': '/ec2-instances'
        }
    cache_dir = '{}{}'.format(global_cache_dir, paths[type])
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir


def get_cache_name(type, profile, report_type):
    template = {
        'config': 'aws_config',
        'infra': 'aws_resource',
        'security': 'aws_security',
        'trusted-advisor': 'aws_trusted_advisor',
        'ec2': 'ec2_instances'
        }
    return '{type}_profile={profile}_type={report}'.format(type=template[type], profile=profile, report=report_type)


def write_data_to_cache(type, report_data, profile, report_type):
    """
    This caches the AWS Infrastructure data for a given AWS Profile project
    """
    """
    When we cache the report data, wrap it in an envelope that contains
    also the datetime when we generated it.
    """
    data_envelope = {}
    data_envelope['data'] = report_data
    now = datetime.now()
    timestamp = now.strftime("%d-%b-%Y (%H:%M:%S.%f)")
    data_envelope['last_update'] = timestamp
    data_envelope['profile'] = profile
    data_envelope['account_name'] = get_account_name(profile)

    cache_filepath = '{cache_dir}/{cache_name}.yaml'.format(
        cache_dir=get_cache_dir(type),
        cache_name=get_cache_name(type, profile, report_type))

    """
    Save the results, wrapped in our envelope
    """
    f = open(cache_filepath, 'w')
    yaml.dump(data_envelope, f)
    f.close()


def cache_read(type, cache_key):
    cache_filepath = '{cache_dir}/{cache_name}.yaml'.format(
        cache_dir=get_cache_dir(type),
        cache_name=cache_key)
    if os.path.isfile(cache_filepath):
        f = open(cache_filepath, 'r')
        contents = f.read()
        f.close()
        return contents
    else:
        return 'data: {}'
 

def get_cached_data(type, profile, report):
    cache_name = get_cache_name(type, profile, report)
    print('Reading from cache:', cache_name)
    yaml_data = cache_read(type, cache_name)
    py_data = yaml.load(yaml_data, Loader=yaml.Loader)
    return py_data

def format_seconds_to_hhmmss(seconds):
    hours = seconds // (60 * 60)
    seconds %= (60 * 60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)