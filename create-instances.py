import boto3,argparse,json,getpass


parser = argparse.ArgumentParser()
parser.add_argument("--application", "-a", choices=['cassandra', 'matching', 'history', 'frontend', 'stress', 'statsd'], required=True, help='application type that will be created')
parser.add_argument("--num", type=int, default=1, help='number of instances that will be created')
parser.add_argument("--instance-type", default='t2.medium')
parser.add_argument("--disk-size", type=int, default=30, help="disk size in GiB")
parser.add_argument("--ec2-image", default='ami-4fffc834', help="ec2 image to install on instance")
parser.add_argument("--key-name", required=True, help="AWS keypair for EC2 instance(make sure you have the private key(pem file))")
parser.add_argument("--subnet-id", required=True, help="AWS subnet-id")
parser.add_argument("--security-group-id", required=True, help="AWS security-group-id")
parser.add_argument("--deployment-group", "-d", default='cadence-dev-{username}-'.format(username=getpass.getuser()), help="Use the same group for the EC2 instances you created. This is implemented as a name prefix of EC2 tag")

args = parser.parse_args()

ec2 = boto3.client('ec2')
#response = ec2.describe_instances()
print 'Going to request an on-demand EC2 instance...'

response = ec2.run_instances(
    BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'DeleteOnTermination': True,
                # Use default of gp2 is 100/3000
                #'Iops': 100,
                # need bigger for Cassandra
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
                    'Value': args.deployment_group+args.application
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
