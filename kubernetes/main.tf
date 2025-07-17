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
variable "kubeadm_token" {}

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
  name       = "ephemeral-kubernetes-key"
  public_key = module.ssh_keygen.public_key
}

data "template_file" "provisioner_script_worker" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - wget https://raw.githubusercontent.com/killer-sh/cks-course-environment/refs/heads/master/cluster-setup/latest/install_worker.sh
  - bash install_worker.sh 
  - touch /worker_installed.txt
EOF
}

resource "digitalocean_droplet" "worker" {
  image    = "ubuntu-24-04-x64"
  name     = "kubernetes-worker"
  region   = "nyc3"
  size     = "s-2vcpu-2gb"
  tags = ["ephemeral", "kubernetes", "kubernetes-worker", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script_worker.rendered

}


data "template_file" "provisioner_script_master" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - wget https://raw.githubusercontent.com/killer-sh/cks-course-environment/refs/heads/master/cluster-setup/latest/install_master.sh
  - bash install_master.sh 
  - touch /master_installed.txt
  - kubeadm token create ${var.kubeadm_token}
  - touch /token_created.txt
EOF
}

resource "digitalocean_droplet" "master" {
  image    = "ubuntu-24-04-x64"
  name     = "kubernetes-master"
  region   = "nyc3"
  size     = "s-2vcpu-2gb"
  tags = ["ephemeral", "kubernetes", "kubernetes-master", local.working_dir_tag]
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = data.template_file.provisioner_script_master.rendered

}
output "instance_ip_address" {
   value = digitalocean_droplet.master.ipv4_address
}


output "instance_ip_address_master" {
   value = digitalocean_droplet.master.ipv4_address
}

output "instance_ip_address_worker" {
   value = digitalocean_droplet.worker.ipv4_address
}

resource "null_resource" "wait_for_master_ready" {
  depends_on = [digitalocean_droplet.master]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.master.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /token_created.txt ]; do echo 'waiting for master token...'; sleep 15; done"
    ]
  }
}

resource "null_resource" "wait_for_worker_ready" {
  depends_on = [digitalocean_droplet.master]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.worker.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /worker_installed.txt ]; do echo 'waiting for worker install...'; sleep 15; done"
    ]
  }
}

resource "null_resource" "join_worker_to_master" {
  depends_on = [ null_resource.wait_for_master_ready, null_resource.wait_for_worker_ready]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.worker.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "kubeadm join ${digitalocean_droplet.master.ipv4_address}:6443 --token ${var.kubeadm_token} --discovery-token-unsafe-skip-ca-verification"
    ]
  }
}

resource "null_resource" "extract_kubeconfig" {
  depends_on = [null_resource.join_worker_to_master] 
  provisioner "local-exec" {
    command = "scp -o StrictHostKeyChecking=no -i ${module.ssh_keygen.private_key_pem_path} root@${digitalocean_droplet.master.ipv4_address}:/etc/kubernetes/admin.conf ./kubeconfig"
  }
}

