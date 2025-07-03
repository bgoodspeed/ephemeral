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

# Set the variable values in *.tfvars file, or using -var="do_token=..." CLI option
variable "do_token" {}
variable "web_username" {}
variable "web_password" {}

provider "digitalocean" {
  token = var.do_token
}
locals {
  cleaned_path = replace(path.cwd, "/", ":")
  working_dir_tag = "ephemeral-dir::${local.cleaned_path}"
}

module "ssh_keygen" {
  source = "../modules/ssh_keygen"
  providers = {
    digitalocean = digitalocean
  }
}

resource "digitalocean_ssh_key" "default" {
  name       = "ephemeral-mailserver-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "provisioner_script" {
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
  tags = ["ephemeral", "mailserver", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.mailserver.ipv4_address
}


