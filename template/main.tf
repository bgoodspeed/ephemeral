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
  name       = "ephemeral-service-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - echo "do what you need to do to setup your box"
 
EOF
}

resource "digitalocean_droplet" "service" {
  image    = "ubuntu-24-10-x64"
  name     = "service-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags = ["ephemeral", "service", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered

}

output "instance_ip_address" {
   value = digitalocean_droplet.service.ipv4_address
}


