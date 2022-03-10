#!/usr/bin/bash

# iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
nft add table nat
nft add chain nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule ip nat postrouting oifname "eth0" counter masquerade

# iptables -A FORWARD -i eth0 -o tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT
nft add table ip filter
nft add chain ip filter forward { type filter hook forward priority 0 \; }
nft add rule ip filter forward iifname "eth0" oifname "tun0" ct state related,established  counter accept

# iptables -A FORWARD -i tun0 -o eth0 -j ACCEPT
nft add rule ip filter forward iifname "tun0" oifname "eth0" counter accept