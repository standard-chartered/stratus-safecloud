"""
Usage: cache_aws_security_data.py [options]

Options:
  --profile PROFILE     profile to use for AWS access

  --loglevel LEVEL      logging level
                        [default: INFO]
"""
import batch
from db_models import ProjectModel
import importlib.util
import importlib
import platform
import urllib3
import pprint
from natsort import natsorted
from collections import OrderedDict
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
cache_name_template = 'aws_security_profile={profile}_type={report}'


logger = logging.getLogger(__name__)


def get_failed_count(data):
    count = 0
    for item in data:
        for result in data[item]:
            if 'FAILED' in result['Compliance']['Status']:
                count += 1
                break
    return count


def get_passed_count(data):
    count = 0
    for item in data:
        for result in data[item]:
            if 'PASSED' in result['Compliance']['Status']:
                count += 1
                break
    return count


def get_unknown_count(data):
    count = 0
    for item in data:
        for result in data[item]:
            if 'WARNING' in result['Compliance']['Status']:
                count += 1
                break
    return count


def get_disabled_count(data, disabled):
    count = 0
    for key in data:
        for result in data[key]:
            if result['ProductFields']['StandardsControlArn'] in disabled:
                count += 1
                break
    return count


def calculate_scores(profile, data, enabled, disabled):
    results = {}
    scores = {}
    total_passed = 0
    total_enabled = 0
    total_no_data = 0
    if not disabled:
        scores = {}
        batch.write_data_to_cache('security', scores, profile, 'score')
        return scores
    for standard in data:
        # Ignore guardduty controls since they
        # are not scored
        if standard == 'guardduty':
            continue
        total_enabled += len(enabled[standard])
        results[standard] = []
        for control in data[standard]:
            tmp = {}
            tmp['control'] = control
            findings = []
            for item in data[standard][control]:
                tmp2 = {}
                tmp2['compliance'] = item['Compliance']['Status']
                tmp2['workflow'] = item['Workflow']['Status']
                findings.append(tmp2)
            tmp['findings'] = findings
            results[standard].append(tmp)

        # Calculate the scores
        failed = 0
        passed = 0
        unknown = 0
        no_data = 0
        for item in results[standard]:
            if check_for_passed(item['findings']):
                passed += 1
            if check_for_failed(item['findings']):
                failed += 1
            if check_for_unknown(item['findings']):
                unknown += 1
        no_data = len(enabled[standard]) - (failed + passed + unknown)
        # Disabled controls are by definition "unknown"
        unknown += len(disabled[standard])
        total_no_data += no_data
        scores[standard] = {}
        scores[standard]['enabled'] = len(enabled[standard])
        scores[standard]['disabled'] = len(disabled[standard])
        scores[standard]['failed'] = failed
        scores[standard]['passed'] = passed
        total_passed += passed
        scores[standard]['unknown'] = unknown
        scores[standard]['no_data'] = no_data
        if len(enabled[standard]) + len(disabled[standard]) - no_data == 0:
            scores[standard]['percentage'] = '{:.0f}%'.format(0)
        else:
            scores[standard]['percentage']  = '{:.0f}%'.format(
                float(passed)/float(len(enabled[standard]) + len(disabled[standard]) - no_data))

    scores['total_passed'] = total_passed
    scores['total_enabled'] = total_enabled - total_no_data
    if (total_enabled - total_no_data) == 0:
        score = 0
    else:
        score = (float(total_passed)/float(total_enabled - total_no_data)) * 100
    scores['overall_score'] = score
    print(score)
    scores['percent'] = '{:.0f}%'.format(score)
    print(scores['percent'])
    batch.write_data_to_cache('security', scores, profile, 'score')
    return scores


def check_for_no_data(findings_list):
    print(findings_list)
    return


def check_for_passed(finding_list):
    passed = all(d['compliance'] == 'PASSED' for d in finding_list)
    resolved = all(d['workflow'] == 'RESOLVED' for d in finding_list)
    result = passed or resolved
    return result


