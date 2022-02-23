#!/usr/bin/bash

ip route add 10.8.0.0/16 via 130.235.200.1
ip route add default via 11.11.11.1 dev tun0