terraform {
  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# Set this in your .tfvars file or with -var
variable "vultr_api_key" {}

provider "vultr" {
  api_key = var.vultr_api_key
}

locals {
  cleaned_path    = replace(path.cwd, "/", ":")
  working_dir_tag = "ephemeral-dir::${local.cleaned_path}"
}

module "ssh_keygen" {
  source = "../modules/ssh_keygen"
}

resource "vultr_ssh_key" "default" {
  name    = "ephemeral-service-key"
  ssh_key = module.ssh_keygen.public_key
}

data "template_file" "provisioner_script" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update
  - echo "do what you need to do to setup your box"
EOF
}

resource "vultr_instance" "service" {
  region      = "ewr"        # Newark, NJ (example)
  plan        = "vc2-1c-1gb" # 1 CPU, 1 GB RAM (example)
  os_id       = 2284          # Ubuntu 24.04 (example ID)
  label       = "service-1"
  ssh_key_ids = [vultr_ssh_key.default.id]
  user_data   = data.template_file.provisioner_script.rendered

  tags = ["ephemeral", "service", local.working_dir_tag]
}

output "instance_ip_address" {
  value = vultr_instance.service.main_ip
}
