import boto3,argparse,json,pprint,subprocess,sys,os,getpass,string
import cmds

pp = pprint.PrettyPrinter()
#pp.pprint(response)

parser = argparse.ArgumentParser()
parser.add_argument("--region", "-r", choices=['us-east-1', 'us-west-1', 'us-east-2', 'us-west-2', 'ap-southeast-1','ap-southeast-2','ap-northeast-1','ap-northeast-2', 'ap-south-1', 'eu-west-1','eu-west-2', 'ca-central-1'], required=False, help='aws region', default='us-east-1')
parser.add_argument("--application", "-a", choices=['cassandra', 'matching', 'history', 'frontend', 'stress', 'worker', 'statsd'], required=True, help='application type that will be created')
parser.add_argument("--dry-run", action='store_true', help='Only print out commands')
parser.add_argument("--pem", default='~/ec2.pem'.format(username=getpass.getuser()), required=False, help='Private key to login EC2 instances')
parser.add_argument("--deployment-group", "-d", default='cadence-dev-{username}'.format(username=getpass.getuser()), help="Use the same group for the EC2 instances you created. This is implemented as a name prefix of EC2 tag")
parser.add_argument("--operation", "-op", required=False, type=str, help='operation type to be executed')
parser.add_argument("--operation-params", required=False, help='operation params in key-values: k1:v1,k2:v2,k3:v3')
parser.add_argument("--target-instances", required=False, help='target instances to be operated: 0-N or 0,1,2,3')
args = parser.parse_args()


ec2 = boto3.client('ec2', region_name=args.region)
filters = [ { 'Name': 'tag:Name', 'Values': [] },]

def run_cmd(instances, instance_idxs, cmd_tmpls, params):
    cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds, cadence_frontend_json = get_seeds()

    for idx in instance_idxs:
        if idx not in instances:
            #print " #"+str(idx)+", skip..."
            continue
        if instances[idx]['State'] != 'running':
            print " #"+str(idx)+" instance("+instances[idx]['InstanceId']+") is not running, skip..."
            continue

        print "Now operate on #"+str(idx)+" ..."
        #TODO there is a bug about bash export command ...
        private_ip_under = instances[idx]['private_ip'].replace('.','_')

        for cmd_tmpl in cmd_tmpls:
            cmd = "ssh -o StrictHostKeyChecking=no -i {ec2_pem_path} ec2-user@".format(ec2_pem_path=args.pem)\
                    + instances[idx]['public_ip'] + " "\
                    +cmd_tmpl.format(\
                public_ip=instances[idx]['public_ip'], private_ip=instances[idx]['private_ip'],private_ip_under=private_ip_under, cassandra_seeds=cassandra_seeds,
                statsd_seeds=statsd_seeds, statsd_seed_ip=statsd_seed_ip, cadence_seeds=cadence_seeds, cadence_frontend_json = cadence_frontend_json,
                application=args.application, **params)
            print "\n <<<running: "+cmd+">>>"
            if not args.dry_run :
                subprocess.call(cmd,shell=True)


def parse_ips_from_ec2_response(response):
    ips = []
    #Reservations->Instances->PrivateIpAddress
    map(lambda r: map(lambda i: ips.append(i['PrivateIpAddress']) if 'PrivateIpAddress' in i and i['State']['Name']=='running' else ips, r['Instances'] ), response['Reservations'])
    return ips

def get_seeds():
    ############
    # Get seeds for cassandra/statsd/cadence
    cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds, cadence_frontend_json = '', '', '', '', ''

    filters[0]['Values'] = [ args.deployment_group+'-cassandra' ]
    response = ec2.describe_instances(Filters=filters)
    ips = parse_ips_from_ec2_response(response)
    if len(ips)==0:
        raise Exception("at least one Cassandra host need to be created first!")
    cassandra_seeds = reduce(lambda ip1,ip2: ip1+","+ip2, ips)

    filters[0]['Values'] = [ args.deployment_group+'-statsd' ]
    response = ec2.describe_instances(Filters=filters)
    ips = parse_ips_from_ec2_response(response)
    if len(ips)==0:
        raise Exception("at least one statsd host need to be created first!")
    #TODO only supports single host statsd
    if len(ips)>1:
        raise Exception("more than ONE statsd hosts are now supported yet!")
    if len(ips)>0:
        statsd_seeds = ips[0]+":8125"
        statsd_seed_ip = ips[0]

    filters[0]['Values'] = [ args.deployment_group+'-frontend' ]
    response = ec2.describe_instances(Filters=filters)
    ips = parse_ips_from_ec2_response(response)
    ip_ports = map(lambda ip: ip+":7933", ips)

    if len(ips)==0:
        raise Exception("at least one frontend host need to be created first!")
    if len(ips)>0:
        cadence_seeds = reduce(lambda ip1,ip2: ip1+","+ip2, ip_ports)

    cadence_frontend_json = json.dumps(ip_ports)
    cadence_frontend_json = cadence_frontend_json.replace('"','\\"')
    cadence_frontend_json = cadence_frontend_json.replace(' ','')
    return cassandra_seeds, statsd_seeds, statsd_seed_ip, cadence_seeds, cadence_frontend_json



