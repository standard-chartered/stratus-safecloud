output "image_id" {
    value = "${data.aws_ami.ubuntu.id}"
}

output "instance_ip" {
    value = aws_instance.vamp-ec2.public_ip
}

output "elastic_ip" {
    value = aws_eip.fixed_ip.public_ip
}
