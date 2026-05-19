from PIL import Image
from PIL.ExifTags import TAGS
from fractions import Fraction
import datetime 
import uuid
import json
import io
import re
import os
import boto3
import requests

#AWS SDK clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

#DynamoDB database details
tableName = "photographyPortfolioMetadata"
region = "ap-southeast-6"

#IOStream holding data from S3
fileStream = io.bytesIO()

#Cloudfront distribution
cloud = "d3mu20l8vaxqu0.cloudfront.net"


def getImageLocalVersion():
    """ 
    This downloads the image locally from the S3 bucket for local testing. 
    This will be done in-memory to simulate what will happen in the Lambda function
    """
    bucketName = 'kevin-photography-raws'
    fileName = 'Butterfly-2.jpg'
    cloudfrontURL = "https://" + cloud + "/" + fileName
    #s3.download.fileobj(bucketName, fileName, fileStream)
    response = requests.get(cloudfrontURL, stream=True)
    
    if (response.status_code == 200):
        for chunk in response.iter_content(chunk_size=8192):
            fileStream.write(chunk)
        fileStream.seek(0)
        print(f"Done.")      
    else:
        print(f"Error!!! Status code is {response.status_code}")
    




def lambda_handler(event, context):
    
    #getImage()
    #getExifData()
    #generateThumbnail()
    #preparePayload()
    #updateDatabase
    
    getImageLocalVersion()
    img = fileStream.read()
    
    
    print(f"Operations completed.")