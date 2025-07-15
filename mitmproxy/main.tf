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
  name       = "ephemeral-mitmproxy-key"
  public_key = module.ssh_keygen.public_key
}


data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt -y install python3-venv
  - echo ${base64encode(file("${path.module}/install-mitmproxy-with-venv.sh"))} | base64 --decode > install-mitmproxy-with-venv.sh
  - chmod +x install-mitmproxy-with-venv.sh
  - ./install-mitmproxy-with-venv.sh
  - echo ${base64encode(file("${path.module}/run-mitmproxy-with-venv.sh"))} | base64 --decode > run-mitmproxy-with-venv.sh
  - chmod +x run-mitmproxy-with-venv.sh
  - ./run-mitmproxy-with-venv.sh
 
EOF
}

resource "digitalocean_droplet" "mitmproxy" {
  image    = "ubuntu-24-10-x64"
  name     = "mitmproxy-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  tags = ["ephemeral", "mitmproxy", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script.rendered
}

resource "null_resource" "wait_for_ready" {
  depends_on = [digitalocean_droplet.mitmproxy]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.mitmproxy.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /mitm.token ]; do echo 'waiting for token...'; sleep 15; done"
    ]
  }
}

resource "null_resource" "extract_mitm_token" {
  depends_on = [digitalocean_droplet.mitmproxy, null_resource.wait_for_ready]

  provisioner "local-exec" {
    command = <<EOT
scp -o StrictHostKeyChecking=no -i id_rsa root@${digitalocean_droplet.mitmproxy.ipv4_address}:/mitm.token ${path.module}/mitm.token
EOT
  }
}




output "instance_ip_address" {
   value = digitalocean_droplet.mitmproxy.ipv4_address
}


