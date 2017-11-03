#/bin/bash

if [ -z "$5" ]; then
    echo "Usage: one-click-cluster.sh keypair-name subnet-id security-group-id deployment-group keypair-pem-location "
    echo "Example: one-click-cluster.sh cadence-shared subnet-xxxxxx sg-xxxxxx cadence-shared-A ~/cadence-shared.pem"
    exit 1
fi

echo "-----Start creating cadence cluster instances-----"
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a statsd --disk-size 250
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a cassandra --num 3 --disk-size 100
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a history --num 2
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a frontend
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a matching
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a stress
python create-instances.py  --key-name $1 --subnet-id $2 --security-group-id $3 -d $4 -a worker

echo "waiting for instances to be ready..."
sleep 150

echo "-----Start configuring cadence clusters-----"
echo "1. config/install Statsd-Graphite-Grafana application:"
python operate-instances.py -a statsd -d cadence-shared --pem $5 -d $4 -op dk --operation-params NONE --target-instances 0-100
python operate-instances.py -a statsd -d cadence-shared --pem $5 -d $4 -op sv --operation-params NONE --target-instances 0-100
python operate-instances.py -a statsd -d cadence-shared --pem $5 -d $4 -op fw --operation-params local_port:8080,remote_port:80 --target-instances 0-100
python operate-instances.py -a statsd -d cadence-shared --pem $5 -d $4 -op fw --operation-params local_port:8081,remote_port:81 --target-instances 0-100

echo "2. config/install Cassandra application"
python operate-instances.py -a cassandra -d cadence-shared --pem $5 -d $4 -op dk --operation-params NONE --target-instances 0-100
python operate-instances.py -a cassandra -d cadence-shared --pem $5 -d $4 -op sv --operation-params NONE --target-instances 0-100
python operate-instances.py -a cassandra -d cadence-shared --pem $5 -d $4 -op jt --operation-params NONE --target-instances 0-100

echo "3. config/install Cadence frontend application"
python operate-instances.py -a frontend -d cadence-shared --pem $5 -d $4 -op dk --operation-params NONE --target-instances 0-100
python operate-instances.py -a frontend -d cadence-shared --pem $5 -d $4 -op sv --operation-params num_history_shards:4,log_level:info,version:master --target-instances 0-100

echo "4. config/install Cadence history application"
python operate-instances.py -a history -d cadence-shared --pem $5 -d $4 -op dk --operation-params NONE --target-instances 0-100
python operate-instances.py -a history -d cadence-shared --pem $5 -d $4 -op sv --operation-params num_history_shards:4,log_level:info,version:master --target-instances 0-100

echo "5. config/install Cadence matching application"
python operate-instances.py -a matching -d cadence-shared --pem $5 -d $4 -op dk --operation-params NONE --target-instances 0-100
python operate-instances.py -a matching -d cadence-shared --pem $5 -d $4 -op sv --operation-params num_history_shards:4,log_level:info,version:master --target-instances 0-100

echo "6. config/install Cadence stress(bench) test application"
python operate-instances.py -a stress -d cadence-shared --pem $5 -d $4 -op sv --operation-params NONE --target-instances 0-100
python operate-instances.py -a stress -d cadence-shared --pem $5 -d $4 -op fw --operation-params local_port:9696,remote_port:9696 --target-instances 0-100

echo "7. config/install Cadence bench worker application"
python operate-instances.py -a worker -d cadence-shared --pem $5 -d $4 -op sv --operation-params NONE --target-instances 0-100
python operate-instances.py -a worker -d cadence-shared --pem $5 -d $4 -op fw --operation-params local_port:9696,remote_port:9696 --target-instances 0-100