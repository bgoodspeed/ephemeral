# Overview

This repo will help you setup your own listener on digitalocean.  You'll have root access to it with ssh for monitoring and file/payload serving.

It's meant to be ephemeral - stand it up as needed, tear it down when you're done (or when cloudflare/akamai burns it).

The server will listen on ports `80` and `443` for HTTP and HTTPS respectively.  HTTPS is served under a certbot certificate

This version uses flask, and will support a redirect loop https://slcyber.io/assetnote-security-research-center/novel-ssrf-technique-involving-http-redirect-loops/

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

You can optionally set `subdomain` here, the default is `listener`, so this would be `listener.foo.com`.



Install the terraform providers:

```
terraform init
```


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


# Usage Examples

## Login 

```
$ ssh -i id_rsa -l root listener.foo.com
```




## File serving

You can serve your payloads as needed:

```
$ echo "hi mom" > /tmp/foo
$ scp -i id_rsa /tmp/foo root@listener.foo.com:/scripts/static
foo                                                     100%    7     0.2KB/s   00:00
$ curl https://listener.foo.com/static/foo
hi mom
```

