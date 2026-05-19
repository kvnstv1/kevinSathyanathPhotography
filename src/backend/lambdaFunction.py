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
region = "ap-southeast-6"
s3 = boto3.client('s3', region_name = region)
dynamodb = boto3.resource('dynamodb', region_name = region)

#DynamoDB database details
tableName = "photographyPortfolioMetadata"


#Cloudfront distribution
cloud = "d3mu20l8vaxqu0.cloudfront.net"


def getImageLocalVersion(fileStream):
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


def getExifData(fileStream):
    """ 
    Gets EXIF data from an image buffer.
    Preps a JSON object that will be used to update the dynamoDB 
    database
    """
    exif = {}
    
    try:
        fileStream.seek(0)
        
        with Image.open(fileStream) as img:
            exifObject = img.getexif()
            if not exifObject:
                print(f"Something went wrong getting the EXIF object.")
            
            #Deal with root data
            for k,v in exifObject.items():
                kName = TAGS.get(k,k)
                if kName in ['XPTitle', 'XPComment']:
                    try:
                        exif[kName] = v.decode('utf-16').rstrip('\x00')  #Solve windows formatting issues
                    except:
                        exif[kName] = v   #Force it through. Might need it.
                else:
                    exif[kName] = v
            
            #Get Actually vital photo data
            exif_ifd = exifObject.get_ifd(34665)
            for k,v in exif_ifd.items():
                kName = TAGS.get(k,k)
                exif[kName] = v
                
                if kName == 'UserComment' and isinstance(v,bytes):
                    try:
                        exif[kName] = v[8:].decode('utf-8', errors='ignore')
                    except:
                        pass
        
        
        return exif
    
    except Exception as e:
        print(f"Unforeseen error. Details: {e}")
        return {}




def lambdaHandler(event, context):
    
    #getImage()
    #getExifData()
    #generateThumbnail()
    #preparePayload()
    #updateDatabase

    #IOStream holding data from S3
    fileStream = io.BytesIO()
    getImageLocalVersion(fileStream)
    data = getExifData(fileStream)
    print("Data is ")
    print(data)
    
    print(f"Operations completed.")
    
if __name__ == "__main__":
    lambdaHandler(1,2)