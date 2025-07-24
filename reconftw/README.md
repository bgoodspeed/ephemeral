# Overview

This repo will help you setup your own reconFTW instance.  Uses the containerized version `six2dez/reconftw`.

It's meant to be ephemeral - stand it up as needed, tear it down when you're done.


# Prerequisites

* Install terraform or opentofu
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 

# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token and the target domain:

```
do_token = "dop_v1_a2c....71"
target_domain = "foo.com"
```


# Provision 
Install the terraform providers: `terraform init`



# Create your server

To create your scanner run `terraform apply`:

# Convenience scripts

There are a couple helper scripts to facilitate this:

* `getip.sh` will return the provisioned public IP.
* `copy-recon-local.sh` will tar up the completed recon and copy it locally.


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


