import boto3,argparse,json,pprint,subprocess,sys

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", required=True, help='Cluster type')
args = parser.parse_args()

ec2 = boto3.client('ec2')
filters = [ { 'Name': 'tag:Name', 'Values': [] },]

def run_cmd(ec2_response, host_id, cmd_tmpl, cluster):
    cassandra_seeds, statsd_seeds, cadence_seeds = get_seeds()
    ins_cnt = 0
    for res in ec2_response['Reservations']:

        for ins in res['Instances']:
            ins_cnt += 1
            if ins_cnt != host_id and host_id != 0:
                continue
            if ins['State']['Name'] != 'running':
                print " instance #"+str(ins_cnt)+" is not running, skip..."
                continue
            public_ip = ins['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']
            private_ip = ins['PrivateIpAddress']

            cmd = "ssh -i ~/i.pem ec2-user@"+public_ip+" "+cmd_tmpl.format(public_ip=public_ip, private_ip=private_ip, cassandra_seeds=cassandra_seeds, statsd_seeds=statsd_seeds, cadence_seeds=cadence_seeds, cluster=cluster)
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
    # reserve 0 for customized command
    #0: {}

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
      }
}

ins_cnt = 0
for res in response['Reservations']:

    for ins in res['Instances']:
        ins_cnt += 1
        print "---------------------"
        print "("+str(ins_cnt)+")."+ins['InstanceId'] + " is " + ins['State']['Name']
        if ins['State']['Name'] != 'running':
            continue
        public_ip = ins['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']
        private_ip = ins['PrivateIpAddress']

        print "\tpublic IP:\t"+public_ip
        print "\tprivate IP:\t"+private_ip


print "############## Total:"+str(ins_cnt) + " ##############"
print "[0 -"+str(len(cmd_map))+"] to execute command on host(s), type anyother to exit."
print "[0]: run customized command. "
for idx in cmd_map:
    print "["+str(idx)+"]: "+cmd_map[idx]['desc']
sys.stdout.write(">>>")
n = int(raw_input())
if n<0 and not n in cmd_map:
    print "Done without operation."
else:
    cmd_tmpl = ""
    if n==0:
        print "input command to be run:"
        sys.stdout.write(">>>")
        cmd_tmpl = str(raw_input())
    else:
        cmd_tmpl = cmd_map[n]['cmd']
    print "Choose host (1-"+str(ins_cnt)+") to execute command, 0 for ALL"
    sys.stdout.write(">>>")
    host_id = int(raw_input())
    if host_id<0 or host_id>ins_cnt:
        print "Wrong host id! Done without operation."
    else:
        run_cmd(response, host_id, cmd_tmpl, cluster=args.cluster, )
