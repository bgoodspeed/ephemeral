# Overview

This repo has some example terraform code to stand up a set of VMs and demonstrate ssh proxyjump and a terminal socks5 proxy.

The intent is to obfuscate the source of the requests being proxied.

## Try it out

Create a `terraform.tfvars` file with your digitalocean token:

```
do_token "dop_v1_a2c....71"
```

Install the necessary providers:

```
$ terraform init
```

Create the resources:

```
$ terraform apply
```

Initiate the proxy jumps (`ssh -J user@host1,user@host2 -D LPORT user@finalhost`), this is encapsulated in the script `do_tunnel.sh`:

```
$ ./do_tunnel.sh
159.89.182.17 -> 159.203.101.53 -> 159.203.122.60
...
Last login: Wed Jan 10 19:10:47 2024 from 159.203.101.53
```

Here we can see the logins flow from left to right.  Each step in the chain (159.203.101.53 in this case) only sees a login from the previous step (159.203.101.53 in this case).

Finally, we can confirm we have successfully proxied our traffic (e.g. by the script `checkip.sh`, which just fetches the result from ifconfig.me using the `--socks5` directive with curl):

```
$ ./checkip.sh
159.203.122.60
```

