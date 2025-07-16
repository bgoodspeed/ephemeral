# Overview


This repo will deploy a [wiredoor](https://www.wiredoor.net) endpoint.  You'll need a domain that is managed by digitalocean so you can create A records dynamically.



# Prerequisites

* Install terraform or opentofu
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 
* Download the wiredoor client: https://github.com/wiredoor/wiredoor-cli/


# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token, and set your domain:

```
do_token = "dop_v1_a2c....71"
managed_domain = "FOO.COM"
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
terraform apply
```

Then on your internal system, start whatever service you want to expose:

``` 
$ python3 -m http.server 30303
...
```

Expose the service using wiredoor-cli:
```
$ sudo wiredoor login --url wiredoor.FOO.COM 
$ wiredoor http --domain service.FOO.COM --port 30303 --ttl 1h 
```

Interact with it:

```
$ curl https://service.FOO.COM/inthebg 
...
```

And you'll see the request on your local service:

```
$ python3 -m http.server 30303
...
10.20.30.1  -  - [16/Jul/2025 11:22:28 "GET /inthebg HTTP/1.1" 404 -
```


