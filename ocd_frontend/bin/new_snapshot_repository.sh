SNAPSHOT_DIR=wo_user_data

mkdir $SNAPSHOT_DIR
cd $SNAPSHOT_DIR

SNAPSHOT_PATH=`pwd`

ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST:-localhost}
ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}

curl -XPUT "$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_snapshot/$SNAPSHOT_DIR" -d"
{
    \"type\": \"fs\",
    \"settings\": {
        \"compress\": true,
        \"location\": \"$SNAPSHOT_PATH\"
    }
}
"
