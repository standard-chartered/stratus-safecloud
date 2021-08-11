[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)


# Stratus SafeCloud

## Introduction
This application regularly interrogates the various AWS Accounts used by individual Venture Projects 
to assess the security score as measured against:

* AWS Foundational Security Best Practices v1.0.0
* CIS AWS Foundations Benchmark v1.2.0

As well as providing an overall security score for each AWS Account, this portal also allows you to 
drill down into the exact details of each of the checks that are carrtied out and, for failed
tests, provides a link to the official AWS remediation guides for each failure.

This project also allows you to see exactly what AWS resources your account is using.

## Prerequistes
* python 3
* mysqldb (if needed)
* understanding of dotenv https://github.com/theskumar/python-dotenv

## Starting Dev Server
1. copy the .env file from env folder to the root folder of this directory
2. configure the environment variables in the .env file
3. create a virtual python environment https://docs.python.org/3/library/venv.html
4. run the app script
```
  python app.py
```

## Setting up accounts
1. start the app server and add a project
2. run the udpate.py script to download the details about your aws project


## Deployment and Installation

### Before runnning the terraform scripts
Before running the terraform scripts, you need to do the following:
* Ensure that your SSH keys are located in the directories specified in the variables.tf file
```
variable "ssh_pub_github_source" {
  description = "Location of SSH key pub file for access to github"
  default = "/home/jim/.ssh/aws-bb.pub"
}

variable "ssh_private_github_source" {
  description = "Location of SSH key private file for access to github"
  default = "/home/jim/.ssh/aws-bb"
}
```
* Ensure that you have your aws config and credentials files in the directory specified in the variables.tf file
```
variable "aws_config_file_source" {
  description = "Location of aws config file"
  default = "/home/jim/.aws/config"
}

variable "aws_credentials_file_source" {
  description = "Location of aws credentials file"
  default = "/home/jim/.aws/credentials"
}
```
* Create a key pair in PEM format as described in Option 2 of this page: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
* Ensure that the key pair files are stored in the directory specified in the variables.tf file
```
variable "ec2_pem_file" {
  description = "Location of pem file to access the ec2 instance"
  default = "/home/jim/.ssh/aws-ec2.pem"
}
```
* Ensure that you are using the desired AWS profile as specified in providers.tf
```
provider "aws" {
  region                  = "ap-southeast-1"
  shared_credentials_file = var.aws_credentials_file_source
  profile                 = "desired_aws_profile"
}
```
Note that you can test these terraform scripts by specifying your own personal AWS account profile to deploy a test version of the application
in your own personal AWS account.

* Ensure that you have a local copy of the required access and secret access keys:
In order to access the AWS accounts, you need to have the following files on your local machine:

  * ~/.aws/config
  * ~/.aws/credentials

These files should contain the AWS access and AWS secret access keys and will be copied over by the 
terraform script from your local ~/.aws directory to the ec2 instance.

For obvious reasons, these access key files files are NOT included in the code repo.

### How to use the terraform scripts
This directory contains terraform scripts needed to create the AWS infrastructure required for running the application.

Infrastructure consists of:
* VPC
* Subnet inside VPC
* Internet gateway associated with VPC
* Route Table inside VPC with a route that directs internet-bound traffic to the internet gateway
* Route table association with our subnet to make it a public subnet
* Security group inside VPC
* Key pair used for SSH access
* EC2 instance inside our public subnet with an associated security group and a generated key pair

Once you have made the required changes described in the previous section, simply do the following:
```
$ cd ~/Workspace/ssc/terraform
$ terraform init
$ terraform plan
$ terraform apply
```

### Installing the application
You need to SSH onto the EC2 instance and then run the ~/install-vamp.sh script.
This script does the following:
* updates the package lists for upgrades for linux packages 
  that need upgrading, as well as new packages that have just come to the repositories 
* Installs python3 virtualenv
* Installs python3 pip
* Installs authbind
* Creates the required directory structure
* Pulls in the application code from BitBucket
* Creates the required virtualenv 
* installs all the required python modules
* Runs the data collection script for the first time
* Starts the application

Once the installation script has completed, you can view the application here:

http://\<instance-ip-address\>:5000

## Setting up a cron job for data collection
Use the command crontab -e to create the cron job which should look like this:

    # Edit this file to introduce tasks to be run by cron.
    # 
    # Each task to run has to be defined through a single line
    # indicating with different fields when the task will be run
    # and what command to run for the task
    # 
    # To define the time you can provide concrete values for
    # minute (m), hour (h), day of month (dom), month (mon),
    # and day of week (dow) or use '*' in these fields (for 'any').
    # 
    # Notice that tasks will be started based on the cron's system
    # daemon's notion of time and timezones.
    # 
    # Output of the crontab jobs (including errors) is sent through
    # email to the user the crontab file belongs to (unless redirected).
    # 
    # For example, you can run a backup of all your user accounts
    # at 5 a.m every week with:
    # 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
    # 
    # For more information see the manual pages of crontab(5) and cron(8)
    # 
    # m h  dom mon dow   command
    MAILTO=""
    CRON_TZ=Asia/Singapore
    USER='ubuntu'
    0 0 * * * /home/ubuntu/Workspace/ssc/update.sh > /home/ubuntu/Workspace/ssc/update.log 2>&1

The above example will set the cron job to run at midnight each day (using Singapore timezone)

Note that cron is a bit weird when it comes to timezones.  You may need to set the *server* timezone:

    $ sudo ln -sf /usr/share/zoneinfo/Asia/Singapore /etc/localtime

## Destroying the infrastructure
To destroy the AWS infrastructure, simply do the following:
```shell script
$ cd terraform
$ terraform destroy
```
This will delete all the AWS resources created by the terraform apply command.

## Issues or Questions
If you have any issues or concerns about the application or suggestions as to how 
it could be improved, please do nto hesitate to contact me.

**Name:**      James Lian

**Email:**      james.lian@sc.com

***


