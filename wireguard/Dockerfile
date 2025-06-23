FROM alpine:latest

RUN apk add --no-cache wireguard-tools iproute2 curl bash
RUN mkdir -p /etc/wireguard
COPY client.conf /etc/wireguard/client.conf
COPY container-wg-setup.sh /usr/local/bin/container-wg-setup.sh
RUN chmod +x /usr/local/bin/container-wg-setup.sh

ENTRYPOINT ["/usr/local/bin/container-wg-setup.sh"]
