# cadence-aws
Running Cadence on AWS
See https://github.com/uber/cadence

# Prerequisite
* Python 2.7
* AWS credential: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
* Private key for access EC2 instances. Usually from AWS EC2 keypair: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html

# Create instances
```bash
python reate-instances.py --cluster stress --key-name cadence-longer --subnet-id subnet-ddaa8xxx --security-group-id sg-f0574xxx
Going to request an on-demand EC2 instance...
###
i-0cb47790d9exxxxxx
[{u'PrivateDnsName': 'ip-10-x-x-x.ec2.internal', u'Primary': True, u'PrivateIpAddress': '10.x.x.x'}]

```

# Operate instances
```bash
py operate-instances.py --cluster frontend
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
	private IP:	10.4.127.180
############## Total:3 ##############
Choose operation:
[0]: run customized command
[1]: install docker
[2]: install service frontend
[3]: uninstall service frontend
[4]: remove cadence image service(for deploying new code)
[5]: login EC2 host
[6]: forword remote 80 to 8080
[7]: Terminate EC2 instance
>>>
```
