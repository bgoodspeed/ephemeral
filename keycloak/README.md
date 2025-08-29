# Overview

This repo will help you setup your own keycloak instance.



# Prerequisites

* Install terraform or opentofu
* Register a domain name and make sure digital ocean manages DNS for it
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 

# Configure


Add your digitalocean token to `terraform.tfvars`:

```
do_token = "dop_v1_a2c....71"
```


Set your managed domain in `terraform.tfvars`:

```
managed_domain = "foo.com"
```

You can optionally set `subdomain` here, the default is `keycloak`, so this would be `keycloak.foo.com`.



Install the terraform providers:

```
terraform init
```


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


# Usage Examples

## Login 

```
$ ssh -i id_rsa -l root keycloak.foo.com
```




