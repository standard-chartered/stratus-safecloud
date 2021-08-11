"""
Usage: cache_aws_infra.py [options]

Options:
  --profile PROFILE     profile to use for AWS access

  --loglevel LEVEL      logging level
                        [default: INFO]
"""
import batch
import platform
import importlib.util
import importlib
from skew import ARN, scan
import urllib3
import pprint
from datetime import datetime
import logging
import os
import stat
import time

import boto3
import yaml
from docopt import docopt

boto3.set_stream_logger('', logging.CRITICAL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pp = pprint.PrettyPrinter(indent=4)
cache_timeout = 24 * 3600  # 1 day
cache_name_template = 'aws_resource_profile={profile}_type={report}'


logger = logging.getLogger(__name__)



def cache_infra_data(profile):
    global_services = ['iam', 's3', 'route53', 'cloudfront']
    results = {}
    arn = ARN()
    if profile in ['AladdinPreProd', 'LydiaProd']:
        batch.write_data_to_cache('infra', results, profile, 'infra')
        return
    account = batch.get_account_number(profile)
    if not account:
        print('Cannot find an AWS account number for profile:', profile)
        return
    services = arn.service.choices()
    results[account] = {}
    for service in services:
        # if service == 'sns':
        #    continue
        results[account][service] = {}
        if service in global_services:
            region = '*'
        elif 'Lydia' in profile:
            region = 'eu-west-2'
        else:
            region = 'ap-southeast-1'
        arn = scan('arn:aws:' + service + ':' + region + ':' + account)
        choices = arn.resource.choices()

        for choice in choices:
            results[account][service][choice] = []
            arn = scan('arn:aws:' + service + ':' + region +
                       ':' + account + ':' + choice + '/*')
            try:
                for resource in arn:

                    results[account][service][choice].append(resource.data)
            except Exception as e:
                print(str(e))
                # print(results)
    batch.write_data_to_cache('infra', results, profile, 'infra')
    return


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'SCVTooling'

    loglevel = args['--loglevel'].upper()
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=loglevel)
    logger = logging.getLogger(__name__)

    # Tell skew where the config file is to get AWS account profile
    # names and account numbers
    user = os.environ['USER']
    if not user:
        print('No USER env set')
        exit()

    my_platform = platform.system()
    if 'SKEW_CONFIG' not in os.environ:
        if my_platform == 'Darwin':
            os.environ['SKEW_CONFIG'] = '/Users/{user}/Workspace/ssc/.skew'.format(
                user=user)
        else:
            os.environ['SKEW_CONFIG'] = '/home/{user}/Workspace/ssc/.skew'.format(
                user=user)

    # Cache the AWS resource usage data
    cache_infra_data(profile)
