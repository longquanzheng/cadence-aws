import boto3,argparse,json,pprint,subprocess,sys

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", required=True, help='Cluster type')
parser.add_argument("--dry-run", action='store_true', help='Only print out commands')
args = parser.parse_args()

ec2 = boto3.client('ec2')
filters = [ { 'Name': 'tag:Name', 'Values': [] },]

def run_cmd(instances, instance_idxs, cmd_tmpl):
    cassandra_seeds, statsd_seeds, cadence_seeds = get_seeds()
    for idx in instance_idxs:
        if idx not in instances:
            print " #"+str(idx)+" instance doesn't exist, skip..."
            continue
        if instances[idx]['State'] != 'running':
            print " #"+str(idx)+" instance("+instances[idx]['InstanceId']+") is not running, skip..."
            continue

        cmd = "ssh -i ~/i.pem ec2-user@"+public_ip+" "+cmd_tmpl.format(public_ip=instances[idx]['public_ip'], private_ip=instances[idx]['private_ip'], cassandra_seeds=cassandra_seeds, statsd_seeds=statsd_seeds, cadence_seeds=cadence_seeds, cluster=args.cluster)
        print "running: "+cmd
        if not args.dry_run :
            subprocess.call(cmd,shell=True)



def get_seeds():
    ############
    # Get seeds for cassandra/statsd/cadence
    cassandra_seeds, statsd_seeds, cadence_seeds = '127.0.0.1', '127.0.0.1:8125', '127.0.0.1:7933'
    if args.cluster in ['frontend', 'matching', 'history', 'cassandra']:
        filters[0]['Values'] = [ 'cadence-dev-longer-'+'cassandra' ]
        response = ec2.describe_instances(Filters=filters)
        ips = []
        #Reservations->Instances->PrivateIpAddress
        try:
            map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
        except KeyError as e:
            print e
        cassandra_seeds = reduce(lambda ip1,ip2: ip1+","+ip2, ips)

    if args.cluster in ['frontend', 'matching', 'history']:
        filters[0]['Values'] = [ 'cadence-dev-longer-'+'statsd' ]
        response = ec2.describe_instances(Filters=filters)
        ips = []
        try:
            map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
        except KeyError as e:
            print e
        #TODO only supports single host statsd
        if len(ips)>1:
            raise Exception("more than ONE statsd hosts are now supported yet!")
        if len(ips)>0:
            statsd_seeds = ips[0]+":8125"

        filters[0]['Values'] = [ 'cadence-dev-longer-'+'frontend' ]
        response = ec2.describe_instances(Filters=filters)
        ips = []
        try:
            map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
        except KeyError as e:
            print e
        if len(ips)>0:
            # only using one host due to the bug: https://github.com/uber/cadence/issues/358
            cadence_seeds = ips[0]+":7933"
    return cassandra_seeds, statsd_seeds, cadence_seeds



def terminate_instances(instances, instance_idxs):
    instance_ids = []
    for idx in instance_idxs:
        if idx not in instances:
            print " #"+str(idx)+" instance doesn't exist, skip..."
            continue
        if instances[idx]['State'] != 'running':
            print " #"+str(idx)+" instance("+instances[idx]['InstanceId']+") is not running, skip..."
            continue
        instance_ids.append(instances[idx]['InstanceId'])
    if len(instance_ids)==0:
        print "No instance to be terminated. Done."
    else:
        if args.dry_run:
            print "Trying to terminate instances:"+str(instance_ids)
        else:
            response = ec2.terminate_instances(InstanceIds=instance_ids)
            for ins in response['TerminatingInstances']:
                print "instance "+ins['InstanceId']+" is now "+ins['CurrentState']['Name']
    return


def print_instances(instances):
    for idx in instances:
        print "---------------------"
        print "("+str(idx)+")."+ instances[idx]['InstanceId'] + " is " + instances[idx]['State']
        print "\tpublic IP:\t"+instances[idx]['public_ip']
        print "\tprivate IP:\t"+instances[idx]['private_ip']
    print "############## Total:"+str(len(instances)) + " ##############"



######### main function begins here ##########
filters[0]['Values'] = [ 'cadence-dev-longer-'+args.cluster ]
response = ec2.describe_instances(
    Filters=filters
)

# print for debug
#pp = pprint.PrettyPrinter()
#pp.pprint(response)

