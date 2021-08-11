# variables.tf

# VPC related variables

variable "region" {
     default = "ap-southeast-1"
}

variable "availabilityZone" {
     default = "ap-southeast-1a"
}

variable "environment_tag" {
  description = "Environment tag"
  default = "Development"
}

variable "cidr_vpc" {
  description = "CIDR block for the VPC"
  default = "10.1.0.0/16"
}

variable "cidr_subnet" {
  description = "CIDR block for the subnet"
  default = "10.1.0.0/24"
}

variable "availability_zone" {
  description = "availability zone to create subnet"
  default = "ap-southeast-1a"
}

# Installation related variables

variable "ec2_pem_file" {
  description = "Location of pem file to access the ec2 instance"
  default = "/home/jim/.ssh/aws-ec2.pem"
}

variable "ssh_pub_github_source" {
  description = "Location of SSH key pub file for access to github"
  default = "/home/jim/.ssh/aws-bb.pub"
}

variable "ssh_private_github_source" {
  description = "Location of SSH key private file for access to github"
  default = "/home/jim/.ssh/aws-bb"
}

variable "aws_config_file_source" {
  description = "Location of aws config file"
  default = "/home/jim/.aws/config"
}

variable "aws_credentials_file_source" {
  description = "Location of aws credentials file"
  default = "/home/jim/.aws/credentials"
}

variable "vamp_installation_script" {
  description = "Location of application installation script"
  default = "/home/jim/Workspace/ssc/terraform/install-vamp.sh"
}

# EC2 related variables

variable "public_key_path" {
  description = "Public key path"
  default = "~/.ssh/aws-ec2.pub"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

variable instance_type {
  description = "AWS EC2 instance type"
  default = "t2.micro"
}

variable instance_count {
  description = "Number of EC2 instances to create"
  default = "1"
}


