# coding:utf-8
from datetime import datetime
from datetime import timedelta
from __future__ import print_function
import sys, os
import xlsxwriter
import boto3
import json
import time


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


# Send query request to 'readings' table
def request_data(sensor_id, start_timestamp, end_timestamp):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="http://localhost:8000")
    table = dynamodb.Table('readings')

    response = table.query(
        TableName='readings',
        ConsistentRead=True,
        KeyConditionExpression='sensor_id = :sensor_id and published_at BETWEEN :start_timestamp AND :end_timestamp',
        ExpressionAttributeValues={
            ':sensor_id': {
                'S': sensor_id,
            },
            ':start_timestamp': {
                'N': str(start_timestamp)
            },
            ':end_timestamp': {
                'N': str(end_timestamp)
            },
        },
    )
    return response


def make_xlsx(event, context):
    print(event)
    response = request_data('TEMPERATURE_DHT11_1', 1490135972113, 1490137092113)
    print("Query succeeded:")
    print(json.dumps(response, indent=4, cls=DecimalEncoder))
