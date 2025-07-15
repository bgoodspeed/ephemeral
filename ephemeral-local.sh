#!/bin/bash 


for tf in `find ~/src ~/shared_settings -iname 'terraform.tfstate'`
do
  tfdir=`dirname $tf` 

  name=`jq -r '.resources[] | select(.type == "digitalocean_droplet") | .name' $tf`
  ip=`jq -r .outputs.instance_ip_address.value $tf`

  
  echo -n $tfdir":"
  if [[ -n $name ]]; then
	echo " up "$name"("$ip")"
  else
        echo ""
  fi


done
