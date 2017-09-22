import boto3,argparse,json,pprint

parser = argparse.ArgumentParser()
parser.add_argument("--cluster", choices=['cassandra', 'matching', 'history', 'frontend', 'stress'], required=True, help='Cluster type')

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

cnt = 0
for res in response['Reservations']:
    cnt += len(res)
    for ins in res['Instances']:
        print "---------------------"
        print ins['InstanceId'] + " is " + ins['State']['Name']
        print "public IP: "+ins['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']

print "############## Total:"+str(cnt) + " ##############"
