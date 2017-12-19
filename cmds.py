
# for: ssh -i ~/i.pem ec2-user@{public_ip} CMD
def generate_cmd_map(application):
    install_service_cmd = []
    uninstall_service_cmd = ['\'docker rm -f cadence-{application}\'']
    params={}
    if application == 'cassandra':
        #TODO --network=host is not working with Cassandra due to https://github.com/odota/core/issues/1121
        install_service_cmd = [ '\'docker run --restart=unless-stopped --ulimit nofile=65535:100000 -d --name cadence-cassandra  -p 7000:7000 -p 7001:7001 -p 7199:7199 -p 9042:9042 -p 9160:9160 -e LOCAL_JMX=no -e     JVM_EXTRA_OPTS=-Djava.rmi.server.hostname=127.0.0.1 -e CASSANDRA_BROADCAST_ADDRESS={private_ip} -e CASSANDRA_SEEDS={cassandra_seeds} --log-opt max-size=5g cassandra:3.11\'' ]
    elif application == 'statsd':
        install_service_cmd = ['\'docker run --restart=unless-stopped --ulimit nofile=65535:100000 -d --network=host --name cadence-statsd  -p 80-81:80-81 -p 8025-8026:8025-8026 -p 2003:2003 -p 9160:9160 --log-opt max-size=5g kamon/grafana_graphite\'']
    elif application in ['frontend', 'matching', 'history']:
        params={
            'log_level': {
                'default': 'info',
                'choices': [ 'debug', 'info']
                },
            'num_history_shards': {
                'default': '4',
                'choices': ['4', '1024', '16384']
            },
            'version':{
                #master tag is for latest commit on master branch
                'default': 'master',
                'choices': ['0.3.2','master']
            }
        }
        install_service_cmd = [
            # remove docker image of tag master to pick up latest commit on master branch
            '\'docker rmi -f ubercadence/server:master\'',
            '\'docker run --restart=unless-stopped --ulimit nofile=65535:100000 -d --network=host --name cadence-{application}  -e CASSANDRA_SEEDS={cassandra_seeds} -e RINGPOP_SEEDS={cadence_seeds}  -e STATSD_ENDPOINT={statsd_seeds} -e SERVICES={application}  -p 7933-7935:7933-7935  -e LOG_LEVEL={log_level} -e NUM_HISTORY_SHARDS={num_history_shards} --log-opt max-size=5g ubercadence/server:{version}\''
            ]
    elif application == 'stress':
        install_service_cmd = [
            #install golang/glide and checkout code
            '\'bash -s\' < ./templates/install_bench_test.sh',
            # upload the config template to config folder
            '\'cat > bench_template.yaml \' < ./templates/bench_template.yaml ',
            # generate a config based on template
            '\'export cadence_frontend_json={cadence_frontend_json} && export statsd_ip_port=\\"{statsd_seeds}\\" && envsubst < bench_template.yaml > /home/ec2-user/go/src/github.com/uber/cadence/config/bench/aws.yaml \'',
            # create cadence-bench service
            '\'sudo touch /etc/init.d/cadence-bench && sudo chmod 777 /etc/init.d/cadence-bench && cat >> /etc/init.d/cadence-bench \' < ./templates/bench_service.sh ',
            # start stress test service(HTTP on 9696)
            '\'sudo service cadence-bench start \'& ',
            # add to chkconfig
            '\'sudo chkconfig --add cadence-bench \'',
            # check log to see if having any problem
            '\' sleep 1 &&  /bin/cat /home/ec2-user/go/src/github.com/uber/cadence/stress.log \''
        ]
        uninstall_service_cmd = [
            'sudo service cadence-bench stop',
            'sudo pkill cadence',
            'rm -rf /home/ec2-user/go',
            'sudo rm -rf /etc/init.d/cadence-bench',
        ]
    elif application == 'worker':
        install_service_cmd = [
            #install golang/glide and checkout code
            '\'bash -s\' < ./templates/install_bench_test.sh',
            # upload the config template to config folder
            '\'cat > bench_template.yaml \' < ./templates/bench_template_worker.yaml ',
            # generate a config based on template
            '\'export cadence_frontend_json={cadence_frontend_json} && export statsd_ip_port=\\"{statsd_seeds}\\" && envsubst < bench_template.yaml > /home/ec2-user/go/src/github.com/uber/cadence/config/bench/aws.yaml \'',
            # create cadence-bench service
            '\'sudo touch /etc/init.d/cadence-bench && sudo chmod 777 /etc/init.d/cadence-bench && cat >> /etc/init.d/cadence-bench \' < ./templates/bench_service.sh ',
            # start stress test service(HTTP on 9696)
            '\'sudo service cadence-bench start \'& ',
            # add to chkconfig
            '\'sudo chkconfig --add cadence-bench \'',
            # check log to see if having any problem
            '\' sleep 1 &&  /bin/cat /home/ec2-user/go/src/github.com/uber/cadence/stress.log \''
        ]
        uninstall_service_cmd = [
            'sudo service cadence-bench stop',
            'sudo pkill cadence',
            'rm -rf /home/ec2-user/go',
            'sudo rm -rf /etc/init.d/cadence-bench',
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
            'cmds': ['\'bash -s\' < ./templates/install_docker.sh'],
            'desc': 'Install docker'
        },

        'fd': {
            'cmds': ['\'bash -s\' < ./templates/update_fd_limit.sh'],
            'desc': 'Update fd_limit'
        },

        # install service
        'sv':{
            'params': params,
            'cmds': install_service_cmd,
            'desc': 'Install service '+application
        },

        # install jmxtrans
        # TODO need to figure it out how to use docker to make it easier
        'jt':{
            'cmds' : [
                #fix jmx setting and restart cassandra
                '\'bash -s\' < ./templates/fix_cassandra.sh',
                '\'docker restart cadence-cassandra \'',

                # install  jmxtrans
                '\'bash -s\' < ./templates/install_jmxtrans.sh',

                # upload statsd_template.json
                '\'cat > statsd_template.json \' < ./templates/statsd_template.json ',
                'docker cp statsd_template.json cadence-cassandra:statsd_template.json',

                # generate statsd.json based on the template
                '\"docker exec -i  cadence-cassandra /bin/bash -c \\\" export STATSD_IP={statsd_seed_ip} && export PRIVATE_IP_UNDER={private_ip_under} && envsubst < statsd_template.json > /usr/share/jmxtrans/statsd.json \\\" \"',
                # run jmxtrans # NOTE intentionally add 2s delay on the end of bash cmds to let jmx get fully started
                '\'docker exec -i  cadence-cassandra /bin/bash -c "cd /usr/share/jmxtrans/ && export LOG_LEVEL=info && ./bin/jmxtrans.sh stop statsd.json && ./bin/jmxtrans.sh start statsd.json && sleep 2 && echo succ"\''
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
                    'choices': ['80','81','9696','7199','7933']
                },
            },
            'cmds': ['-f -N -L {local_port}:{private_ip}:{remote_port}'],
            'desc': 'Local port forwording, i.e. forwording the local port to remopte server port.'
        },

        'tm':{
            'cmds': ['NOT a real command. SPECIAL CASE.'],
            'desc': 'Terminate EC2 instance'
        },
    }
    return cmd_map
