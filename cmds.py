
# for: ssh -i ~/i.pem ec2-user@{public_ip} CMD
def generate_cmd_map(application):
    install_service_cmd = []
    uninstall_service_cmd = ['\'docker rm -f cadence-{application}\'']
    params={}
    if application == 'cassandra':
        #TODO --network=host is not working with Cassandra due to https://github.com/odota/core/issues/1121
        install_service_cmd = [ '\'docker run  -d --name cadence-cassandra  -p 7000:7000 -p 7001:7001 -p 7199:7199 -p 9042:9042 -p 9160:9160 -e CASSANDRA_BROADCAST_ADDRESS={private_ip} -e CASSANDRA_SEEDS={cassandra_seeds} --log-opt max-size=5g cassandra:3.11\'' ]
    elif application == 'statsd':
        install_service_cmd = ['\'docker run  -d --network=host --name cadence-statsd  -p 80-81:80-81 -p 8025-8026:8025-8026 -p 2003:2003 -p 9160:9160 --log-opt max-size=5g kamon/grafana_graphite\'']
    elif application in ['frontend', 'matching', 'history']:
        params={
            'log_level': {
                'default': 'debug',
                'choices': [ 'debug', 'info']
                },
            'num_history_shards': {
                'default': '4',
                'choices': ['4', '16384']
            },
            'version':{
                'default': '0.3.2',
                'choices': ['0.3.2']
            }
        }
        install_service_cmd = ['\'docker run  -d --network=host --name cadence-{application}  -e CASSANDRA_SEEDS={cassandra_seeds} -e RINGPOP_SEEDS={cadence_seeds}  -e STATSD_ENDPOINT={statsd_seeds} -e SERVICES={application}  -p 7933-7935:7933-7935  -e LOG_LEVEL={log_level} -e NUM_HISTORY_SHARDS={num_history_shards} --log-opt max-size=5g ubercadence/server:{version}\'']
    elif application == 'stress':
        install_service_cmd = [
            #install golang/glide and checkout code
            '\'bash -s\' < ./script/install_bench_test.sh',
            # upload the config template to config folder
            '\'cat > bench_template.yaml \' < ./script/bench_template.yaml ',
            # generate a config based on template
            '\'export cadence_frontend_json={cadence_frontend_json} && export statsd_ip_port=\\"{statsd_seeds}\\" && envsubst < bench_template.yaml > /home/ec2-user/go/src/github.com/uber/cadence/config/bench/aws.yaml \'',
            # start stress test service(HTTP on 9696)
            '\' cd /home/ec2-user/go/src/github.com/uber/cadence && nohup ./cadence-bench-test aws &>stress.log & \'& '
        ]
        uninstall_service_cmd = [
            'sudo pkill cadence',
            'rm -rf /home/ec2-user/go',
        ]

    cmd_map = {
        'cc': {
            'params':{
                'cmd':{},
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
            'params': params,
            'cmds': install_service_cmd,
            'desc': 'Install service '+application
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
            'cmds': uninstall_service_cmd,
             'desc': 'Uninstall service '+application
          },

        'lg':{
            'cmds': [''],
            'desc': 'Login EC2 host'
          },

        'fw':{
            'params':{
                'local_port': {
                    'default': '8080',
                },
                'remote_port':{
                    'default': '80',
                    'choices': ['80', '81', '9696','9697','9698' ]
                },
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
