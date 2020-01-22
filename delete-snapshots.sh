#/bin/bash
#takes region and date as input parameters
aws ec2 describe-snapshots --region $1  --output json --query "sort_by(Snapshots[?StartTime > '$2' ],&StartTime)[].{SnapshotId: SnapshotId}" --output text>snaps.txt
while read snap; do
        echo $snap
        aws ec2 delete-snapshot --snapshot-id $snap --region $1
done <snaps.txt
