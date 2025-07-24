#!/bin/bash 

domain=${1}

if [ -z "$domain" ];
then
	echo "usage: ${0} domain.com"
	exit 1
fi

dig_output=$(dig _dmarc.$domain TXT | grep "ANSWER: " | awk -F 'ANSWER: ' '{ print $2}' | awk -F ',' '{ print $1 }')

if [ $dig_output == "0" ];
then
	echo "no _dmarc on ${domain}, try to spoof"
else
	echo "_dmarc record on ${domain}, no luck"
fi

