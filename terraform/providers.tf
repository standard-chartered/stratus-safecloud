provider "aws" {
  region                  = "ap-southeast-1"
  shared_credentials_file = var.aws_credentials_file_source
  profile                 = "SCVTooling"
}
