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

variable "vultr_api_key" {}
variable "vultr_provisioned_username" {
  description = "Password for the provisioned Windows local admin account"
  type        = string
  sensitive   = true

}
variable "vultr_provisioned_password" {
  description = "Username for the provisioned Windows local admin account"
  type        = string
  default     = "redteam"
}

provider "vultr" {
  api_key = var.vultr_api_key
}

locals {
  cleaned_path    = replace(path.cwd, "/", ":")
  working_dir_tag = "ephemeral-dir::${local.cleaned_path}"
}


resource "vultr_instance" "windows_service" {
  region = "ewr"            # Newark, NJ
  plan   = "vc2-1c-2gb"      # Minimum viable for Windows
  os_id  = 501              # run ./list-os.sh APIKEY...VALUE
  label  = "windows-service-1"
  tags = ["ephemeral", "windows", local.working_dir_tag]
}

output "windows_instance_ip_address" {
  value = vultr_instance.windows_service.main_ip
}

output "windows_instance_label" {
  value = vultr_instance.windows_service.label
}

output "windows_instance_region" {
  value = vultr_instance.windows_service.region
}

