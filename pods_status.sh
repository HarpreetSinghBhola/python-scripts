#!/bin/sh
#This script checks the restart count of the pods in the namespace provided as second parameter to the script, the first parameter is the config file of kubernetes. It compares the restart count value and generates the appropriate warning/alert.
count=$(/usr/local/bin/kubectl --kubeconfig=$1 get pods --namespace=$2 |awk -F ' ' '{ print  $4 }'|grep -v RESTARTS|sort -nr | head -n 1)
if [ $count -gt 1 ] && [ $count -lt 3 ]; then
    echo "Warning: One or more Pods got restarted more than 1 once. | perf=$count;1;3"
    exit 1
elif [ $count -ge 3 ]; then
    echo "Critical: One or more pods got restarted more than 3 times | perf=$count;1;3"
    exit 2
else
    echo "OK: All pods are running fine. | perf=$count;1;3"
    exit 0
fi
