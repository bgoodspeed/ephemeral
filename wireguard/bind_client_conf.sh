#!/bin/bash


./generate_client_conf.sh 

sudo ip addr add 192.168.69.2/24 dev wg0 
sudo wg setconf wg0 client.conf
sudo ip link set up dev wg0



