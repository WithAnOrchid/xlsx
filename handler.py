# coding:utf-8
from __future__ import print_function
from datetime import datetime
from datetime import timedelta
import sys, os
import xlsxwriter
import boto3
import json
import time
import decimal


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
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('readings')

    response = table.query(
        TableName='readings',
        ConsistentRead=True,
        KeyConditionExpression='sensor_id = :sensor_id AND published_at BETWEEN :start_timestamp AND :end_timestamp',
        ExpressionAttributeValues={
            ':sensor_id': sensor_id,
            ':start_timestamp': start_timestamp,
            ':end_timestamp': end_timestamp
        }
    )

    items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.query(
            TableName='readings',
            ConsistentRead=True,
            KeyConditionExpression='sensor_id = :sensor_id and published_at BETWEEN :start_timestamp AND :end_timestamp',
            ExpressionAttributeValues={
            ':sensor_id': sensor_id,
            ':start_timestamp': start_timestamp,
            ':end_timestamp': end_timestamp
            },
            ExclusiveStartKey=response['LastEvaluatedKey']
        )

        items.extend(response['Items'])

    return items
# End of request_data

def write_summary(sheet, type, count, start, end):
    # TODO
    # Write some simple text.
    # Widen the first column to make the text clearer.
    sheet.set_column('A1:A4', 25)
    sheet.write('A1', u'导出时间:', bold)
    sheet.set_column('B1:B4', 25)
    beijing_time = datetime.utcnow() + timedelta(hours=8)
    sheet.write('B1', beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], center_align)

    sheet.write('A2', u'数据总数:', bold)
    sheet.write('B2', count, center_align)

    temp = datetime.fromtimestamp(start / 1e3)
    temp = temp +  timedelta(hours=8)
    sheet.write('A3', u'起始时间:', bold)
    sheet.write('B3', temp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], center_align)

    temp = datetime.fromtimestamp(end / 1e3)
    temp = temp +  timedelta(hours=8)
    sheet.write('A4', u'结束时间:', bold)
    sheet.write('B4', temp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], center_align)

    sheet.set_column('C6:C6', 25)
    sheet.set_column('D7:D7', 10)
    sheet.write('A6', u'设备ID')
    sheet.write('B6', u'模块ID')
    sheet.write('C6', u'记录时间')
    sheet.write('D6', type)
    return

def write_data(sheet, data):
    device_id_column = 'A'  # starts from A7
    sensor_id_column = 'B'
    published_at_column = 'C'
    data_column = 'D'
    current_row = 7
    for reading in data:
        # Write device_id
        device_id_position = device_id_column + str(current_row)
        sheet.write(device_id_position, reading['device_id'])
        # Write sensor_id
        sensor_id_position = sensor_id_column + str(current_row)
        sheet.write(sensor_id_position, reading['sensor_id'])
        # Write published_at
        published_at_position = published_at_column + str(current_row)
        tempDateTime = datetime.utcfromtimestamp(float(reading['published_at'])/1e3)
        tempDateTime = tempDateTime + timedelta(hours=8)
        tempDateTime = tempDateTime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        sheet.write(published_at_position, tempDateTime)
        # Writer data
        reading_position = data_column + str(current_row)
        sheet.write(reading_position, float(reading['sensor_reading']))

        current_row = current_row + 1
    return

def create_xlsx(items, start_timestamp, end_timestamp):
    date_fmt = '%Y-%m-%d_%H-%M-%S'
    beijing_time = datetime.utcnow() + timedelta(hours=8)

    # Define filename and filepath
    filename = beijing_time.strftime(date_fmt) + '.xlsx'
    filepath ='/tmp/' + filename

    # Create an new Excel file and add a worksheet.
    workbook = xlsxwriter.Workbook(filepath)
    # Add a bold format to use to highlight cells.
    global bold
    bold = workbook.add_format({'bold': True})
    global center_align
    center_align = workbook.add_format({'align': 'center'})

    # TODO
    temperature_sheet = workbook.add_worksheet(u'温度')
    write_summary(temperature_sheet, u'温度 (℃)', len(items), start_timestamp, end_timestamp)
    write_data(temperature_sheet, items)
    workbook.close()

    # Upload to S3
    s3 = boto3.resource('s3')
    s3.Object('xlsx-export', filename).put(Body=open(filepath, 'rb'), ACL='public-read')


def export_to_xlsx(event, context):
    print(json.dumps(event))

    response = request_data('TEMPERATURE_DHT11_1', 1490135972113, 1490137092113)
    create_xlsx(response, 1490135972113, 1490137092113)
    print("Query succeeded:")
    print(json.dumps(response, indent=4, cls=DecimalEncoder))
    return response[0]
