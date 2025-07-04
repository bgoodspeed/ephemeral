terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Set the variable values in *.tfvars file
# or using -var="do_token=..." CLI option
variable "do_token" {}
variable "admin_password" {}


variable "realm" {
  description = "The kerberos realm for AD - edit openssl-ldap.conf to match"
  type = string 
  default = "inthebg.cloud"
}

variable "domain" {
  description = "The AD domain"
  type = string 
  default = "INTHEBG"
}

# Configure the DigitalOcean Provider
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
  name       = "ephemeral-samba-ad-key"
  public_key = module.ssh_keygen.public_key
}




data "template_file" "userdata_provision_sambad" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - echo "krb5-config krb5-config/default_realm string ${var.realm}" | debconf-set-selections
  - DEBIAN_FRONTEND=noninteractive apt install -y samba-dsdb-modules samba krb5-config winbind smbclient libldb2 libldb-dev samba-ad-provision samba-ad-dc ldap-utils crudini
  - mv /etc/samba/smb.conf /etc/samba/smb.conf.old
  - echo "${var.realm}" > realm.txt 
  - echo "${var.admin_password}" > passwd.txt 
  - echo "${var.domain}" > domain.txt
  - curl http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address -o public_ip.txt
  - samba-tool domain provision --use-rfc2307 --realm=${var.realm} --domain=${var.domain} --adminpass="${var.admin_password}" --server-role=dc --dns-backend=SAMBA_INTERNAL  
  - mkdir /sambad
  - mkdir -p /etc/samba/tls 
  - mkdir -p /var/log/samba/ldap 
  - echo ${base64encode(file("${path.module}/openssl-ldap.conf"))} | base64 --decode > /etc/samba/tls/openssl-ldap.conf
  - openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/samba/tls/ldap.key -out /etc/samba/tls/ldap.crt -config /etc/samba/tls/openssl-ldap.conf
  - sed 's/^[[:space:]]*//' /etc/samba/smb.conf > /tmp/smb-clean.conf
  - crudini --set /tmp/smb-clean.conf global "tls certfile" /etc/samba/tls/ldap.crt
  - crudini --set /tmp/smb-clean.conf global "tls keyfile" /etc/samba/tls/ldap.key
  - crudini --set /tmp/smb-clean.conf global "tls cafile" /etc/samba/tls/ldap.crt
  - crudini --set /tmp/smb-clean.conf global "log level" 5
  - crudini --set /tmp/smb-clean.conf global "log file" /var/log/samba/ldap/query.log
  - crudini --set /tmp/smb-clean.conf global "max log size" 10000
  - cp /tmp/smb-clean.conf /etc/samba/smb.conf
  - systemctl stop smbd nmbd winbind
  - systemctl unmask samba-ad-dc
  - systemctl enable --now samba-ad-dc

EOF
}

resource "digitalocean_droplet" "sambad" {
  image    = "ubuntu-24-10-x64"
  name     = "sambad-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = ["ephemeral", "samba-ad", local.working_dir_tag]
  user_data = data.template_file.userdata_provision_sambad.rendered
}

output "instance_ip_address" {
   value = digitalocean_droplet.sambad.ipv4_address
}


