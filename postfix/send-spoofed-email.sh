#!/bin/bash 
ssh -i id_rsa.pem -l root `./getip.sh` 'bash /spoof-email.sh'

