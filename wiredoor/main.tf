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

variable "ssh_keyfile" {
  description = "The path to the SSH keyfile"
  type        = string
  default     = "~/.ssh/id_rsa"
}

locals {
    ssh_keyfile_public = "${var.ssh_keyfile}.pub"
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
  name       = "ephemeral-service-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "userdata_provision_wiredoor" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y git docker.io docker-compose
  - mkdir /wiredoor
  - cd /wiredoor 
  - git clone https://github.com/wiredoor/docker-setup.git
  - curl http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address -o /tmp/public_ip
  - echo ${base64encode(file("${path.module}/.env"))} |  base64 --decode > docker-setup/.env_initial
  - cat docker-setup/.env_initial | sed "s/AUTOMATICALLYREPLACED/wiredoor.${var.managed_domain}/" > docker-setup/.env
  - cd docker-setup 
  - docker-compose up -d 
EOF
}

resource "digitalocean_droplet" "wiredoor" {
  image    = "ubuntu-24-10-x64"
  name     = "wiredoor-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags     = ["ephemeral", "wiredoor", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.userdata_provision_wiredoor.rendered
}

resource "digitalocean_record" "wiredoor" {
  domain = var.managed_domain
  type   = "A"
  name   = "wiredoor"
  value  = digitalocean_droplet.wiredoor.ipv4_address
  ttl    = 300
}


resource "digitalocean_record" "service" {
  domain = var.managed_domain
  type   = "A"
  name   = "service"
  value  = digitalocean_droplet.wiredoor.ipv4_address
  ttl    = 300
}

output "instance_ip_address" {
   value = digitalocean_droplet.wiredoor.ipv4_address
}


