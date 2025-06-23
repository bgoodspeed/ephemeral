#!/bin/bash

export target=${1:-172.64.80.1/32}

sudo ip route add ${target} dev wg0



