
terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
  }
}

resource "tls_private_key" "generated" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "private_key_pem" {
  content         = tls_private_key.generated.private_key_pem
  filename        = "${path.root}/id_rsa.pem"
  file_permission = "0600"
}

resource "local_file" "public_key_openssh" {
  content         = tls_private_key.generated.public_key_openssh
  filename        = "${path.root}/id_rsa.pub"
  file_permission = "0644"
}


resource "null_resource" "convert_key" {
  provisioner "local-exec" {
    command = "${path.module}/convert_to_openssh.sh"
  }

  triggers = {
    pem_checksum = sha256(local_file.private_key_pem.content)
  }
}

resource "null_resource" "cleanup_converted_key" {
  triggers = {
    destroy_trigger = uuid()
  }

  provisioner "local-exec" {
    when    = destroy
    command = "rm -f ${path.root}/id_rsa"
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [local_file.private_key_pem]
}

output "public_key" {
  value = tls_private_key.generated.public_key_openssh
}

output "private_key_pem" {
  value = tls_private_key.generated.private_key_pem 
  sensitive = true 
}
