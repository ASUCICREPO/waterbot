import os
import boto3
import json
from datetime import datetime, timezone

dynamo_client=boto3.client('dynamodb')
ssm_client=boto3.client('ssm')
table_arn=os.environ['TABLE_ARN']
s3_bucket=os.environ['S3_BUCKET']
param_name=os.environ['LAST_EXPORT_TIME_PARAM']


def handler(event,context):
    last_export_time_param_value=ssm_client.get_parameter(Name=param_name)['Parameter']['Value']
    last_export_time=datetime.fromisoformat(last_export_time_param_value)

    # on initial deploy, we set this date.  we must do a full incremental the first time.
    is_initial_export = last_export_time == datetime(1970,1,1,tzinfo=timezone.utc)

    new_export_time=datetime.now(timezone.utc)

    if is_initial_export:
        response=dynamo_client.export_table_to_point_in_time(
            TableArn=table_arn,
            S3Bucket=s3_bucket,
            ExportType="FULL_EXPORT",
            ExportFormat='DYNAMODB_JSON'
        )
    else:
        response=dynamo_client.export_table_to_point_in_time(
            TableArn=table_arn,
            S3Bucket=s3_bucket,
            ExportType="INCREMENTAL_EXPORT",
            ExportFormat='DYNAMODB_JSON',
            IncrementalExportSpecification={
                'ExportFromTime':last_export_time,
                'ExportToTime':new_export_time,
                'ExportViewType':'NEW_IMAGE'
            }
        )

    ssm_client.put_parameter(Name=param_name,Value=new_export_time.isoformat(),Overwrite=True)

     # Convert the response to a JSON-serializable format
    json_response = json.dumps(response, default=str)

    return json_response