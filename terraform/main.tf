# Security Group
resource "aws_security_group" "sg_22" {
  name = "sg_22"
  vpc_id = aws_vpc.vpc.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
  }
 egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Environment = var.environment_tag
  }
}

# AWS Key Pair
resource "aws_key_pair" "ec2key" {
  key_name = "VampKeyPair"
  public_key = file(var.public_key_path)
}

# AWS EC2 Instance
resource "aws_instance" "vamp-ec2" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.subnet_public.id
  vpc_security_group_ids = [aws_security_group.sg_22.id]
  key_name               = aws_key_pair.ec2key.key_name
  tags = {
   Environment = var.environment_tag
   Name        = "Vamp"
  }
  root_block_device {
    encrypted = "true"
  }
  
  # Copy over the public and private keys we'll use to 
  # connect to github 
  provisioner "file" {
    source      = var.ssh_pub_github_source
    destination = "/home/ubuntu/.ssh/aws-bb.pub"
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      private_key  = file(var.ec2_pem_file)
    }
  } 
  provisioner "file" {
    source      = var.ssh_private_github_source
    destination = "/home/ubuntu/.ssh/aws-bb"
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      private_key  = file(var.ec2_pem_file)
    }
  } 
  
  # Copy over AWS credentials and config files
  provisioner "remote-exec" {
    inline = [
      "mkdir /home/ubuntu/.aws"
    ]
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      agent        = false
      private_key  = file(var.ec2_pem_file)
    }
  }
  provisioner "file" {
    source      = var.aws_config_file_source
    destination = "/home/ubuntu/.aws/config"
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      private_key  = file(var.ec2_pem_file)
    }
  }   
  provisioner "file" {
    source      = var.aws_credentials_file_source
    destination = "/home/ubuntu/.aws/credentials"
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      private_key  = file(var.ec2_pem_file)
    }
  } 
  
  # Copy over the install.sh file which we'll use to provision
  # the EC2 instance
  provisioner "file" {
    source      = var.vamp_installation_script
    destination = "/home/ubuntu/install-vamp.sh"
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      private_key  = file(var.ec2_pem_file)
    }
  } 
  
  # chmod +x install.sh
  provisioner "remote-exec" {
    inline = [
      "chmod +x /home/ubuntu/install-vamp.sh",
    ]
    connection {
      type         = "ssh"
      host         = self.public_ip
      user         = "ubuntu"
      agent        = false
      private_key  = file(var.ec2_pem_file)
    }
  }
}

# Create an AWS Elastic IP for the instance
resource "aws_eip" "fixed_ip" {
    instance = aws_instance.vamp-ec2.id
    vpc      = true
}



