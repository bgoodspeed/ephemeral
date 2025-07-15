# Overview

This repo will help you setup a sliver C2 host.  Once provisioned a client config will be copied.

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


# Provision 
Install the terraform providers:

```
terraform init
```



# Create your server

To create your server run `terraform apply`:

```
$ terraform plan
... check to make sure everything is as expected ...
$ terraform apply
...
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:

instance_ip_address = "45.55.47.65"
```


The cloud-init script that populates the certificate and starts the web listeners can take a little while after your IP is returned, usually no more than 2 minutes.


You can access it with `ssh`
```
$ ssh -i id_rsa.pem -l root 45.55.47.65
```

The client can be configured with:

```
$ sliver-client import redteam.cfg
```

Then you're good to go:

```
$ sliver-client
```

# Convenience scripts

There are a couple helper scripts to facilitate this:

* `getip.sh` will return the provisioned public IP.


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


# Examples

## Login 

```
$ ssh -i id_rsa -l root `./getip.sh`
```

