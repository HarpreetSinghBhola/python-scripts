#!/bin/sh
#This script checks the sqs/sns metrics for the last 5 minutes and gives the output accordingly.
ENDTIME=`date +%Y-%m-%dT%H:%M:%SZ`
STARTTIME=`date --date 'now - 5 minutes' +%Y-%m-%dT%H:%M:%SZ`
temp_role=$(aws sts assume-role  --role-arn "arn:aws:iam::############:role/#############"  --role-session-name "cloudwatch-readonly")

export AWS_ACCESS_KEY_ID=$(echo $temp_role | jq .Credentials.AccessKeyId | xargs)
export AWS_SECRET_ACCESS_KEY=$(echo $temp_role | jq .Credentials.SecretAccessKey | xargs)
export AWS_SESSION_TOKEN=$(echo $temp_role | jq .Credentials.SessionToken | xargs)

#aws cloudwatch get-metric-statistics --namespace AWS/SNS --metric-name $1  --period 300 --statistics Average --dimensions Name=TopicName,Value=$2 --start-time $STARTTIME --end-time $ENDTIME --region=$3
if [ "$1" == "SNS" ]; then
output=$(aws cloudwatch get-metric-statistics --namespace AWS/SNS --metric-name $2  --period 300 --statistics Average --dimensions Name=TopicName,Value=$3 --start-time $STARTTIME --end-time $ENDTIME --region=$4 --query 'MetricDataResults[*].Values' --output text)
else
output=$(aws cloudwatch get-metric-statistics --namespace AWS/SQS --metric-name $2  --period 300 --statistics Average --dimensions Name=QueueName,Value=$3 --start-time $STARTTIME --end-time $ENDTIME --region=$4 --query 'Datapoints[*].Average' --output text)
fi
compare=$(awk 'BEGIN { print ( $output >= 1.0 ) ? "YES" : "NO" }')

if [ "$output" == "None" ] || [ "$output" == "0.0" ] || [ "$output" == '' ] || [ "$output" == ' ' ]; then
        echo "The metrics are: $output | perf=0;1;2"
        exit 0
elif [ "$compare" == "NO" ]; then
        echo "Warning... The metrics are: $output | perf={$output};1;2"
        exit 1
else
        echo "Alert... The metrics are: $output | perf={$output};1;2"
        exit 2

fi
