#!/bin/bash 

ssh -i id_rsa -L 1337:127.0.0.1:8080 root@`./getip.sh`
