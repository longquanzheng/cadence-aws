
# for: ssh -i ~/i.pem ec2-user@{public_ip} CMD
def generate_cmd_map(cluster):
    install_service_cmd = ""
    if cluster == 'cassandra':
        #TODO --network=host is not working with Cassandra due to https://github.com/odota/core/issues/1121
        install_service_cmd = '\'docker run  -d --name cadence-cassandra  -p 7000:7000 -p 7001:7001 -p 7199:7199 -p 9042:9042 -p 9160:9160 -e CASSANDRA_BROADCAST_ADDRESS={private_ip} -e CASSANDRA_SEEDS={cassandra_seeds} cassandra:3.11\''
    elif cluster == 'statsd':
        install_service_cmd = '\'docker run  -d --network=host --name cadence-statsd  -p 80-81:80-81 -p 8025-8026:8025-8026 -p 2003:2003 -p 9160:9160 kamon/grafana_graphite\''
    elif cluster in ['frontend', 'matching', 'history']:
        install_service_cmd = '\'docker run  -d --network=host --name cadence-{cluster}  -e CASSANDRA_SEEDS={cassandra_seeds} -e RINGPOP_SEEDS={cadence_seeds}  -e STATSD_ENDPOINT={statsd_seeds} -e SERVICES={cluster}  -p 7933-7935:7933-7935   ubercadence/longer-dev:0.3.1\''


    cmd_map = {
        'cc': {
            'params':{
                'cmd',
            },
            'cmds': ['\'{cmd}\''],
            'desc': 'Run a customized command'
        },

        # install docker
        'dk': {
            'cmds': ['\'bash -s\' < ./script/install_docker.sh'],
            'desc': 'Install docker'
           },

        # install service
        'sv':{
            'cmds': [install_service_cmd],
            'desc': 'Install service '+cluster
          },

        # install jmxtrans
        'jt':{
            'cmds' : [
                # upload statsd.json
                '\'cat > statsd_template.json \' < ./script/statsd_template.json ',
                'docker cp statsd_template.json cadence-cassandra:statsd_template.json',

                # install  jmxtrans
                '\'docker exec -i  cadence-cassandra apt-get update\'',
                '\'docker exec -i  cadence-cassandra apt-get install wget -y\'',
                '\'docker exec -i  cadence-cassandra apt-get install openjdk-8-jdk -y\'',
                '\'docker exec -i  cadence-cassandra apt-get install vim -y\'',
                '\'docker exec -i  cadence-cassandra apt-get install gettext -y\'',
                '\'docker exec -i  cadence-cassandra wget http://central.maven.org/maven2/org/jmxtrans/jmxtrans/267/jmxtrans-267.deb\'',
                '\'docker exec -i  cadence-cassandra dpkg -i jmxtrans-267.deb\'',
                # generate statsd.json based on template TODO there is a bug about bash export command...
                '\"docker exec -i  cadence-cassandra /bin/bash -c \\\" export STATSD_IP={statsd_seed_ip} && export PRIVATE_IP_UNDER={private_ip_under} && envsubst < statsd_template.json > /usr/share/jmxtrans/statsd.json \\\" \"',
                # run jmxtrans # NOTE intentionally add 2s delay on the end of bash cmds to let jmx get fully started
                '\'docker exec -i  cadence-cassandra /bin/bash -c "cd /usr/share/jmxtrans/ && ./bin/jmxtrans.sh start statsd.json && sleep 2 && echo succ"\''
            ],
            'desc':'Install jmxtrans (for Cassandra docker container)'
        },

        # uninstall service
        'us':{
            'cmds': ['\'docker rm -f cadence-{cluster}\''],
             'desc': 'Uninstall service '+cluster
          },

        # remove image
        'ri': {
            'cmds': ['\'docker rmi -f ubercadence/longer-dev:0.3.1\''],
            'desc': 'Remove cadence image service(for deploying new code)'
           },

        'lg':{
            'cmds': [''],
            'desc': 'Login EC2 host'
          },

        'fw':{
            'params':{
                'local_port','remote_port'
            },
            'cmds': ['-f -N -L {local_port}:{private_ip}:{remote_port}'],
            'desc': 'Forword a remote port(like 80[grafana] and 81([graphite]) to a local port(like 8080/8081)'
        },

        'tm':{
            'cmds': ['NOT a real command. SPECIAL CASE.'],
            'desc': 'Terminate EC2 instance'
        },
    }
    return cmd_map
