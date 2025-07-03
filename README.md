# Terraform/tofu scripts to deploy various pentesting tools 


* [template](template/): a starting point for an arbitrary droplet
* [flask](flask/): deploy a flask server with self-signed certificate, and redirect support
* [jumps](jumps/): deploy a series of jump boxes
* [wireguard](wireguard/): deploy a wireguard VPN endpoint, and demo some mechanisms to consume it, client-side (via explicit routing, via docker)
* [caido](caido/): deploy a caido proxy endpoint 
* [samba ad](samba-ad/): deploy a samba AD instance with a given realm/domain
* [maildev](mailserver/): deploy a maildev instance with webui to access received emails

# Helper scripts 

The script `ephemeral.py` will search digitalocean for droplets with the given tag (the `ephemeral` tag is applied in all of these projects and is the default).

To configure:

* create a venv and activate: `python3 -m venv ~/venvs/pydo && source ~/venvs/pydo/bin/activate` 
* install requirements: `pip install -r requirements.txt`
* provide digital ocean API token as environment variable or in a file: `export DIGITALOCEAN_API_TOKEN=...` or `echo "the token" > .digital_ocean_token`

Run with `python ephemeral.py` to list created droplets.
