terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Set the variable values in *.tfvars file
# or using -var="do_token=..." CLI option
variable "do_token" {}

# Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

module "ssh_keygen" {
  source = "../modules/ssh_keygen"
  providers = {
    digitalocean = digitalocean
  }
}

resource "digitalocean_ssh_key" "default" {
  name       = "ephemeral-caido-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "userdata_provision_caido" {
  template = <<EOF
#cloud-config
runcmd:
  - mkdir /caido
  - cd /caido 
  - wget https://caido.download/releases/v0.48.1/caido-cli-v0.48.1-linux-x86_64.tar.gz
  - tar -xzf caido-cli-v0.48.1-linux-x86_64.tar.gz
  - nohup ./caido-cli & 
EOF
}

resource "digitalocean_droplet" "caido" {
  image    = "ubuntu-24-10-x64"
  name     = "caido-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags     = ["ephemeral", "caido"]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.userdata_provision_caido.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.caido.ipv4_address
}


