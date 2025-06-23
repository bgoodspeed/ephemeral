#!/bin/bash 

docker run --rm -it --cap-add=NET_ADMIN --cap-add=SYS_MODULE --device /dev/net/tun --privileged wg-container

