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
   default = "keycloak"
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
  name       = "ephemeral-keycloak-key"
  public_key = module.ssh_keygen.public_key
}



data "template_file" "userdata_provision_certbotsslkeycloak" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y nginx certbot python3-certbot-nginx python3-certbot-dns-digitalocean unzipopenjdk-21-jdk
  - mkdir -p /scripts/static
  - mkdir -p /root/.secrets/certbot 
  - echo "dns_digitalocean_token = ${var.do_token}" > /root/.secrets/certbot/digitalocean.ini 
  - chmod 600 /root/.secrets/certbot/digitalocean.ini
  - certbot certonly --dns-digitalocean --dns-digitalocean-credentials /root/.secrets/certbot/digitalocean.ini -d ${var.subdomain}.${var.managed_domain} --agree-tos --email ${var.certbot_email}
  - wget https://github.com/keycloak/keycloak/releases/download/26.3.2/keycloak-26.3.2.zip
  - unzip keycloak-26.3.2.zip 
  - echo ${base64encode(file("${path.module}/startup.sh"))} | base64 --decode > startup_raw.sh
  - cat startup_raw.sh | sed 's/AUTOMATICALLYREPLACED/${var.subdomain}.${var.managed_domain}/' > startup.sh 
  - echo "TODO figure out how to automate the rest of the configuration and initial bootstrapping of users etc" > TODO.txt 
EOF
}

# /etc/letsencrypt/live/<subdomain>.<domain> will have the certs
resource "digitalocean_record" "certbotsslkeycloak" {
  domain = var.managed_domain
  type   = "A"
  name   = var.subdomain
  value  = digitalocean_droplet.certbotsslkeycloak.ipv4_address
  ttl    = 300
}


resource "digitalocean_droplet" "certbotsslkeycloak" {
  image    = "ubuntu-24-10-x64"
  name     = "certbotsslkeycloak-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = ["ephemeral", "certbotsslkeycloak", local.working_dir_tag]

  user_data = data.template_file.userdata_provision_certbotsslkeycloak.rendered
}


output "instance_ip_address" {
   value = digitalocean_droplet.certbotsslkeycloak.ipv4_address
}


