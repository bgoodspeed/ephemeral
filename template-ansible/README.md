# Overview

This repo will help you setup your own droplet, you can customize it as needed with ansible

It's meant to be ephemeral - stand it up as needed, tear it down when you're done.


# Prerequisites

* Install terraform or opentofu
* Install ansible 
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 

# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token:

```
do_token = "dop_v1_a2c....71"
```


Edit your provisioning logic in `playbook.yml`

# Provision 
Install the terraform providers:

```
terraform init
```



# Create your server

To create your listener run `terraform apply`:

```
$ terraform apply
...
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:

instance_ip_address = "45.55.47.65"
```

