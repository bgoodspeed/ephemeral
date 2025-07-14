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
  name       = "ephemeral-sliver-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - curl -sSL https://sliver.sh/install | bash
  - sleep 10
  - mkdir -p /opt/sliver
  - cp /root/sliver-server /opt/sliver/
  - useradd --system --shell /usr/sbin/nologin sliver
  - /opt/sliver/sliver-server &
  - /opt/sliver/sliver-server operator --name redteam --lhost "$(hostname -I | awk '{print $1}')" --save /opt/sliver/redteam.cfg
  - echo ${base64encode(file("${path.module}/sliver.service"))} | base64 --decode > /etc/systemd/system/sliver.service 
  - systemctl daemon-reexec
  - systemctl enable sliver
  - systemctl start sliver
 
EOF
}

resource "digitalocean_droplet" "sliver" {
  image    = "ubuntu-24-10-x64"
  name     = "sliver-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags = ["ephemeral", "sliver", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered

}

resource "null_resource" "wait_for_ready" {
  depends_on = [digitalocean_droplet.sliver]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.sliver.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /opt/sliver/redteam.cfg ]; do echo 'waiting...'; sleep 15; done"
    ]
  }
}

resource "null_resource" "extract_sliver_config" {
  depends_on = [digitalocean_droplet.sliver, null_resource.wait_for_ready]

  provisioner "local-exec" {
    command = <<EOT
scp -o StrictHostKeyChecking=no -i id_rsa root@${digitalocean_droplet.sliver.ipv4_address}:/opt/sliver/redteam.cfg ${path.module}/redteam.cfg
EOT
  }
}



output "instance_ip_address" {
   value = digitalocean_droplet.sliver.ipv4_address
}


