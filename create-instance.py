import boto3,argparse,json

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", choices=['cassandra', 'matching', 'history', 'frontend', 'stress'], required=True, help='Cluster type that will be created')
parser.add_argument("--num", type=int, default=1, help='number of instances that will be created')
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
                'VolumeSize': 30,
                'VolumeType': 'gp2'
            }
        },
    ],
    ImageId='ami-4fffc834',
    InstanceType='t2.medium',
    KeyName='cadence-longer',
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
            'SubnetId': 'subnet-ddaa8184',
            "Groups":  [ "sg-f0574d9c" ]
        },
    ],

    TagSpecifications=[
        {
            'ResourceType' : 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'cadence-dev-longer-'+args.cluster
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
