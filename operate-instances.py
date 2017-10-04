import boto3,argparse,json,pprint,subprocess,sys,os,getpass
import cmds

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", required=True, help='Cluster type')
parser.add_argument("--dry-run", action='store_true', help='Only print out commands')
parser.add_argument("--pem", default='~/ec2.pem'.format(username=getpass.getuser()), required=False, help='Private key to login EC2 instances')
parser.add_argument("--tag-prefix", default='cadence-dev-{username}-'.format(username=getpass.getuser()))
args = parser.parse_args()


ec2 = boto3.client('ec2')
filters = [ { 'Name': 'tag:Name', 'Values': [] },]

def run_cmd(instances, instance_idxs, cmd_tmpls, params):
    cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds = get_seeds()

    for idx in instance_idxs:
        if idx not in instances:
            print " #"+str(idx)+" instance doesn't exist, skip..."
            continue
        if instances[idx]['State'] != 'running':
            print " #"+str(idx)+" instance("+instances[idx]['InstanceId']+") is not running, skip..."
            continue

        #TODO there is a bug about bash export command ...
        private_ip_under = instances[idx]['private_ip'].replace('.','_')

        for cmd_tmpl in cmd_tmpls:
            cmd = "ssh -i {ec2_pem_path} ec2-user@".format(ec2_pem_path=args.pem)\
                    + instances[idx]['public_ip'] + " "\
                    +cmd_tmpl.format(\
                public_ip=instances[idx]['public_ip'], private_ip=instances[idx]['private_ip'],private_ip_under=private_ip_under, cassandra_seeds=cassandra_seeds,
                statsd_seeds=statsd_seeds, statsd_seed_ip=statsd_seed_ip, cadence_seeds=cadence_seeds, cluster=args.cluster, **params)
            print "\n <<<running: "+cmd+">>>"
            if not args.dry_run :
                subprocess.call(cmd,shell=True)



def get_seeds():
    ############
    # Get seeds for cassandra/statsd/cadence
    cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds = '', '', '', ''

    filters[0]['Values'] = [ args.tag_prefix+'cassandra' ]
    response = ec2.describe_instances(Filters=filters)
    ips = []
    #Reservations->Instances->PrivateIpAddress
    try:
        map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
    except KeyError as e:
        print e
    cassandra_seeds = reduce(lambda ip1,ip2: ip1+","+ip2, ips)
    if len(ips)==0:
        raise Exception("at least one Cassandra host need to be created first!")

    filters[0]['Values'] = [ args.tag_prefix+'statsd' ]
    response = ec2.describe_instances(Filters=filters)
    ips = []
    try:
        map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
    except KeyError as e:
        print e
    if len(ips)==0:
        raise Exception("at least one statsd host need to be created first!")
    #TODO only supports single host statsd
    if len(ips)>1:
        raise Exception("more than ONE statsd hosts are now supported yet!")
    if len(ips)>0:
        statsd_seeds = ips[0]+":8125"
        statsd_seed_ip = ips[0]

    filters[0]['Values'] = [ args.tag_prefix+'frontend' ]
    response = ec2.describe_instances(Filters=filters)
    ips = []
    try:
        map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']), r['Instances'] ), response['Reservations'])
    except KeyError as e:
        print e
    if len(ips)==0:
        raise Exception("at least one frontend host need to be created first!")
    if len(ips)>0:
        # only using one host due to the bug: https://github.com/uber/cadence/issues/358
        cadence_seeds = ips[0]+":7933"
    return cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds



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


def parse_ec2_response(response):
    # print for debug
    #pp = pprint.PrettyPrinter()
    #pp.pprint(response)
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
    return ins_cnt, instances


##############################################
######### main function begins here ##########
##############################################
filters[0]['Values'] = [ args.tag_prefix+args.cluster ]
response = ec2.describe_instances(
    Filters=filters
)
ins_cnt, instances = parse_ec2_response(response)
print_instances(instances)

if ins_cnt<=0:
    print "No ec2 instance to operate."
    sys.exit(0)

cmd_map = cmds.generate_cmd_map(args.cluster)
# Interactive operations
print "Choose operation:"
for idx in cmd_map:
    print "[ "+str(idx)+" ]:  "+cmd_map[idx]['desc']
sys.stdout.write(">>>")
op = str(raw_input())
if op not in cmd_map:
    print "Done without operation."
else:
    #need to input extra params
    params = {}
    if 'params' in cmd_map[op]:
        for p in cmd_map[op]['params']:
            print "input {param_name}:".format(param_name=p)
            sys.stdout.write(">>>")
            params[p] = '\''+str(raw_input())+'\''

    # choose instance to operate on, if only one, then don't aks for it
    instance_idxs = []
    if ins_cnt==1:
        instance_idxs.append(ins_cnt-1)
    else:
        print "Choose instances (0-"+str(ins_cnt-1)+") to operate on"
        print_instances(instances)
        sys.stdout.write(">>>")
        target_str = str(raw_input())
        if '-' in target_str:
            ar = target_str.split('-')
            for n in range(int(ar[0]), int(ar[1])+1 ):
                instance_idxs.append(n)
        elif ',' in target_str:
            for n in target_str.split(','):
                instance_idxs.append(int(n))
        else:
            instance_idxs.append(int(target_str))

    #run command on instances
    if len(instance_idxs)==0:
        print "No instance to operate on. Done."
    else:
        if op=='tm': # for terminating EC2 instances
            terminate_instances(instances, instance_idxs)
        else:
            cmd_tmpls = cmd_map[op]['cmds']
            run_cmd(instances, instance_idxs, cmd_tmpls, params )
