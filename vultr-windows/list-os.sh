#!/bin/bash 

curl -s -X GET https://api.vultr.com/v2/os -H "Authorization: Bearer $1"
