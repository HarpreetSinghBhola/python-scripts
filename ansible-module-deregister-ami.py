#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['stableinterface'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
'''
EXAMPLES = '''
'''

RETURN = '''
'''

from datetime import date
from datetime import time
from datetime import datetime
import boto3
import sys
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import (boto3_conn, boto3_tag_list_to_ansible_dict, camel_dict_to_snake_dict,
                                      ec2_argument_spec, get_aws_connection_info)

#from ansible.module_utils.ec2 import get_aws_connection_info, ec2_argument_spec, boto3_conn, camel_dict_to_snake_dict
from ansible.module_utils.ec2 import ansible_dict_to_boto3_tag_list, boto3_tag_list_to_ansible_dict, compare_aws_tags
from ansible.module_utils.aws.core import AnsibleAWSModule

try:
    import botocore
except ImportError:
    pass

def deregister_image(module, connection, image_id):
    delete_snapshot = module.params.get('delete_snapshot')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    image = get_image_by_id(module, connection, image_id)
    if image is None:
        return None

    # Get all associated snapshot ids before deregistering image otherwise this information becomes unavailable.
    snapshots = []
    if 'BlockDeviceMappings' in image:
        for mapping in image.get('BlockDeviceMappings'):
            snapshot_id = mapping.get('Ebs', {}).get('SnapshotId')
            if snapshot_id is not None:
                snapshots.append(snapshot_id)

    # When trying to re-deregister an already deregistered image it doesn't raise an exception, it just returns an object without image attributes.
    if 'ImageId' in image:
        try:
            connection.deregister_image(ImageId=image_id)
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            module.fail_json_aws(e, msg="Error deregistering image")
    else:
        module.exit_json(msg="Image %s has already been deregistered." % image_id, changed=False)

    for snapshot_id in snapshots:
        connection.delete_snapshot(SnapshotId=snapshot_id)


def get_image_by_id(module, connection, image_id):
    try:
        try:
            images_response = connection.describe_images(ImageIds=[image_id])
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            module.fail_json_aws(e, msg="Error retrieving image %s" % image_id)
        images = images_response.get('Images')
        no_images = len(images)
        if no_images == 0:
            return None
        if no_images == 1:
            result = images[0]
            try:
                result['LaunchPermissions'] = connection.describe_image_attribute(Attribute='launchPermission', ImageId=image_id)['LaunchPermissions']
                result['ProductCodes'] = connection.describe_image_attribute(Attribute='productCodes', ImageId=image_id)['ProductCodes']
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] != 'InvalidAMIID.Unavailable':
                    module.fail_json_aws(e, msg="Error retrieving image attributes for image %s" % image_id)
            except botocore.exceptions.BotoCoreError as e:
                module.fail_json_aws(e, msg="Error retrieving image attributes for image %s" % image_id)
            return result
        module.fail_json(msg="Invalid number of instances (%s) found for image_id: %s." % (str(len(images)), image_id))
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
        module.fail_json_aws(e, msg="Error retrieving image by image_id")

def get_image_by_tags(module, connection, group):
    images_response = connection.describe_images(Filters=[{'Name': 'tag:group','Values': [group]}])
    id_to_delete = []
    images_id = []
    today = datetime.now()
    tag = []
    images = images_response.get('Images')
    no_images = len(images)
    if no_images == 0:
        return None
    for reservation in images_response["Images"]:
        images_id.append(reservation["ImageId"])
    for i in range(len(images_id)):
        image_data = get_image_by_id(module, connection, images_id[i])
        if 'CreationDate' in image_data:
            images_creation_date = image_data.get('CreationDate')
            imagedate = datetime.strptime(images_creation_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        if 'Tags' in image_data:
            for mapp in image_data.get('Tags'):
                temp = mapp.get('Value')
                tag.append(temp)
        for val in range(len(tag)):
            vals = tag[val]
            if vals != module.params.get('group'):
                days_retention = vals
                delta = today-imagedate
                if delta.days > int(vals):
                    id_to_delete.append(images_id[i])
    for j in range(len(id_to_delete)):
        deregister_image(module, connection, id_to_delete[j])
    images_deleted = list(dict.fromkeys(id_to_delete))
    module.exit_json(msg="AMI Deleted. %s" % images_deleted)
#    module.exit_json(msg="Successful")

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        group=dict(),
        delete_snapshot=dict(default=True, type='bool'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(default=1200, type='int'),
        state=dict(default='present', choices=['present', 'absent'])
    ))

    module = AnsibleAWSModule(
        argument_spec=argument_spec
        # required_if=[
            # ['state', 'absent',[image_id]],
        # ]
    )
    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        connection = boto3_conn(module, conn_type='client', resource='ec2', region=region, endpoint=ec2_url, **aws_connect_kwargs)
    except botocore.exceptions.NoRegionError:
        module.fail_json(msg=("Region must be specified as a parameter in AWS_DEFAULT_REGION environment variable or in boto configuration file."))

    if module.params.get('state') == 'absent':
        get_image_by_tags(module, connection, module.params.get('group'))
    else:
        module.fail_json(msg="This module is only intended to deregister the AMI and delete the associated snapshots.")

if __name__ == '__main__':
    main()
