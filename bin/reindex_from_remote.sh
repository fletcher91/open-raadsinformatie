#!/usr/bin/env bash

# the container needs to access the forwarded port on the host
#$ iptables -A INPUT -i wo-bridge -j ACCEPT
#$ ufw allow in on wo-bridge

# set dockerhost alias in container
docker exec ori_elasticsearch yum install -y iproute
docker exec ori_elasticsearch bin/set_dockerhost_alias.sh

# TODO: listen only on wo-bridge
ssh -M -S waaroverheid.sock -fnNT -L :9292:localhost:9200 waaroverheid

curl -XPOST "localhost:9200/_reindex" -d'
{
  "conflicts": "proceed",
  "source": {
    "remote": {
      "host": "http://dockerhost:9292"
    },
    "index": "wo_gm0180",
    "size": 200
  },
  "dest": {
    "index": "wo_gm0180",
    "op_type": "create"
  }
}
'

ssh -S waaroverheid.sock -O exit waaroverheid
