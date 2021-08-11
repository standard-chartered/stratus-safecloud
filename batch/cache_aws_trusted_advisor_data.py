"""
Usage: cache_aws_trusted_advisor_data.py [options]

Options:
  --profile PROFILE     profile to use for AWS access

  --loglevel LEVEL      logging level
                        [default: INFO]
"""
import logging
import os
import pprint
from datetime import datetime

import boto3
import urllib3
import yaml
from docopt import docopt

import batch

boto3.set_stream_logger('', logging.CRITICAL)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


pp = pprint.PrettyPrinter(indent=4)
cache_timeout = 24 * 3600  # 1 day
cache_name_template = 'aws_trusted_advisor_profile={profile}_type={report}'


logger = logging.getLogger(__name__)




def cache_trusted_advisor_data(profile):
    # Returns a list of OrderedDict objects
    results = []
    session = boto3.session.Session(profile_name=profile)
    client = session.client('support', verify=False, region_name='us-east-1')
    try:
        ta_checks = client.describe_trusted_advisor_checks(language='en')
        ta_checks = ta_checks['checks']
        for check in ta_checks:
            tmp = {}
            tmp['id'] = check['id']
            tmp['name'] = check['name']
            tmp['category'] = check['category']
            tmp['description'] = check['description']
            data = client.describe_trusted_advisor_check_result(checkId=tmp['id'])
            tmp['result'] = data['result']
            results.append(tmp)
            print('\t', check['name'], 'result:', data['result']['status'])
        ids = [d['id'] for d in results]
        summaries = client.describe_trusted_advisor_check_summaries(checkIds=ids)
        summaries = summaries['summaries']
        for summary in summaries:
            for check in results:
                if summary['checkId'] == check['id']:
                    summary['check_id'] = check['id']
                    summary['name'] = check['name']
                    summary['description'] = check['description']
                    summary['category'] = check['category']
                    break   
        batch.write_data_to_cache('trusted-advisor', results, profile, 'details')
  
        data = {}
        data['categories'] = {}
        savings = 0.0
        for item in results:
            if 'categorySpecificSummary' in item['result'] and 'costOptimizing' in item['result']['categorySpecificSummary']:
                 savings += item['result']['categorySpecificSummary']['costOptimizing']['estimatedMonthlySavings']
        dollar_savings = "{:.2f}".format(savings)
        print("Savings:", dollar_savings)
        for category in ['cost_optimizing', 'performance', 'security', 'fault_tolerance', 'service_limits']:
            category_name = category.replace('_', ' ')
            category_name = category_name.title()
            data['categories'][category] = {}
            category_checks = [d for d in results if d['category'] == category]
            ok_checks = [d for d in category_checks if d['result']['status'] == 'ok']
            warning_checks = [d for d in category_checks if d['result']['status'] == 'warning']
            error_checks = [d for d in category_checks if d['result']['status'] == 'error']
            not_available = [d for d in category_checks if d['result']['status'] == 'not_available']
            data['categories'][category]['name'] = category_name
            data['categories'][category]['ok'] = len(ok_checks)
            data['categories'][category]['warning'] = len(warning_checks)
            data['categories'][category]['error'] = len(error_checks)
            data['categories'][category]['not_available'] = len(not_available)
        data['savings'] = dollar_savings
        pp.pprint(data)
        batch.write_data_to_cache('trusted-advisor', data, profile, 'results')
    except:
        data = {}
        data['categories'] = {}
        data['error'] = True
        for category in ['cost_optimizing', 'performance', 'security', 'fault_tolerance', 'service_limits']:
            category_name = category.replace('_', ' ')
            category_name = category_name.title()
            data['categories'][category] = {}
            data['categories'][category]['name'] = category_name
            data['categories'][category]['ok'] = 0
            data['categories'][category]['warning'] = 0
            data['categories'][category]['error'] = 0
            data['categories'][category]['not_available'] = 0
        batch.write_data_to_cache('trusted-advisor', {}, profile, 'details')
        batch.write_data_to_cache('trusted-advisor', data, profile, 'results')
    return


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'SCVAutumnDev'

    loglevel = args['--loglevel'].upper()
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=loglevel)
    logger = logging.getLogger(__name__)
    cache_trusted_advisor_data(profile)
