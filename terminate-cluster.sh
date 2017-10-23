#/bin/bash

if [ -z "$1" ]; then
    echo "Usage: terminate-cluster.sh deployment-group "
    echo "Example:terminate-cluster.sh cadence-shared-A "
    exit 1
fi

python operate-instances.py -a statsd -d $1 -op tm --operation-params NONE --target-instances 0-100
python operate-instances.py -a cassandra -d $1 -op tm --operation-params NONE --target-instances 0-100
python operate-instances.py -a history -d $1 -op tm --operation-params NONE --target-instances 0-100
python operate-instances.py -a matching -d $1 -op tm --operation-params NONE --target-instances 0-100
python operate-instances.py -a frontend -d $1 -op tm --operation-params NONE --target-instances 0-100
python operate-instances.py -a stress -d $1 -op tm --operation-params NONE --target-instances 0-100
