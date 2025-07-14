# Vultr - windows

A windows VM will be provisioned to the account with the api key provided.

Vultr doesn't support `cloudbase-init`, so `user_data` will have no effect.

You'll need to  login to your dashboard to see the administrator password for the provisioned machine.  Their API doesn't expose this.

## Setup

* In your vultr account, enable the API, and copy the api key
* Ensure your source IP address is in the access control section for your API key
* Write your api key to the `vultr_api_key` variable in `terraform.tfvars`* Run `tofu init` 

## provision 

* Run `tofu apply`


