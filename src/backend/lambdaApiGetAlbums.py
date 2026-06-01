import json
import logging
import boto3
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region = "ap-southeast-6"
dynamodb = boto3.resource('dynamodb', region_name=region)
table = dynamodb.Table('KevinPhotoSite')

class DecimalEncoder(json.JSONEncoder):
    """
    DynamoDB will return decimals in a way that boto3 will parse as decimal. This is not 
    a primitive type in Python and will prevent the response from being easily pared to JSON.
    This helper class will do the conversion. 
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    logger.info(f"Starting fetch of items from dynamodb.")

    try:
        response = table.scan()
        items = response.get("Items", [])

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey = response['LastEvaluatedKey'])
            items.extend(response.get("Items", []))
        
        return {
            "statusCode" : 200,
            "headers" : {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            },
            "body": json.dumps(items, cls = DecimalEncoder)
        }
    
    except Exception as e:
        logger.error(f"Error prevented completion of GET. Reason: {e}")

        return {
            "statusCode" : 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": "Internal service error" , "details": str(e)}) 
        }