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
variable "managed_domain" {}
variable "certbot_email" {}

variable "subdomain" {
   type = string
   default = "listener"
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
  name       = "ephemeral-flask-key"
  public_key = module.ssh_keygen.public_key
}



data "template_file" "userdata_provision_certbotssllistener" {
  template = <<EOF
#cloud-config
runcmd:
  - apt update 
  - apt install -y python3-flask nginx certbot python3-certbot-nginx python3-certbot-dns-digitalocean
  - mkdir -p /scripts/static
  - echo ${base64encode(file("${path.module}/http_server.py"))} | base64 --decode > /scripts/http_server.py 
  - nohup python3 /scripts/http_server.py &
  - rm /etc/nginx/sites-enabled/default 
  - echo ${base64encode(file("${path.module}/flaskapp.nginx"))} | base64 --decode > /tmp/flaskapp.nginx.raw
  - cat /tmp/flaskapp.nginx.raw | sed 's/AUTOMATICALLYREPLACED/${var.subdomain}.${var.managed_domain}/' > /etc/nginx/sites-available/flaskapp
  - ln -s /etc/nginx/sites-available/flaskapp /etc/nginx/sites-enabled
  - mkdir -p /root/.secrets/certbot 
  - echo "dns_digitalocean_token = ${var.do_token}" > /root/.secrets/certbot/digitalocean.ini 
  - chmod 600 /root/.secrets/certbot/digitalocean.ini
EOF
}


resource "digitalocean_record" "certbotssllistener" {
  domain = var.managed_domain
  type   = "A"
  name   = var.subdomain
  value  = digitalocean_droplet.certbotssllistener.ipv4_address
  ttl    = 300
}


resource "digitalocean_droplet" "certbotssllistener" {
  image    = "ubuntu-24-10-x64"
  name     = "certbotssllistener-1"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = ["ephemeral", "certbotssllistener", local.working_dir_tag]

  user_data = data.template_file.userdata_provision_certbotssllistener.rendered
}

resource "null_resource" "wait_for_ready" {
  depends_on = [digitalocean_droplet.certbotssllistener]


  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.certbotssllistener.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /etc/nginx/sites-available/flaskapp ]; do echo 'waiting for server to provision...'; sleep 10; done"
    ]
  }
}


resource "null_resource" "configure_nginx_ssl" {
  depends_on = [digitalocean_droplet.certbotssllistener, null_resource.wait_for_ready, digitalocean_record.certbotssllistener]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = module.ssh_keygen.private_key_pem
    host        = digitalocean_droplet.certbotssllistener.ipv4_address
  }

  provisioner "remote-exec" {
    inline = [
      "certbot certonly --dns-digitalocean --dns-digitalocean-credentials /root/.secrets/certbot/digitalocean.ini -d ${var.subdomain}.${var.managed_domain} --agree-tos --email ${var.certbot_email} --non-interactive",
      "systemctl restart nginx"
    ]
  }
}


output "instance_ip_address" {
   value = digitalocean_droplet.certbotssllistener.ipv4_address
}


