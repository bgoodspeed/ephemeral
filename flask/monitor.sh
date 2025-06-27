#!/bin/bash

ssh -i id_rsa -l root `bash getip.sh` 'tail -f /scripts/80.log /scripts/443.log'

