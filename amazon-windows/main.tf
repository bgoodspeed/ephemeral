terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

variable "aws_region" {
  default = "us-east-1"
}

variable "aws_secret_access_key" {
  description = "aws secret access key"
  type        = string
}
variable "aws_access_key" {
  description = "aws access key"
  type        = string
}
variable "provisioned_username" {
  description = "Username for the provisioned Windows local admin account"
  type        = string
  default     = "redteam"
}

variable "provisioned_password" {
  description = "Password for the provisioned Windows local admin account"
  type        = string
  sensitive   = true
}

provider "aws" {
  region = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_access_key
}

locals {
  cleaned_path    = replace(path.cwd, "/", ":")
  working_dir_tag = "ephemeral-dir::${local.cleaned_path}"
}
data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "windows_rdp" {
  name        = "allow-rdp"
  description = "Allow RDP access from anywhere (use your IP for better security)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "RDP"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # For public testing, restrict to your IP if desired
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "windows_service" {
  ami                         = "ami-0345f44fe05216fc4" # Example for Windows Server 2022 in us-east-1; update for your region
  instance_type               = "t3.medium" # TODO free tier?
  associate_public_ip_address  = true

  vpc_security_group_ids       = [aws_security_group.windows_rdp.id]
  tags = {
    Name = "windows-service-1"
    Environment = "ephemeral"
    WorkingDirTag = local.working_dir_tag
  }

  user_data = <<EOF
<powershell>
New-LocalUser -Name "${var.provisioned_username}" -Password (ConvertTo-SecureString "${var.provisioned_password}" -AsPlainText -Force)
Add-LocalGroupMember -Group "Administrators" -Member "${var.provisioned_username}"
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
</powershell>
EOF
}

output "windows_instance_ip_address" {
  value = aws_instance.windows_service.public_ip
}

output "windows_instance_id" {
  value = aws_instance.windows_service.id
}

output "aws_region" {
  value = var.aws_region
}

