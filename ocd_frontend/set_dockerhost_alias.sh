#!/usr/bin/env bash
# set dockerhost host alias (remove any existing)

sed '/dockerhost$/d' /etc/hosts > /etc/hosts.new \
&& cat /etc/hosts.new > /etc/hosts \
&& ip route show | awk '/default/ {print $3 "\t" "dockerhost"}' >> /etc/hosts
