# Overview

This repo will help you setup your own AD instance on digitalocean.  You'll have root access to it with ssh for monitoring and config/setup.

The server will listen on port `389`.  It supports StartTLS with a self-signed certificate. 


# Prerequisites

* Install terraform or opentofu
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 
* Generate server cert

# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token:

```
do_token = "dop_v1_a2c....71"
```

Set your administrator password:

```
admin_password = "SomePassword1!"
```

Optionally set the path to your private key file (generate a new one if you want), otherwise it'll try to use `~/.ssh/id_rsa`: 

```
ssh_keyfile = "~/.ssh/id_ed25519"
```

Install the terraform providers:

```
terraform init
```

# Usage

You can verify with `ldapsearch` as per:

```
LDAPTLS_REQCERT=never ldapsearch -x -H ldap://<droplet IP> -ZZ \
  -D "CN=Administrator,CN=Users,DC=<domain>,DC=<domain tld>" -W \
  -b "DC=<domain>,DC=<domain tld>" "(objectClass=user)"
```
