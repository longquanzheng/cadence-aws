# cadence-aws
Create/manage Cadence service on AWS
See https://github.com/uber/cadence


# How?

## Prerequisite
* Python 2.7 (not tested in other versions)
* Boto3 for python: https://github.com/boto/boto3
* Install AWSCLI if you don't have it: http://docs.aws.amazon.com/cli/latest/userguide/awscli-install-bundle.html
* Set default AWS credential and region. Run "aws configure" to set them. See http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
* Prepare a private key for access EC2 instances. Usually it is from AWS EC2 keypair: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html . Save it to ~/ec2.pem (otherwise need to specify location in operate-instances.py)
* Prepare at least one subnet(please save the subnet id) for creating EC2 instances. Make sure your subnet doesn't have special rules to block traffic.
* Prepare a security group(please save the security group id) for creating EC2 Instaces. Make sure the security group allow ssh from outside and any TCP traffic inside.


## Step one: create initial ec2 instances
1. Create at least one instance for cassandra/frontend/matching/history applications respectively
2. Create EXACTLY one instance for statsd application, since we don't support distributed mode yet.

* Document of create-instances.py
```bash
$ python create-instances.py --help
usage: create-instances.py [-h] --application
                           {cassandra,matching,history,frontend,stress,statsd}
                           [--num NUM] [--instance-type INSTANCE_TYPE]
                           [--disk-size DISK_SIZE] [--ec2-image EC2_IMAGE]
                           --key-name KEY_NAME --subnet-id SUBNET_ID
                           --security-group-id SECURITY_GROUP_ID
                           [--deployment-group DEPLOYMENT_GROUP]

optional arguments:
  -h, --help            show this help message and exit
  --application {cassandra,matching,history,frontend,stress,statsd}, -a {cassandra,matching,history,frontend,stress,statsd}
                        application type that will be created
  --num NUM             number of instances that will be created
  --instance-type INSTANCE_TYPE
  --disk-size DISK_SIZE
                        disk size in GiB
  --ec2-image EC2_IMAGE
                        ec2 image to install on instance
  --key-name KEY_NAME   AWS keypair for EC2 instance(make sure you have the
                        private key(pem file))
  --subnet-id SUBNET_ID
                        AWS subnet-id
  --security-group-id SECURITY_GROUP_ID
                        AWS security-group-id
  --deployment-group DEPLOYMENT_GROUP, -d DEPLOYMENT_GROUP
                        Use the same group for the EC2 instances you created.
                        This is implemented as a name prefix of EC2 tag

```
* Example of create-instances.py Replace values of --key-name/--subnet-id/--security-group-id with what you've prepared in *Prerequisite*
```bash
$ python create-instances.py -a stress --key-name cadence-KEY --subnet-id subnet-xxxxxxxx --security-group-id sg-xxxxxxxx
Going to request an on-demand EC2 instance...
###
i-xxxxxxxxxxxxxxxx
[{u'PrivateDnsName': 'ip-10-x-x-x.ec2.internal', u'Primary': True, u'PrivateIpAddress': '10.x.x.x'}]

```




**The rest of the instructions are all executed by operate-instances.py**
**See example at the bottom**

## Step two: config/install Statsd-Graphite-Grafana application
1. Install docker
2. Install statsd service
3. Forward remote 80(Grafana) and 81(Graphite) ports to your local ports(use 8080/8081 as non-privileged ports)
4. Open http://localhost:8081 for Graphite. There should be statsd metrics.
5. Open http://localhost:8080 for Grafana, username and password are both "admin".

## Step three: config/install Cassandra application
1. Install docker
2. Install Cassandra service
3. Install jmxtrans
4. Go to Graphite to make sure that every Cassandra node is emitting metrics(In Tree: Metrics->stats->counters->servers->cassandra-10-...)

## Step four: config/install Cadence frontend/matching/history application
1. Install docker
2. Install frontend/matching/history service
3. Go to Graphite to make sure that Cadence service is emitting metrics(In Tree: Metrics->stats->counters->cadence)


## Docs & Example of operate-instances.py
```bash
$ python operate-instances.py --help
usage: operate-instances.py [-h] --application
                            {cassandra,matching,history,frontend,stress,statsd}
                            [--dry-run] [--pem PEM]
                            [--deployment-group DEPLOYMENT_GROUP]

optional arguments:
  -h, --help            show this help message and exit
  --application {cassandra,matching,history,frontend,stress,statsd}, -a {cassandra,matching,history,frontend,stress,statsd}
                        application type that will be created
  --dry-run             Only print out commands
  --pem PEM             Private key to login EC2 instances
  --deployment-group DEPLOYMENT_GROUP, -d DEPLOYMENT_GROUP
                        Use the same group for the EC2 instances you created.
                        This is implemented as a name prefix of EC2 tag

```
```bash
python operate-instances.py -a frontend
---------------------
(0).i-xxxxxxxxxxxxxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
---------------------
(1).i-xxxxxxxxxxxxxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
---------------------
(2).i-xxxxxxxxxxxxxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
############## Total:3 ##############
Choose operation:
[ jt ]:  Install jmxtrans (for Cassandra docker container)
[ tm ]:  Terminate EC2 instance
[ dk ]:  Install docker
[ lg ]:  Login EC2 host
[ cc ]:  Run a customized command
[ fw ]:  Forword a remote port(like 80[grafana] and 81([graphite]) to a local port(like 8080/8081)
[ sv ]:  Install service frontend
[ us ]:  Uninstall service frontend
[ ri ]:  Remove cadence image service(for deploying new code)
>>> dk
```
