#!/bin/bash

curl ifconfig.me --socks5 localhost:${1:-12321}
