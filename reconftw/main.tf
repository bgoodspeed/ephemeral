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
variable "target_domain" {}

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
  name       = "ephemeral-reconftw-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y git docker.io docker-compose
  - docker pull six2dez/reconftw:main 
  - echo ${base64encode(file("${path.module}/reconftw.cfg"))} | base64 --decode > reconftw.cfg
  - echo ${base64encode(file("${path.module}/run-target.sh"))} | base64 --decode > orig-run-target.sh 
  - cat orig-run-target.sh | sed 's/AUTOMATICALLYREPLACED/${var.target_domain}/' > run-target.sh
  - mkdir Recon 
  - bash run-target.sh
 
EOF
}

resource "digitalocean_droplet" "reconftw" {
  image    = "ubuntu-24-10-x64"
  name     = "reconftw-1"
  region   = "nyc3"
  size     = "s-2vcpu-2gb" # slightly more powerful to deal with the containers
  tags = ["ephemeral", "reconftw", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered

}

output "instance_ip_address" {
   value = digitalocean_droplet.reconftw.ipv4_address
}


