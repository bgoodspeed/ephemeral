# Overview

This repo will help you setup your own kubernetes cluster.  The setup requires slightly more robust VMs to host the master and worker nodes: at least 2GB ram each, and 2 vCPUs minimum.

The install scripts for the nodes are based on Kim Wuestkamp's excellent CKS course:
* Course: https://wuestkamp.medium.com/kubernetes-cks-course-on-youtube-ea541e5a7d25
* Repo: https://github.com/killer-sh/cks-course-environment

# Prerequisites

* Install terraform or opentofu
* Install kubectl 
* Generate a Digital Ocean API token - https://m.do.co/c/15eb168a4c37 

# Configure

Create a `terraform.tfvars` file, there is an example file `terraform.tfvars.example`.

Add your digitalocean token:

```
do_token = "dop_v1_a2c....71"
```

Make up a kubeadm token so that the worker can join the cluster:
```
kubeadm_token = "abcdef.abcdef1234567890" 
```

# Provision 
Install the terraform providers:

```
terraform init
```


# Create your cluster

To create your cluster run `terraform apply`:

```
$ terraform plan
... check to make sure everything is as expected ...
$ terraform apply
...
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:

Outputs:

instance_ip_address = "159.89.37.160"
instance_ip_address_master = "159.89.37.160"
instance_ip_address_worker = "161.35.186.152"
```

The provisioning will take several minutes.  What's happening behind the scenes:
* required software for the cluster is installed on the master and worker nodes
* the access token is set on the master using kubeadm 
* the worker is joined to the master using said access token 
* a kubeconfig file with the requisite certificates and configuration is copied to the local directory for kubectl access


You can access the nodes with `ssh`

```
$ ssh -i id_rsa.pem -l root `./getip-master.sh`
$ ssh -i id_rsa.pem -l root `./getip-worker.sh`  
```

You can interact with the cluster using `kubectl`

```
$ KUBECONFIG=./kubeconfig kubectl get nodes
$ KUBECONFIG=./kubeconfig kubectl get pods -A
```

# Convenience scripts

There are a couple helper scripts to facilitate this:

* `getip-master.sh` will return the provisioned public IP for the master/control plane node 
* `getip-worker.sh` will return the provisioned public IP for the worker node. 


# Cleanup

When you're done, delete the resources you created with `terraform destroy`.


# Examples

## Login 

```
$ ssh -i id_rsa -l root `./getip.sh`
```

