#/bin/bash
docker exec -i  cadence-cassandra apt-get update && \
docker exec -i  cadence-cassandra apt-get install wget -y && \
docker exec -i  cadence-cassandra apt-get install openjdk-8-jdk -y && \
docker exec -i  cadence-cassandra apt-get install vim -y && \
docker exec -i  cadence-cassandra apt-get install gettext -y && \
docker exec -i  cadence-cassandra wget http://central.maven.org/maven2/org/jmxtrans/jmxtrans/267/jmxtrans-267.deb && \
docker exec -i  cadence-cassandra dpkg -i jmxtrans-267.deb
