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
  name       = "ephemeral-flask-key"
  public_key = module.ssh_keygen.public_key
}



data "template_file" "userdata_provision_listener" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y python3-flask
  - mkdir -p /scripts/static
  - echo ${base64encode(file("${path.module}/server.pem"))} | base64 --decode > /scripts/server.pem 
  - echo ${base64encode(file("${path.module}/https_server.py"))} | base64 --decode > /scripts/https_server.py 
  - echo ${base64encode(file("${path.module}/http_server.py"))} | base64 --decode > /scripts/http_server.py 
  - nohup python3 /scripts/https_server.py &
  - nohup python3 /scripts/http_server.py &
EOF
}

resource "digitalocean_droplet" "listener" {
  image    = "ubuntu-24-10-x64"
  name     = "listener-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = ["ephemeral", "flask", local.working_dir_tag]

  user_data = data.template_file.userdata_provision_listener.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.listener.ipv4_address
}