def check_for_failed(finding_list):
    failed = any(d['compliance'] == 'FAILED' and not d['workflow']
                 == 'RESOLVED' for d in finding_list)
    result = failed
    return result


def check_for_unknown(finding_list):
    # Unknown - indicates that one of the following is true:
    #    * There are no findings
    #    * All findings have a Workflow.Status of SUPPRESSED. Because SUPPRESSED findings are ignored, this is equivalent to no findings.
    #    * No findings are FAILED. At least one finding has a Compliance.Status of WARNING or NOT_AVAILABLE
    #      and does not have a Workflow.Status of RESOLVED or SUPPRESSED.
    if len(finding_list) == 0:
        no_findings = True
    else:
        no_findings = False
    suppressed = all(d['workflow'] == 'SUPPRESSED' for d in finding_list)
    no_failures = not any(d['compliance'] == 'FAILED' for d in finding_list)
    warning = any((d['compliance'] == 'WARNING' or d['compliance'] == 'NOT_AVAILABLE')
                  and not (d['workflow'] == 'RESOLVED' or d['workflow'] == 'SUPPRESSED') for d in finding_list)
    result = no_findings or suppressed or (no_failures and warning)
    return result


def cache_scores(data, disabled_controls, profile):
    result = {}
    failed = get_failed_count(data['cis-aws-foundations-benchmark'])
    unknown = get_unknown_count(data['cis-aws-foundations-benchmark'])
    disabled = get_disabled_count(
        data['cis-aws-foundations-benchmark'], disabled_controls)
    failed -= disabled
    cis_passed = get_passed_count(data['cis-aws-foundations-benchmark'])
    cis_total_enabled = cis_passed + failed + unknown
    percent = '{:.0%}'.format(float(cis_passed)/float(cis_total_enabled))
    result['cis_failed'] = failed
    result['cis_passed'] = cis_passed
    result['cis_score'] = percent

    aws_total = len(data['aws-foundational-security-best-practices'])
    failed = get_failed_count(data['aws-foundational-security-best-practices'])
    unknown = get_unknown_count(
        data['aws-foundational-security-best-practices'])
    disabled = get_disabled_count(
        data['aws-foundational-security-best-practices'], disabled_controls)
    failed -= disabled
    aws_passed = aws_total - failed - unknown - disabled
    aws_total_enabled = aws_passed + failed + unknown
    percent = '{:.0%}'.format(float(aws_passed)/float(aws_total_enabled))
    result['aws_failed'] = failed
    result['aws_passed'] = aws_passed
    result['aws_score'] = percent
    denominator = aws_total_enabled + cis_total_enabled
    nominator = aws_passed + cis_passed
    overall_score = float(nominator)/float(denominator) * 100
    overall_score_percent = '{:.0%}'.format(
        float(nominator)/float(denominator))
    result['overall_score'] = overall_score
    result['overall_score_percent'] = overall_score_percent
    batch.write_data_to_cache('security', result, profile, 'score')
    return result


def get_aws_security_data(profile, disabled):
    # Returns a list of OrderedDict objects
    if not disabled:
        output = {}
        batch.write_data_to_cache('security', output, profile, 'detail')
        return output
    session = boto3.session.Session(profile_name=profile)
    client = session.client('securityhub', verify=False)
    myfilter = {'RecordState': [{'Value': 'ACTIVE', 'Comparison': 'EQUALS'}]}
    result = client.get_findings(Filters=myfilter)
    data = result['Findings']
    i = 1
    while True:
        i = i + 1
        if 'NextToken' in result:
            result = client.get_findings(
                Filters=myfilter, NextToken=result['NextToken'])
            data += result['Findings']
        else:
            break
    findings = []
    for item in data:
        if 'guardduty' not in item['ProductArn']:
            findings.append(item)

    standards = ['cis-aws-foundations-benchmark',
                 'aws-foundational-security-best-practices']

    # Create an ordered dict with titles as keys (no duplicates)
    titles = natsorted(list(set([d['Title'] for d in findings])))
    results = OrderedDict()
    for item in titles:
        results[item] = [d for d in findings if d['Title'] == item]
    output = {}
    for standard in standards:
        if standard not in disabled:
            continue
        temp = OrderedDict()
        for item in results:
            if 'StandardsControlArn' not in results[item][0]['ProductFields']:
                continue
            if results[item][0]['ProductFields']['StandardsControlArn'] in disabled[standard]:
                continue
            if standard in results[item][0]['GeneratorId']:
                temp[item] = results[item]
        output[standard] = temp

    batch.write_data_to_cache('security', output, profile, 'detail')
    return output


