#!/usr/bin/env bash

# the container needs to access the forwarded port on the host
#$ iptables -A INPUT -i wo-bridge -j ACCEPT
#$ ufw allow in on wo-bridge

# set dockerhost alias in container
docker exec ori_elasticsearch yum install -y iproute
docker exec ori_elasticsearch bin/set_dockerhost_alias.sh

# set up ssh tunnel to listen only on wo-bridge
WO_BRIDGE_IP_RESOLVED="$(ip addr show wo-bridge | sed -En -e 's/.*inet ([0-9.]+).*/\1/p')"
WO_BRIDGE_IP=${WO_BRIDGE_IP:-$WO_BRIDGE_IP_RESOLVED}
WO_BRIDGE_PORT=${WO_BRIDGE_PORT:-9292}
SOCKET_PATH="/tmp/$1.sock"

ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST:-localhost}
ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}

ssh -M -S "$SOCKET_PATH" -fnNT -L "$WO_BRIDGE_IP:$WO_BRIDGE_PORT:$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT" "$1" \
&& curl -XPOST "$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_reindex" -d'
{
  "conflicts": "proceed",
  "source": {
    "remote": {
      "host": "http://dockerhost:9292"
    },
    "index": "alerts_wo",
    "size": 200
  },
  "dest": {
    "index": "alerts_wo",
    "op_type": "create"
  }
}
'
# FIXME: the index name won't expand within single quotes

ssh -S "$SOCKET_PATH" -O exit "$1"
