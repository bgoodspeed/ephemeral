# Terraform/tofu scripts to deploy various pentesting tools 


## Digital Ocean 

The following are all based on [digitalocean](https://m.do.co/c/15eb168a4c37) resources:
* [template](template/): a starting point for an arbitrary droplet
* [template-ansible](template-ansible/): a starting point for an arbitrary droplet with ansible provisioning support
* [flask](flask/): deploy a web listener/payload server  with self-signed certificate, and redirect support
* [certbot](certbot/): deploy a web listener/payload server with a valid SSL certificate, requires a domain managed by digitalocean
* [jumps](jumps/): deploy a series of jump boxes
* [wireguard](wireguard/): deploy a wireguard VPN endpoint, and demo some mechanisms to consume it, client-side (via explicit routing, via docker)
* [caido](caido/): deploy a caido proxy endpoint 
* [samba ad](samba-ad/): deploy a samba AD instance with a given realm/domain
* [maildev](mailserver/): deploy a maildev instance with webui to access received emails
* [sliver](sliver/): deploy a sliver C2 instance, and builds a client configuration for its use
* [wiredoor](wiredoor/): deploy a [wiredoor](https://www.wiredoor.net) server and configured subdomains to expose internal services via wireguard tunnels.  Requires a domain managed by digitalocean.
* [wiredoor-iponly](wiredoor-iponly/): deploy a [wiredoor](https://www.wiredoor.net) server to expose internal services via wireguard tunnels (no domain dependency)
* [kubernetes](kubernetes/): deploy a 2 node kubernetes cluster. no load balancer or other cloud-provider dependencies

## Vultr

[Vultr](vultr.com) is another hosting provider.  Unlike digital ocean, they support windows VPS instances, and allow by-the-minute usage.

* [linux vm](vultr-basic/): a basic linux VM, just to highlight the differences deploying to another provider
* [windows vm](vultr-windows/): a basic windows VM. Unfortunately they don't support cloudbase, so any further provisioning needs to be done by hand (userdata/cloudinit doesn't work)


## Amazon web services

[AWS](https://aws.amazon.com/) supports windows and linux via various AMI images, but they are more complex and expensive than the other options.

* [windows on aws](amazon-windows/) provisions a custom admin-level user, enables RDP, and creates the necessary ingress firewall rules to access it in AWS.

# Helper scripts 

It is useful to be keep track of which instances are active (since they are generating costs), the scripts below can help.

## Remote via API
The script `ephemeral.py` will search digitalocean for droplets with the given tag (the `ephemeral` tag is applied in all of these projects and is the default).

To configure:

* create a venv and activate: `python3 -m venv ~/venvs/pydo && source ~/venvs/pydo/bin/activate` 
* install requirements: `pip install -r requirements.txt`
* provide digital ocean API token as environment variable or in a file: `export DIGITALOCEAN_API_TOKEN=...` or `echo "the token" > .digital_ocean_token`

Run with `python ephemeral.py` to list created droplets.

## Local via terraform introspection

The script `ephemeral-local` will search local directories for terraform state files and if they contain digitalocean resources report them.
