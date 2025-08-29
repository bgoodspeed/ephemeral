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
variable "managed_domain" {}
variable "certbot_email" {}

variable "subdomain" {
   type = string
   default = "listener"
}
# Configure the DigitalOcean Provider
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
  name       = "ephemeral-validdns-key"
  public_key = module.ssh_keygen.public_key
}



data "template_file" "userdata_provision_validdns" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y python3-venv certbot python3-certbot-nginx python3-certbot-dns-digitalocean
  - mkdir -p /root/.secrets/certbot 
  - echo "dns_digitalocean_token = ${var.do_token}" > /root/.secrets/certbot/digitalocean.ini 
  - chmod 600 /root/.secrets/certbot/digitalocean.ini
EOF
}


resource "digitalocean_record" "validdns" {
  domain = var.managed_domain
  type   = "A"
  name   = var.subdomain
  value  = digitalocean_droplet.validdns.ipv4_address
  ttl    = 300
}


resource "digitalocean_droplet" "validdns" {
  image    = "ubuntu-24-10-x64"
  name     = "validdns-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = ["ephemeral", "validdns", local.working_dir_tag]

  user_data = data.template_file.userdata_provision_validdns.rendered
}


output "instance_ip_address" {
   value = digitalocean_droplet.validdns.ipv4_address
}


