# Vultr - windows

A windows VM will be provisioned to the account with the access key & secret key provided.

Ingress to RDP will be configured, and the named user will be made an administrator.


## Setup

* In your AWS account, generate an access key id and secret access key
* Run `tofu init`
* Configure terraform.tfvars:
  - `provisioned_username`: your windows user account name
  - `provisioned_password`: your windows user account password
  - `aws_access_key`: AWS key
  - `aws_secret_access_key`: AWS secret

## provision 

* Run `tofu apply`


