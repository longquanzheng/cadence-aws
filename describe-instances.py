import boto3,argparse,json,pprint

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", required=True, help='Cluster type')

args = parser.parse_args()

ec2 = boto3.client('ec2')

response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'cadence-dev-longer-'+args.cluster
            ]
        },
    ]
)

pp = pprint.PrettyPrinter()
pp.pprint(response)

docker_cmd_tmpl = 'ssh -i ~/i.pem ec2-user@{public_ip} \'bash -s\' < ./bashscript/install_docker.sh'
statsd_cmd_tmpl = 'ssh -i ~/i.pem ec2-user@{public_ip} \'docker run --name cadence-statsd -d -p 8080:80 -p 2003:2003 -p 8125:8125 -p 8126:8126 hopsoft/graphite-statsd\''
common_tmpl = 'ssh -i ~/i.pem ec2-user@{public_ip} \'docker run --network=host -d -e CASSANDRA_SEEDS=10.4.124.208,10.4.125.14 -e RINGPOP_SEEDS=10.4.127.180:7933  -e STATSD_ENDPOINT=127.0.0.1:8125 -e SERVICES={cluster}  -p 7933-7935:7933-7935 --name cadence-{cluster}  ubercadence/longer-dev:0.3.1\''
port_forward_tmpl = 'ssh -f -N -L {local_port}:{private_ip}:8080 ec2-user@{public_ip} -i ~/i.pem'

service_cmd_tmpl_map = {
    'cassandra' : 'ssh -i ~/i.pem ec2-user@{public_ip} \'docker run  -d --name cadence-cassandra  -p 7000:7000 -p 7001:7001 -p 7199:7199 -p 9042:9042 -p 9160:9160 -e CASSANDRA_BROADCAST_ADDRESS={private_ip} -e CASSANDRA_SEEDS=10.4.124.208,10.4.125.14 cassandra:3.9\'',
    'matching' : common_tmpl,
    'history' : common_tmpl,
    'frontend' : common_tmpl,
    'stress' : ''
}

service_rm_cmd_tmpl = 'ssh -i ~/i.pem ec2-user@{public_ip} \'docker rm -f cadence-{cluster}\''

image_rm_cmd_tmpl = 'ssh -i ~/i.pem ec2-user@{public_ip} \'docker rmi -f ubercadence/longer-dev:0.3.1\''

service_port_base_map = {
    'cassandra' : 8100,
    'matching' : 8200,
    'history' : 8300,
    'frontend' : 8400,
    'stress' : 8500,
}

install_docker_cmd = ''
install_statsd_cmd = ''
install_service_cmd = ''
rm_service_cm = ''
rm_image_cmd = ''
port_forward_cmd = ''

cnt = 0
port_cnt = 0
for res in response['Reservations']:
    cnt += len(res)

    for ins in res['Instances']:

        print "---------------------"
        print ins['InstanceId'] + " is " + ins['State']['Name']
        if ins['State']['Name'] != 'running':
            continue
        public_ip = ins['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']
        private_ip = ins['PrivateIpAddress']
        local_port = service_port_base_map[args.cluster] + port_cnt
        port_cnt +=1

        print "ssh -i ~/i.pem ec2-user@"+public_ip
        print "private IP: "+private_ip
        install_docker_cmd += " ; "+docker_cmd_tmpl.format(public_ip=public_ip,private_ip=private_ip,cluster=args.cluster)
        install_statsd_cmd += " ; "+statsd_cmd_tmpl.format(public_ip=public_ip,private_ip=private_ip,cluster=args.cluster)
        install_service_cmd += " ; "+service_cmd_tmpl_map[args.cluster].format(public_ip=public_ip,private_ip=private_ip,cluster=args.cluster)
        port_forward_cmd += " ; "+port_forward_tmpl.format(private_ip=private_ip,local_port=local_port, public_ip=public_ip)
        rm_service_cm += " ; " + service_rm_cmd_tmpl.format(public_ip=public_ip,cluster=args.cluster)
        rm_image_cmd += " ; " + image_rm_cmd_tmpl.format(public_ip=public_ip)

print "############## Total:"+str(cnt) + " ##############"

print "DOCKER:\n "+install_docker_cmd[3:]
print "#######################"
print "STATSD:\n "+install_statsd_cmd[3:]
print "#######################"
print "START service: \n"+install_service_cmd[3:]
print "#######################"
print "STOP service: \n"+rm_service_cm[3:]
print "#######################"
print "REMOVE image: \n"+rm_image_cmd[3:]
print "#######################"
print "PORT: \n"+port_forward_cmd[3:]
