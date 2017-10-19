#/bin/bash
sudo yum update -y
sudo yum install go -y
sudo yum install gettext -y
export PATH=$PATH:/home/ec2-user/go/bin
export GOPATH=/home/ec2-user/go
mkdir -p /home/ec2-user/go/src/github.com/uber
mkdir -p /home/ec2-user/go/bin
curl https://glide.sh/get | sh

cd /home/ec2-user/go/src/github.com/uber
git clone https://github.com/uber/cadence.git

cd cadence
git checkout bench_aws
make bins_bench
