#!/bin/bash
#
# cadence-bench         cadence-bench test service
# chkconfig: 2345 99 01
# description: cadence-bench is the bench test service for cadence service.

case "$1" in
start)
   cd /home/ec2-user/go/src/github.com/uber/cadence && (nohup ./cadence-bench-test aws &>stress.log & echo $!>/var/run/cadence-bench.pid) &
   ;;
stop)
   kill `cat /var/run/cadence-bench.pid`
   rm /var/run/cadence-bench.pid
   ;;
restart)
   $0 stop
   $0 start
   ;;
status)
   if [ -e /var/run/cadence-bench.pid ]; then
      echo cadence-bench is running, pid=`cat /var/run/cadence-bench.pid`
   else
      echo cadence-bench is NOT running
      exit 1
   fi
   ;;
*)
   echo "Usage: $0 {start|stop|status|restart}"
esac

exit 0
