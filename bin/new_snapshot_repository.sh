SNAPSHOT_DIR=wo_user_data

mkdir $SNAPSHOT_DIR
cd $SNAPSHOT_DIR

SNAPSHOT_PATH=`pwd`

curl -XPUT "localhost:9200/_snapshot/$SNAPSHOT_DIR" -d"
{
    \"type\": \"fs\",
    \"settings\": {
        \"compress\": true,
        \"location\": \"$SNAPSHOT_PATH\"
    }
}
"