def get_disabled_controls(profile):
    # Returns a list of OrderedDict objects
    session = boto3.session.Session(profile_name=profile)
    client = session.client('securityhub', verify=False)
    try:
        standards = client.get_enabled_standards()
    except Exception as e:
        print(str(e))
        standards = {}
    if standards:
        enabled_standards = [d['StandardsSubscriptionArn'] for d in standards['StandardsSubscriptions']
                             if d['StandardsStatus'] == 'READY' or d['StandardsStatus'] == 'INCOMPLETE']
        disabled = {}
        for standard in enabled_standards:
            name = standard.split('/')[1]
            result = client.describe_standards_controls(
                StandardsSubscriptionArn=standard)
            data = [d['StandardsControlArn']
                    for d in result['Controls'] if d['ControlStatus'] == 'DISABLED']
            disabled[name] = data
    else:
        disabled = {}
    return disabled


def get_enabled_controls(profile):
    # Returns a list of OrderedDict objects
    session = boto3.session.Session(profile_name=profile)
    client = session.client('securityhub', verify=False)
    try:
        standards = client.get_enabled_standards()
    except Exception as e:
        print(str(e))
        standards = {}
    if standards:
        enabled_standards = [d['StandardsSubscriptionArn'] for d in standards['StandardsSubscriptions']
                             if d['StandardsStatus'] == 'READY' or d['StandardsStatus'] == 'INCOMPLETE']
        enabled = {}
        for standard in enabled_standards:
            name = standard.split('/')[1]
            result = client.describe_standards_controls(
                StandardsSubscriptionArn=standard)
            data = [d['StandardsControlArn']
                    for d in result['Controls'] if d['ControlStatus'] == 'ENABLED']
            enabled[name] = data
    else:
        enabled = {}
    return enabled


def get_aws_controls(profile, status='DISABLED'):
    # Returns a list of OrderedDict objects
    session = boto3.session.Session(profile_name=profile)
    client = session.client('securityhub', verify=False)
    standards = client.get_enabled_standards()
    enabled_standards = [d['StandardsSubscriptionArn']
                         for d in standards['StandardsSubscriptions'] if d['StandardsStatus'] == 'READY']
    results = {}
    for standard in enabled_standards:
        standard_name = standard.split('/')[1]
        results[standard_name] = []
        result = client.describe_standards_controls(
            StandardsSubscriptionArn=standard)
        data = [d['ControlId']
                for d in result['Controls'] if d['ControlStatus'] == status]
        results[standard_name] = data
    print(results)
    return results


def cache_security_data(profile):
    disabled = get_disabled_controls(profile)
    # pp.pprint(disabled)
    enabled = get_enabled_controls(profile)
    # pp.pprint(enabled)
    data = get_aws_security_data(profile, disabled)
    # pp.pprint(data)
    calculate_scores(profile, data, enabled, disabled)
    return


def get_ec2_instance_ip():
    session = boto3.session.Session(profile_name='SCVTooling')
    client = session.client('ec2', verify=False)
    response = client.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            tags = instance['Tags']
            for tag in tags:
                if tag['Key'] == 'Name' and tag['Value'] == 'Vamp':
                    return instance['PublicIpAddress']
    return ''


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    if args['--profile']:
        profile = args['--profile']
    else:
        profile = 'AutumnDev'

    vamp_ip = get_ec2_instance_ip()
    if vamp_ip:
        print('SSC is running at', vamp_ip, 'on port 5000')
    else:
        print('Cannot find IP Address for SSC application.  Check the EC2 instance is running in SCV Tooling account')

    cache_security_data(profile)
