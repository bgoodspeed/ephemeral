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
locals {
  cleaned_path = replace(path.cwd, "/", ":")
  working_dir_tag = "ephemeral-dir::${local.cleaned_path}"
}

resource "digitalocean_ssh_key" "default" {
  name       = "default ssh key"
  public_key = file(local.ssh_keyfile_public)
}


resource "digitalocean_droplet" "jump1" {
  image    = "ubuntu-24-10-x64"
  name     = "jump-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags     = ["ephemeral", "jumps", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
}

resource "digitalocean_droplet" "jump2" {
  image    = "ubuntu-24-10-x64"
  name     = "jump-2"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags     = ["ephemeral", "jumps", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
}
resource "digitalocean_droplet" "jump3" {
  image    = "ubuntu-24-10-x64"
  name     = "jump-3"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags     = ["ephemeral", "jumps", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]
}
output "instance_ip_addresses" {
   value = [digitalocean_droplet.jump1.ipv4_address,
            digitalocean_droplet.jump2.ipv4_address,
            digitalocean_droplet.jump3.ipv4_address]
}