# for: ssh -i ~/i.pem ec2-user@{public_ip} CMD
install_service_cmd = ""
if args.cluster == 'cassandra':
    install_service_cmd = '\'docker run  -d --name cadence-cassandra  --network=host  -p 7000:7000 -p 7001:7001 -p 7199:7199 -p 9042:9042 -p 9160:9160 -e CASSANDRA_BROADCAST_ADDRESS={private_ip} -e CASSANDRA_SEEDS={cassandra_seeds} cassandra:3.9\''
elif args.cluster == 'statsd':
    install_service_cmd = '\'docker run  -d --name cadence-statsd  --network=host  -p 80-81:80-81 -p 8025-8026:8025-8026 -p 2003:2003 -p 9160:9160 kamon/grafana_graphite\''
elif args.cluster in ['frontend', 'matching', 'history']:
    install_service_cmd = '\'docker run  -d --name cadence-{cluster} --network=host  -e CASSANDRA_SEEDS={cassandra_seeds} -e RINGPOP_SEEDS={cadence_seeds}  -e STATSD_ENDPOINT={statsd_seeds} -e SERVICES={cluster}  -p 7933-7935:7933-7935   ubercadence/longer-dev:0.3.1\''

# TODO
#'port forwarding cmd': 'ssh -f -N -L LOCAL_PORT:{private_ip}:REMOTE_PORT ec2-user@{public_ip} -i ~/i.pem'
cmd_map = {
    # 0 for customized command
    0: {
        'cmd': 'NOT a real command',
        'desc': 'run customized command'
    },

    # install docker
    1: {
        'cmd': '\'bash -s\' < ./bashscript/install_docker.sh',
        'desc': 'install docker'
       },

    # install service
    2:{
        'cmd':install_service_cmd,
        'desc': 'install service '+args.cluster
      },

    # uninstall service
    3:{
        'cmd': '\'docker rm -f cadence-{cluster}\'',
         'desc': 'uninstall service '+args.cluster
      },

    # remove image
    4: {
        'cmd': '\'docker rmi -f ubercadence/longer-dev:0.3.1\'',
        'desc': 'remove cadence image service(for deploying new code)'
       },

    5:{
        'cmd': '',
        'desc': 'login EC2 host'
      },

    6:{
        'cmd': '-f -N -L 8080:{private_ip}:80',
        'desc': 'forword remote 80 to 8080'
    },

    7:{
        'cmd': 'NOT a real command',
        'desc': 'Terminate EC2 instance'
    },

}


#Parsing ec2 response and print out brief
ins_cnt = 0
instances = {}
for res in response['Reservations']:

    for ins in res['Instances']:
        instances[ins_cnt] = {
            'InstanceId': ins['InstanceId'] ,
            'State': ins['State']['Name'],
        }

        public_ip, private_ip = 'None','None'
        if ins['State']['Name'] == 'running':
            public_ip = ins['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']
            private_ip = ins['PrivateIpAddress']

        instances[ins_cnt]['public_ip'] = public_ip
        instances[ins_cnt]['private_ip'] = private_ip

        #next
        ins_cnt += 1
print_instances(instances)


# Interactive operations
print "Choose operation:"
for idx in cmd_map:
    print "["+str(idx)+"]: "+cmd_map[idx]['desc']
sys.stdout.write(">>>")
op = int(raw_input())
if op not in cmd_map:
    print "Done without operation."
else:
    print "Choose instances (1-"+str(ins_cnt)+") to operate on"
    print_instances(instances)
    sys.stdout.write(">>>")
    target_str = str(raw_input())
    instance_idxs = []
    if '-' in target_str:
        ar = target_str.split('-')
        for n in range(int(ar[0]), int(ar[1])+1 ):
            instance_idxs.append(n)
    elif ',' in target_str:
        for n in target_str.split(','):
            instance_idxs.append(int(n))
    else:
        instance_idxs.append(int(target_str))
    if len(instance_idxs)==0:
        print "No instance to operate on. Done."
    else:
        cmd_tmpl = ""
        if op==0:# for customized command
            print "input command to be run:"
            sys.stdout.write(">>>")
            cmd_tmpl = str(raw_input())
        elif op==7: # for terminating EC2 instances
            terminate_instances(instances, instance_idxs)
        else:
            cmd_tmpl = cmd_map[op]['cmd']
            run_cmd(instances, instance_idxs, cmd_tmpl )
