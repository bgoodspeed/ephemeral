# Overview

This repo will help you setup your own listener on digitalocean.  You'll have root access to it with ssh for monitoring and file/payload serving.

It's meant to be ephemeral - stand it up as needed, tear it down when you're done (or when cloudflare/akamai burns it).

The server will listen on ports `80` and `443` for HTTP and HTTPS respectively.  HTTPS is served under a self-signed certificate.

This version uses flask, and will support a redirect loop https://slcyber.io/assetnote-security-research-center/novel-ssrf-technique-involving-http-redirect-loops/

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


Install the terraform providers:

```
terraform init
```

Generate certs:

```
$ ./gencerts.sh 
```

Or manually:

```

$ openssl genrsa -out server.key 2048
$ openssl req -new -key server.key -out server.csr
$ openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
$ cat server.crt server.key > server.pem

```



### Mac users on M1 chips
<details>
    <summary>Click here</summary>


When I initialized terraform I got the following error....
```sh
terraform init

Initializing the backend...

Initializing provider plugins...
- Finding digitalocean/digitalocean versions matching "~> 2.0"...
- Finding latest version of hashicorp/template...
- Installing digitalocean/digitalocean v2.34.1...
- Installed digitalocean/digitalocean v2.34.1 (signed by a HashiCorp partner, key ID F82037E524B9C0E8)

Partner and community providers are signed by their developers.
If you'd like to know more about provider signing, you can read about it here:
https://www.terraform.io/docs/cli/plugins/signing.html
╷
│ Error: Incompatible provider version
│
│ Provider registry.terraform.io/hashicorp/template v2.2.0 does not have a package available for your current platform, darwin_arm64.
│
│ Provider releases are separate from Terraform CLI releases, so not all providers are available for all platforms. Other versions of this provider may have different platforms supported.
╵

```
I was running Mac OS `14.2.1 (23C71)`
FYI -  Xcode was running `15.0` (sometimes Xcode has magic powers with macs. True story)

Based on [some research](https://discuss.hashicorp.com/t/template-v2-2-0-does-not-have-a-package-available-mac-m1/35099/4) on the internet and a leap of faith , I ran the following commands:
- `brew uninstall terraform`
- `brew cleanup`
- `brew install kreuzwerker/taps/m1-terraform-provider-helper`
- `brew tap hashicorp/tap`
- `brew install hashicorp/tap/terraform`
- `m1-terraform-provider-helper activate`

Then ...
```sh
m1-terraform-provider-helper install hashicorp/template -v v2.2.0

Getting provider data from terraform registry
2024/01/05 15:29:26 Getting provider data from https://registry.terraform.io/v1/providers/hashicorp/template
2024/01/05 15:29:27 Provider data: {https://github.com/hashicorp/terraform-provider-template terraform-provider-template}
Getting source code...
2024/01/05 15:29:27 Extracted repo https://github.com/hashicorp/terraform-provider-template to terraform-provider-template
2024/01/05 15:29:27 Cloning https://github.com/hashicorp/terraform-provider-template to /Users/geoff/.m1-terraform-provider-helper/terraform-provider-template
Enumerating objects: 5962, done.
Total 5962 (delta 0), reused 0 (delta 0), pack-reused 5962
2024/01/05 15:29:30 Resetting /Users/geoff/.m1-terraform-provider-helper/terraform-provider-template and pulling latest changes
Compiling...
Successfully installed hashicorp/template v2.2.0

~/Tools/dotofu main:$ terraform --version
Terraform v1.6.6
on darwin_arm64

```

</details>


# Create your listener

To create your listener run `terraform apply`:

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
$ ssh -l root 45.55.47.65
```

# Convenience scripts

There are a couple helper scripts to facilitate this:

* `getip.sh` will return the provisioned public IP.
* `getipcb.sh` will copy the provisioned public IP to the clipboard.
* `monitor.sh` will connect to the public IP and monitor the logs.


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


# Examples

## Login 

```
$ ssh -i id_rsa -l root `./getip.sh`
```

## Monitoring  

```
$ ./monitor.sh 
==> /scripts/443.log <==

==> /scripts/80.log <==
05/Jan/2024 13:14:16|111.222.111.222|GET /foobar|
```

## Jumpbox (via socks5)

```
$ export LOCAL_PORT=31337
$ ssh -l root -D $LOCAL_PORT `./getip.sh`  
```

Then setup Burp/ZAP to use a socks5 proxy with address localhost:31337.



## File serving

You can serve your payloads as needed:

```
$ echo "hi mom" > /tmp/foo
$ scp /tmp/foo root@`./getip.sh`:/shared
foo                                                     100%    7     0.2KB/s   00:00
$ curl http://`./getip.sh`/foo
hi mom
```

## File sharing (SSHFS)

You'll need `sshfs` installed, but you won't need root permissions to mount the actual share. 

```
$ sshfs root@`./getip.sh`:/shared ~/shared -o reconnect
```

Don't forget to unmount before you destroy your instance, as FUSE can be a little fussy.

```
$ fusermount -u ~/shared
```


# Caveats

* A self-signed certificate is pre-generated, if you need a trusted cert, letsencrypt.org can be used, but manual steps will be required.
* No host name is bound by default, if you want to use a public one, afraid.org can be used, but manual steps are required.
* The selected VM is the cheapest option, but it still has a cost.  Typically it will cost about $7/month CAD.  It is wise to set an alert threshold on your cloud accounts to prevent surprises in billing.


# Error conditions

If you get the error below:

```sh
digitalocean_ssh_key.default: Creating...
╷
│ Error: Error creating SSH Key: POST https://api.digitalocean.com/v2/account/keys: 422 (request "32fb72fb-bbf1-41dc-9ea3-4bcad43cc10b") SSH Key is already in use on your account
│
│   with digitalocean_ssh_key.default,
│   on dotofu.tf line 23, in resource "digitalocean_ssh_key" "default":
│   23: resource "digitalocean_ssh_key" "default" {
│
╵
```

Deleting the SSH key from the DigitalOcean UI resolved the issue because Terraform may attempt to create a new SSH key on DigitalOcean with the same public key content as an existing key in your account. Delete the existing key from the DigitalOcean UI, it removed this conflict, allowing Terraform to successfully add the key to your DigitalOcean account.

When it worked it should look like this ....
```sh
...
...
digitalocean_ssh_key.default: Creating...
digitalocean_ssh_key.default: Creation complete after 0s [id=40573957]
digitalocean_droplet.listener: Creating...
digitalocean_droplet.listener: Still creating... [10s elapsed]
digitalocean_droplet.listener: Still creating... [20s elapsed]
digitalocean_droplet.listener: Still creating... [30s elapsed]
digitalocean_droplet.listener: Still creating... [40s elapsed]
digitalocean_droplet.listener: Creation complete after 42s [id=394038405]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

instance_ip_address = "165.227.124.192"
```

