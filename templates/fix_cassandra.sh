#/bin/bash
docker exec -i cadence-cassandra /bin/bash -c "sed -i '/password/d' /etc/cassandra/cassandra-env.sh && sed -i 's/JVM_OPTS=\"\$JVM_OPTS -Dcom.sun.management.jmxremote.authenticate=true\"/JVM_OPTS=\"\$JVM_OPTS -Dcom.sun.management.jmxremote.authenticate=false\"/g' /etc/cassandra/cassandra-env.sh"