def terminate_instances(instances, instance_idxs):
    instance_ids = []
    for idx in instance_idxs:
        if idx not in instances:
            #print " #"+str(idx)+" instance doesn't exist, skip..."
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
            state = ins['State']['Name']
            if state == 'terminated':
                continue

            instances[ins_cnt] = {
                'InstanceId': ins['InstanceId'] ,
                'State': state,
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


def parse_target_instance(target_str):
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
    return instance_idxs

def execute_operation(op, params, instances, instance_idxs, cmd_map ):
    #run command on instances
    if len(instance_idxs)==0:
        print "No instance to operate on. Done."
    else:
        if op=='tm': # for terminating EC2 instances
            terminate_instances(instances, instance_idxs)
        else:
            cmd_tmpls = cmd_map[op]['cmds']
            run_cmd(instances, instance_idxs, cmd_tmpls, params )
            print '---------------------------------------'
            print '>>>>>>>>>Done operation:'+op+"<<<<<<<<<<<"

##############################################
######### main function begins here ##########
##############################################
filters[0]['Values'] = [ args.deployment_group+"-"+args.application ]
response = ec2.describe_instances(
    Filters=filters
)
ins_cnt, instances = parse_ec2_response(response)
print_instances(instances)

if ins_cnt<=0:
    print "No ec2 instance to operate."
    sys.exit(0)

cmd_map = cmds.generate_cmd_map(args.application)
if args.operation is not None:
    instance_idxs = parse_target_instance(args.target_instances)
    params = {}
    for kv in args.operation_params.split(","):
        if ':' not in kv:
            continue
        pair = kv.split(":")
        params[pair[0]]=pair[1]
    print "execution {op} with params: {param_str}".format(op=args.operation, param_str=str(params))
    execute_operation(args.operation, params, instances, instance_idxs, cmd_map)
    sys.exit(0)

# Interactive operations
while True:
    print "Choose operation:"
    for idx in cmd_map:
        print "[ "+str(idx)+" ]:  "+cmd_map[idx]['desc']
    sys.stdout.write(">>>")
    op = str(raw_input())
    if op in ['x','exit','q','quit','done']:
        break
    if op not in cmd_map:
        print "Not a valid operation."
        continue

    # input extra params
    params = {}
    if 'params' in cmd_map[op]:
        for p in cmd_map[op]['params']:
            if 'default' in cmd_map[op]['params'][p]:
                default = str(cmd_map[op]['params'][p]['default'])
                default_desc = "[default: "+default+"]"
            else:
                default = default_desc = ''

            if 'choices' in cmd_map[op]['params'][p]:
                choices = map(str, cmd_map[op]['params'][p]['choices'])
                choices_desc = "(choices: "+",".join(choices)+")"
            else:
                choices = []
                choices_desc = ''


            while True:
                print "input {param_name}{default}{choices}:".format(param_name=p, default=default_desc,choices=choices_desc)
                sys.stdout.write(">>>")
                params[p] = str(raw_input())
                if len(params[p])<1:
                    params[p] = default

                if len(choices)>0 and params[p] not in choices:
                    print "{param_name} must be one of: {choices}".format(param_name=p, choices=str(choices_desc))
                    continue
                else:
                    #succ input params
                    break

    # choose instance to operate on, if only one, then don't aks for it
    instance_idxs = []
    if ins_cnt==1:
        instance_idxs.append(ins_cnt-1)
    else:
        print "Choose instances (0-"+str(ins_cnt-1)+") to operate on"
        print_instances(instances)
        sys.stdout.write(">>>")
        target_str = str(raw_input())
        instance_idxs = parse_target_instance(target_str)
    execute_operation(op, params, instances, instance_idxs, cmd_map)
