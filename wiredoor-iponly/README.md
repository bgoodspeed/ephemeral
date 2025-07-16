# Overview


This repo will deploy a [wiredoor](https://www.wiredoor.net) endpoint.  



# Prerequisites

* Install terraform or opentofu
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 
* Download the wiredoor client: https://github.com/wiredoor/wiredoor-cli/


# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token, and set your domain:

```
do_token = "dop_v1_a2c....71"
```


Install the terraform providers:

```
terraform init
```

Create `.env`, use `env.example` as a starting point.
Set:
 * ADMIN_EMAIL
 * ADMIN_PASSWORD
 * GRAFANA_USER
 * GRAFANA_PASSWORD 


# Deploy 

Deploy the system:

```
$ terraform apply
...
instance_ip_address = "167.172.242.139"
```

Then on your internal system, start whatever service you want to expose:

``` 
$ python3 -m http.server 33333
...
```

Expose the service using wiredoor-cli:
```
$ sudo wiredoor login --url https://167.172.242.139 # the ip for your instance
$ wiredoor http --path /inthebg --port 33333 --ttl 1h 
```

Interact with it:

```
$ curl https://167.172.242.139/inthebg/foo
...
```

And you'll see the request on your local service:

```
$ python3 -m http.server 33333
...
10.20.30.1  -  - [16/Jul/2025 11:49:18 "GET /inthebg/foo HTTP/1.1" 404 -
```


