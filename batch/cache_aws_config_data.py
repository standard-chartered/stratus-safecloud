"""
Usage: cache_aws_config_data.py [options]

Options:
  --profile PROFILE     profile to use for AWS access

"""
import platform
import time
from datetime import datetime

import boto3
import os
import yaml
from docopt import docopt

import batch.cache_aws_security_data as aws_security

import batch
import getpass

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


def cache_config_data(profile):
    output = {}
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-west-2', 'ap-southeast-1', 'eu-central-1']
    for region in regions:
        print('Collecting AWS Config data for profile', profile, 'in region', region)
        output[region] = {}    
        # Make sure our boto3 calls use the correct profile by setting
        # up the default session
        boto3.setup_default_session(profile_name=profile, region_name=region)
        aws_config=boto3.client('config')
        try:
            result = aws_config.describe_config_rules()
        except Exception as e:
            print(str(e))
            output[region]['compliant'] = {}
            output[region]['non_compliant'] = {}
            output[region]['compliant_rule_count'] = 0
            output[region]['non_compliant_rule_count'] = 0
            output[region]['compliant_resources_count'] = 0
            output[region]['non_compliant_resources_count'] = 0
            batch.write_data_to_cache('config', output, profile, 'detail')
            return output
        
        data = result['ConfigRules']
        i = 1
        while True:
            i = i + 1
            if 'NextToken' in result:
                result = aws_config.describe_config_rules(NextToken=result['NextToken']) 
                data += result['ConfigRules']
            else:
                break
            
        evaluation_results = []
        for item in data:
            response = aws_config.get_compliance_details_by_config_rule(ConfigRuleName=item['ConfigRuleName'])
            evaluation_results += response['EvaluationResults']

            while True:
                if 'NextToken' in response:
                    response = aws_config.get_compliance_details_by_config_rule(ConfigRuleName=item['ConfigRuleName'],
                                                                            NextToken=response['NextToken'])
                    evaluation_results += response['EvaluationResults']
                else:
                    break
    
        # Walk through the list to find out how many compliant and non-compliant rules there are
        compliant = 0
        non_compliant = 0
        unknown = 0
        non_compliant_resources = []
        compliant_resources = []
        for item in evaluation_results:
            if item['ComplianceType']  == 'NON_COMPLIANT':
                non_compliant += 1
                non_compliant_resources.append(item)
            elif item['ComplianceType']  == 'COMPLIANT':
                compliant += 1
                compliant_resources.append(item)
            else:
                unknown += 1
            
        output[region]['compliant'] = {}
        output[region]['non_compliant'] = {}
        rule_names = []
        for rule in non_compliant_resources:
            resource_list = []
            rule_name = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ConfigRuleName']
            tmp = {}
            tmp['resource_id'] = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId']
            tmp['resource_type'] = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceType']
            
            if  rule_name not in rule_names:
                rule_names.append(rule_name)
                resource_list.append(tmp)
                output[region]['non_compliant'][rule_name] = resource_list
            else:
                updated_resource_list = output[region]['non_compliant'][rule_name]
                updated_resource_list.append(tmp)
                output[region]['non_compliant'][rule_name] = updated_resource_list

        rule_names = []
        for rule in compliant_resources:
            resource_list = []
            rule_name = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ConfigRuleName']
            tmp = {}
            tmp['resource_id'] = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId']
            tmp['resource_type'] = rule['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceType']
            if  rule_name not in rule_names:
                rule_names.append(rule_name)
                resource_list.append(tmp)
                output[region]['compliant'][rule_name] = resource_list
            else:
                updated_resource_list = output[region]['compliant'][rule_name]
                updated_resource_list.append(tmp)
                output[region]['compliant'][rule_name] = updated_resource_list
    
        # Get all the compliant resource ids and remove duplicates
        compliant_resource_ids = []
        for rule in output[region]['compliant']:
            for resource in output[region]['compliant'][rule]:
                if resource['resource_id'] not in compliant_resource_ids:
                    compliant_resource_ids.append(resource['resource_id'])
    
        non_compliant_resource_ids = []
        for rule in output[region]['non_compliant']:
            for resource in output[region]['non_compliant'][rule]:
                if resource['resource_id'] not in non_compliant_resource_ids:
                    non_compliant_resource_ids.append(resource['resource_id'])
    
        output[region]['compliant_rule_count'] = len(output[region]['compliant'])
        output[region]['non_compliant_rule_count'] = len(output[region]['non_compliant'])
        output[region]['compliant_resources_count'] = len(compliant_resource_ids)
        output[region]['non_compliant_resources_count'] = len(non_compliant_resource_ids)
           
        print('Compliant Rules:', len(output[region]['compliant']))
        print('Non-Compliant Rules:', len(output[region]['non_compliant']))
        print('Compliant Resources:', len(compliant_resource_ids))
        print('Non-Compliant Resources:', len(non_compliant_resource_ids))

    batch.write_data_to_cache('config', output, profile, 'detail')

    return output


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')

    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'all'

    # credentials is the aws credentials file that contains the AWS access key id
    # and secret access key for the various AWS accounts.

    credentials = get_credentials()
    all_profiles = get_all_profiles(credentials)
    
    # Is Stratus SafeCloud running in EC2 ?  Let's get the IP address
    vamp_ip = aws_security.get_ec2_instance_ip()
    if vamp_ip:
        print('\nStratus SafeCloud is running at', vamp_ip, 'on port 5000')
    else:
        print('\nCannot get IP address for Stratus SafeCloud.  Please check the EC2 instance is running')
        
    # Time how long the update takes
    start = time.time()
    
    if profile == 'all':
        for item in all_profiles:
            if 'default' in item:
                continue
            if 'personal' in item:
                continue
            cache_config_data(item)
    elif '*' in profile:
        group = profile.split('*')
        profiles = [i for i in all_profiles if i.startswith(group[0])]
        for item in profiles:
            cache_config_data(item)
    else:
        cache_config_data(profile)

    end = time.time()
    seconds = int(end - start)
    duration = batch.format_seconds_to_hhmmss(seconds)
    print('Time to complete updates:', duration)

