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
  name       = "ephemeral-ansible-key"
  public_key = module.ssh_keygen.public_key
}

resource "null_resource" "wait_for_ready" {
  depends_on = [digitalocean_droplet.ansible]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.ansible.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /etc/passwd ]; do echo 'waiting for ssh...'; sleep 15; done"
    ]
  }
}


resource "digitalocean_droplet" "ansible" {
  image    = "ubuntu-24-10-x64"
  name     = "ansible-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags = ["ephemeral", "ansible", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]
}
resource "null_resource" "ansible" {
  depends_on = [digitalocean_droplet.ansible, null_resource.wait_for_ready]

  provisioner "local-exec" {
    command = <<EOT
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
  -i '${digitalocean_droplet.ansible.ipv4_address},' \
  -u root \
  --private-key ${module.ssh_keygen.private_key_pem_path} \
  ./playbook.yml
EOT
  }
}

output "instance_ip_address" {
   value = digitalocean_droplet.ansible.ipv4_address
}


