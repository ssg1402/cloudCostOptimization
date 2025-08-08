import boto3

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')

    # Fetch all snapshots owned by this account
    snapshots_data = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']

    # Get a list of IDs for all running EC2 instances
    running_instances = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    active_instances = {inst['InstanceId'] for res in running_instances['Reservations'] for inst in res['Instances']}

    # Check each snapshot to see if it should be deleted
    for snap in snapshots_data:
        snap_id = snap['SnapshotId']
        vol_id = snap.get('VolumeId')

        # Case 1: Snapshot not linked to any volume
        if not vol_id:
            ec2_client.delete_snapshot(SnapshotId=snap_id)
            print(f"Removed snapshot {snap_id} — not linked to any volume.")
            continue

        # Case 2: Volume exists but has no attachments.
        try:
            vol_info = ec2_client.describe_volumes(VolumeIds=[vol_id])
            attachments = vol_info['Volumes'][0].get('Attachments', [])
            
            if not attachments:
                ec2_client.delete_snapshot(SnapshotId=snap_id)
                print(f"Removed snapshot {snap_id} — source volume not attached to a running instance.")

        except ec2_client.exceptions.ClientError as err:
            if err.response['Error']['Code'] == 'InvalidVolume.NotFound':
                ec2_client.delete_snapshot(SnapshotId=snap_id)
                print(f"Removed snapshot {snap_id} — source volume no longer exists.")
