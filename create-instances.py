import boto3,argparse,json,getpass


parser = argparse.ArgumentParser()
parser.add_argument("--region", "-r", choices=['us-east-1', 'us-west-1', 'us-east-2', 'us-west-2', 'ap-southeast-1','ap-southeast-2','ap-northeast-1','ap-northeast-2', 'ap-south-1', 'eu-west-1','eu-west-2', 'ca-central-1'], required=False, help='aws region', default='us-east-1')
parser.add_argument("--application", "-a", choices=['cassandra', 'matching', 'history', 'frontend', 'stress', 'worker', 'statsd'], required=True, help='application type that will be created')
parser.add_argument("--num", type=int, default=1, help='number of instances that will be created')
parser.add_argument("--instance-type", default='t2.medium')
parser.add_argument("--disk-size", type=int, default=30, help="disk size in GiB. Ensure to use at least 100 for Cassandra/statsd applications")
parser.add_argument("--ec2-image", default='ami-4fffc834', help="ec2 image to install on instance")
parser.add_argument("--key-name", required=True, help="AWS keypair for EC2 instance(make sure you have the private key(pem file))")
parser.add_argument("--subnet-id", required=True, help="AWS subnet-id")
parser.add_argument("--security-group-id", required=True, help="AWS security-group-id")
parser.add_argument("--deployment-group", "-d", default='cadence-dev-{username}'.format(username=getpass.getuser()), help="Use the same group for the EC2 instances you created. This is implemented as a name prefix of EC2 tag")

args = parser.parse_args()

ec2 = boto3.client('ec2', region_name=args.region)
#response = ec2.describe_instances()
print 'Going to request an on-demand EC2 instance...'

if args.disk_size >= 2048 or args.disk_size < 10:
    raise Exception('Disk size should be in [10, 2048), not all operating systems support root volumes that are greater than 2047 GiB.')

response = ec2.run_instances(
    BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'DeleteOnTermination': True,
                # See http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSVolumeTypes.html
                # Use default of gp2 is 100/300 when disk is less then 100GB
                # need bigger for Cassandra/statsd(100GB at least) so that we have higher disk iops
                'VolumeSize': args.disk_size,
                'VolumeType': 'gp2'
            }
        },
    ],
    ImageId=args.ec2_image,
    InstanceType=args.instance_type,
    KeyName=args.key_name,
    MaxCount=args.num,
    MinCount=args.num,
    Monitoring={
        'Enabled': True
    },

    # Will be needed for EBS optimized instances(R4)
    #EbsOptimized=True,
    NetworkInterfaces=[
        {
            'AssociatePublicIpAddress': True,
            'DeleteOnTermination': True,
            'DeviceIndex': 0,
            'SubnetId': args.subnet_id,
            "Groups":  [ args.security_group_id ]
        },
    ],

    TagSpecifications=[
        {
            'ResourceType' : 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': args.deployment_group+"-"+args.application
                },
                {
                    'Key': 'TeamName',
                    'Value': 'UberCadence'
                },
            ]
        },
    ],
    UserData=''
)

#print for debug
#print response

for ins in response['Instances']:
    print "###"
    print ins['InstanceId']
    print ins['NetworkInterfaces'][0]['PrivateIpAddresses']
