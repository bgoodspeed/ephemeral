#!/bin/bash 
ssh -i id_rsa.pem -l root `./getip.sh` 'tar -cf /recon.tar /Recon && gzip -9 /recon.tar'
scp -i id_rsa.pem root@`./getip.sh`:/recon.tar.gz .



