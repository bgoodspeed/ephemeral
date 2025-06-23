
you need a digital ocean account - https://m.do.co/c/15eb168a4c37 is my referral link.  create a person access token
then clone this, https://github.ibm.com/Ben-Goodspeed/dotofu,  and put your token in terraform.tfvars
run terraform to build the droplet and copy your keys etc, docs are in that github
create an afraid.org account, and pick a free public domain that allows subdomains
ssh into your droplet and hit the URL afraid.org gives you to update the ip
https://letsencrypt.org/docs/challenge-types/ should let you do an http challenge to get your cert

I'm not sure about this
ssh into your droplet and hit the URL afraid.org gives you to update the ip
 Dropping some notes here:
snap install --classic certbot
certbot certonly --webroot
Follow the certbot prompts
mv server.pem server.pem.old
ln -s /etc/letsencrypt/live/<domain>/fullchain.pem /scripts/server.pem
ln -s /etc/letsencrypt/live/<domain>/privkey.pem /scripts/privkey.pem
Change Line 22 of /scripts/https_server.py to -> httpd.socket = ssl.wrap_socket (httpd.socket, certfile='/scripts/server.pem', keyfile='/scripts/privkey.pem', server_side=True)
Restart the https_server (what's the best way to do this?k)
