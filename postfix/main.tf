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
variable "spoofed_to" {}
variable "spoofed_from" {}

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
  name       = "ephemeral-postfix-key"
  public_key = module.ssh_keygen.public_key
}

data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - echo "postfix postfix/main_mailer_type string 'Internet Site'" | debconf-set-selections
  - echo "postfix postfix/mailname string postfix-1.local" | debconf-set-selections
  - DEBIAN_FRONTEND=noninteractive apt-get install -y postfix
  - echo "smtpd_forbid_unauth_pipelining = no" | sudo tee -a /etc/postfix/main.cf
  - echo ${base64encode(file("${path.module}/spoof-email.sh"))} | base64 --decode > /spoof-email-raw.sh
  - cat /spoof-email-raw.sh | sed 's/SPOOFEDEMAILFROM/${var.spoofed_from}/' | sed 's/SPOOFEDEMAILTO/${var.spoofed_to}/' > /spoof-email.sh 

EOF
}

resource "digitalocean_droplet" "postfix" {
  image    = "ubuntu-24-10-x64"
  name     = "postfix-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags = ["ephemeral", "postfix", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered

}

output "instance_ip_address" {
   value = digitalocean_droplet.postfix.ipv4_address
}


