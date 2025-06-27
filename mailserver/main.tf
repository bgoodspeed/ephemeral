terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }

  }

}

# Set the variable values in *.tfvars file
# or using -var="do_token=..." CLI option
variable "do_token" {}
variable "web_username" {}
variable "web_password" {}

# Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}


resource "tls_private_key" "generated" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "private_key_pem" {
  content         = tls_private_key.generated.private_key_pem
  filename        = "${path.module}/id_rsa.pem"
  file_permission = "0600"
}

resource "local_file" "public_key_openssh" {
  content         = tls_private_key.generated.public_key_openssh
  filename        = "${path.module}/id_rsa.pub"
  file_permission = "0644"
}

resource "digitalocean_ssh_key" "default" {
  name       = "from-tls-key"
  public_key = tls_private_key.generated.public_key_openssh
}

resource "null_resource" "convert_key" {
  provisioner "local-exec" {
    command = "${path.module}/convert_to_openssh.sh"
  }

  triggers = {
    pem_checksum = sha256(local_file.private_key_pem.content)
  }
}


data "template_file" "userdata_provision_mailserver" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y podman-docker
  - docker run -p 11080:1080 -p 11025:1025 docker.io/maildev/maildev --verbose --log-mail-contents --web-user "${var.web_username}" --web-pass "${var.web_password}" | tee console.log
 
EOF
}

resource "digitalocean_droplet" "mailserver" {
  image    = "ubuntu-24-10-x64"
  name     = "mailserver-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.userdata_provision_mailserver.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.mailserver.ipv4_address
}


