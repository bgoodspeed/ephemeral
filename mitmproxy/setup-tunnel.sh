ssh -i id_rsa.pem `./getip.sh ` -l root -L 8282:localhost:8080 -L 8181:localhost:8081
