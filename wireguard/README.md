

# how to setup locally:



1. install wireguard and tools: `apt install wireguard wireguard-tools`
2. create the wireguard interface: `ip link add dev wg0 type wireguard`
3. setup providers, `terraform init` 
4. write digitalocean secret into tfvars file `vim terraform.tfvars`
5. generate keys, `./generate_wg_keys.sh`
6. generate server config: `./generate_server_conf.sh`
7. create server and setup: `terraform apply`
8. give cloud init time to run (sometimes takes a few minutes after terraform returns)
9. generate and bind client config: `./bind_client_conf.sh`.

Use it:

* bind routes with your target through the tunnel: `./bind_local_routes.sh 123.2.1.23/32`.

# or just in a tunnel


1. install wireguard and tools: `apt install wireguard wireguard-tools`
2. setup providers, `terraform init` 
3. write digitalocean secret into tfvars file `vim terraform.tfvars`
4. generate keys, `./generate_wg_keys.sh`
5. generate server config: `./generate_server_conf.sh`
6. create server and setup: `terraform apply`
7. give cloud init time to run (sometimes takes a few minutes after terraform returns)
8. generate the client config: `./generate_client_conf.sh`.
9. build and run the container: `./build-container.sh`

Use it:

* run the container `./run-container.sh`
