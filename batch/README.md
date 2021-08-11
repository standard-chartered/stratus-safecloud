# Using the cache_aws_config_data.py script

## Introduction
In order to get access to AWS Config in all the different accounts, we need to change
our approach slightly for this script.

In other data collection scripts, we've been able to simply use the existing "reporter"
user in each of the accounts - this user belongs to a group which has all the required
access rights to collect the required data (security, infra, trusted-advisor, etc.).

Sadly (but sensibly) access to AWS Config is restricted by SCP rules, so we need to take
a different approach.

The way I've been able to do this is to use AWS SSO and modify the ~/.aws/config entries
to make use of it.

Unfortunately, due to the way AWS SSO works, ir requires you to log in using the following
awscli v2 command:

```
$ aws sso login --profile <profile>
```
This then opens a browser window which requires manual intervention to accept the sign-in
*before* you can run the script.

You can, however, then change the profile without having to re-login in to SSO.
The SSO credentials will last for one hour.

Once the aws sso login confirmation been accepted in the browser, you can run the script as required.

This doesn't lend itself well to automation and especially trying to run it on an EC2 instance
where no browser exists, so I'll make this script run locally and then scp the generated data 
cache files over to the EC2 instance.


## Issues or Questions
IF you have any issues or concerns about the application or suggestions as to how 
it could be improved, please do nto hesitate to contact me.

**Name:**      James Lian  
**Email:**      james.lian@sc.com

***


