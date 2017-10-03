
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
            'cmd': '\'{cmd}\'',
            'desc': 'run customized command'
        },

        # install docker
        'dk': {
            'cmd': '\'bash -s\' < ./bashscript/install_docker.sh',
            'desc': 'install docker'
           },

        # install service
        'sv':{
            'cmd':install_service_cmd,
            'desc': 'install service '+cluster
          },

        # uninstall service
        'us':{
            'cmd': '\'docker rm -f cadence-{cluster}\'',
             'desc': 'uninstall service '+cluster
          },

        # remove image
        'ri': {
            'cmd': '\'docker rmi -f ubercadence/longer-dev:0.3.1\'',
            'desc': 'remove cadence image service(for deploying new code)'
           },

        'lg':{
            'cmd': '',
            'desc': 'login EC2 host'
          },

        'fw':{
            'params':{
                'local_port','remote_port'
            },
            'cmd': '-f -N -L {local_port}:{private_ip}:{remote_port}',
            'desc': 'forword a remote port(like 80[grafana] and 81([graphite]) to a local'
        },

        'tm':{
            'cmd': 'NOT a real command. SPECIAL CASE.',
            'desc': 'Terminate EC2 instance'
        },
    }
    return cmd_map
