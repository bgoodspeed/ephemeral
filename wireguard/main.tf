terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Set the variable value in *.tfvars file
# or using -var="do_token=..." CLI option
variable "do_token" {}

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

resource "digitalocean_ssh_key" "default" {
  name       = "ssh key for access to droplet"
  public_key = file(local.ssh_keyfile_public)
}

data "template_file" "userdata_provision_wireguard" {
  template = <<EOF
#cloud-config
runcmd:
  - apt install -y wireguard wireguard-tools
  - sysctl net.ipv4.ip_forward=1
  - echo ${base64encode(file("${path.module}/server.conf"))} | base64 --decode > /etc/wireguard/wg0.conf 
  - echo ${base64encode(file("${path.module}/peer.conf"))} | base64 --decode > /root/peer.conf 
  - wg-quick up wg0
  - wg setconf wg0 /root/peer.conf 
EOF
}


#- wg-quick up wg0
resource "digitalocean_droplet" "wireguard" {
  image    = "ubuntu-24-10-x64"
  name     = "wireguard-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]

  user_data = data.template_file.userdata_provision_wireguard.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.wireguard.ipv4_address
}


