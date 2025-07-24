# Overview

This repo will help you setup your own postfix mailserver, you can customize it as needed

It's meant to be ephemeral - stand it up as needed, tear it down when you're done.


# Prerequisites

* Install terraform or opentofu
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 

# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token:

```
do_token = "dop_v1_a2c....71"
```

Optionally set addresses for spoofing:

```
spoofed_to = "your@email.com"
spoofed_from = "victim@target.com"
```

# Provision 
Install the terraform providers:

```
terraform init
```

# Create your mail server

To create your listener run `terraform apply`:


# Convenience scripts

There are a couple helper scripts to facilitate this:

* `getip.sh` will return the provisioned public IP.
* `check-dmarc.sh` will check for the dmarc record.
* `send-spoofed-email.sh` will send the spoofed email on the postfix server.

# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


