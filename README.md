# cadence-aws
Create/manage Cadence service on AWS
See https://github.com/uber/cadence


# How?

## Prerequisite
* Python 2.7
* Boto3 for python: https://github.com/boto/boto3
* AWS credential: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html  . Make sure you have credentials for default: run "aws configure" to check.
* Prepare a private key for access EC2 instances. Usually it is from AWS EC2 keypair: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html . Save it to ~/ec2.pem (otherwise need to specify location in operate-instances.py)
* Prepare at least one subnet(please save the subnet id) for creating EC2 instances. Make sure your subnet doesn't have special rules to block traffic.
* Prepare a security group(please save the security group id) for creating EC2 Instaces. Make sure the security group allow ssh from outside and any TCP traffic inside.


## Step one: create initial ec2 instances
1. Create at least one instance for cassandra/frontend/matching/history clusters respectively
2. Create EXACTLY one instance for statsd cluster, since we don't support distributed mode yet.

* Example of create-instances.py
```bash
python create-instances.py --cluster stress --key-name cadence-longer --subnet-id subnet-ddaa8xxx --security-group-id sg-f0574xxx
Going to request an on-demand EC2 instance...
###
i-0cb47790d9exxxxxx
[{u'PrivateDnsName': 'ip-10-x-x-x.ec2.internal', u'Primary': True, u'PrivateIpAddress': '10.x.x.x'}]

```

## Step two: config/install Statsd-Graphite-Grafana cluster
1. Install docker
2. Install statsd service
3. Forward remote 80/81 ports to your local ports for Graphite/Grafana

## Step three: config/install Cassandra cluster
1. Install docker
2. Install Cassandra service
3. Install jmxtrans
4. Go to Graphite to make sure that every Cassandra node is emitting metrics(In Tree: Metrics->stats->counters->servers->cassandra-10-...)

## Step four: config/install Cadence frontend/matching/history cluster
1. Install docker
2. Install frontend/matching/history service
3. Go to Graphite to make sure that Cadence service is emitting metrics(In Tree: Metrics->stats->counters->cadence)


## Example of operate-instances.py
```bash
python operate-instances.py --cluster frontend
---------------------
(0).i-061b42eb364bxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
---------------------
(1).i-061b42eb364bxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
---------------------
(2).i-061b42eb364bxxxx is running
	public IP:	x.x.x.x
	private IP:	10.x.x.x
############## Total:3 ##############
Choose operation:
[ jt ]:  Install jmxtrans (for Cassandra docker container)
[ tm ]:  Terminate EC2 instance
[ dk ]:  Install docker
[ lg ]:  Login EC2 host
[ cc ]:  Run a customized command
[ fw ]:  Forword a remote port(like 80[grafana] and 81([graphite]) to a local
[ sv ]:  Install service statsd
[ us ]:  Uninstall service statsd
[ ri ]:  Remove cadence image service(for deploying new code)
>>> dk
```
