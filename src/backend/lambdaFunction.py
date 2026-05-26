from PIL import Image
from PIL.ExifTags import TAGS
from fractions import Fraction
import datetime 
import io
import boto3
import os
import urllib.parse
import logging

# Init logging stuff
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS SDK data
region = "ap-southeast-6"
s3 = boto3.client('s3', region_name=region) 
dynamodb = boto3.resource('dynamodb', region_name=region)

# S3 buckets
source_bucket = "kevin-photography-raws"          
target_bucket = "kevin-photography-portfolio"  

tableName = "KevinPhotoSite"
cloud = "d3mu20l8vaxqu0.cloudfront.net"             


def getImageLocalVersion(fileStream, file_key):
    """
    Downloads images for use in local testing.
    And for lambda
    """    
    logger.info(f"Downloading raw asset directly from S3 bucket '{source_bucket}': {file_key}")
    try:
        s3.download_fileobj(source_bucket, file_key, fileStream)
        fileStream.seek(0)
        logger.info("Got image.")      
    except Exception as e:
        logger.error(f"Error getting image from {source_bucket}, Reason: {e}")
        raise e


def getfile_name(event):
    """
    Returns the filename for this image
    """
    s3_record = event['Records'][0]['s3']
    raw_key = s3_record['object']['key']
    actual_key = urllib.parse.unquote_plus(raw_key)
    parts = actual_key.split("/")
    
    # Derives album from top-level directory prefix; defaults safely to Miscellaneous
    album_name = parts[0].split('-')[0] if len(parts) >= 1 else 'Miscellaneous'
    file_name = parts[-1]
    
    logger.info(f"Album name: '{album_name}' | File Name: '{file_name}'")
    return album_name, file_name


def getExifData(fileStream):
    """
    Gets available EXIF data from image buffer in lambda memory.
    """
    exif = {}
    try:
        fileStream.seek(0)
        with Image.open(fileStream) as img:
            exifObject = img.getexif()
            
            for k, v in exifObject.items():
                kName = TAGS.get(k, k)
                if kName in ['XPTitle', 'XPComment']:
                    try:
                        exif[kName] = v.decode('utf-16').rstrip('\x00')
                    except:
                        exif[kName] = v
                else:
                    exif[kName] = v
            
            exif_ifd = exifObject.get_ifd(34665)
            for k, v in exif_ifd.items():
                kName = TAGS.get(k, k)
                exif[kName] = v
                if kName == 'UserComment' and isinstance(v, bytes):
                    try:
                        exif[kName] = v[8:].decode('utf-8', errors='ignore')
                    except:
                        pass
        logger.info("EXIF data read.")
        return exif
    except Exception as e:
        logger.warning(f"Could not get EXIF data. Reason: {e}")
        return {}


def generateDisplayImage(file_stream, file_name, album_name):
    """
    Generates a main image from potentially high quality JPEGs.
    Until now I have been limiting filesize of JPG exports from lightroom to save space.
    Going forward, I will bring maximum quality JPGs into the source bucket.
    Then put in a smaller file using lambda into the target bucket.
    Might even make this a webp image actually. 
    """
    logger.info("Starting HQ compression.")
    file_stream.seek(0)
    with Image.open(file_stream) as img:
        max_size = (2048, 2048)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        display_buffer = io.BytesIO()
        
        img.save(display_buffer, format='WEBP', quality=85)
        display_buffer.seek(0)
        
        clean_name = os.path.splitext(file_name)[0]
        display_key = f"{album_name}/{clean_name}.webp" if album_name != "Miscellaneous" else f"Miscellaneous/{clean_name}.webp"

        logger.info(f"Uploading HQ file to: '{display_key}'")
        s3.put_object(
            Bucket=target_bucket,
            Key=display_key,
            Body=display_buffer,
            ContentType="image/webp"  # Updated content type
        )
        display_buffer.close()
        return display_key


def generateThumbnail(file_stream, file_name, album_name):
    """
    Generates a Low quality thumbnail for use in frontend in viewing grid.
    """
    logger.info("Starting LQ Compression.")
    file_stream.seek(0)
    with Image.open(file_stream) as img:
        max_size = (400, 400)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        thumbnail_buffer = io.BytesIO()
        
        img.save(thumbnail_buffer, format='WEBP', quality=80)  
        thumbnail_buffer.seek(0) 
        
        clean_name = os.path.splitext(file_name)[0]
        thumbnail_key = f"{album_name}/thumbnails/thumb_{clean_name}.webp"

        logger.info(f"Uploading thumbnail to: '{thumbnail_key}'")
        s3.put_object(
            Bucket=target_bucket,
            Key=thumbnail_key,
            Body=thumbnail_buffer,
            ContentType="image/webp"  # Updated content type
        )
        thumbnail_buffer.close()
        return thumbnail_key


def prepareImageMetadata(data, file_name, file_url, thumbnail_url):
    """
    Makes JSON object for adding to the database.
    """
    try:
        f = Fraction(data.get('ExposureTime')).limit_denominator()
        formatted_exposure = f"{f.numerator}.0s" if f.denominator == 1 else f"{f}s"
    except:
        formatted_exposure = "Unknown"

    try:
        float_aperture = float(Fraction(data.get('FNumber')))
        formatted_aperture = f"f/{float_aperture:.1f}" if float_aperture % 1 != 0 else f"f/{int(float_aperture)}"
    except:
        formatted_aperture = "Unknown"
        
    logger.info("Returning JSON object with EXIF data.")
    return {
        "file_name": file_name,
        "fileUrl": file_url,
        "thumbnailUrl": thumbnail_url,
        "title": data.get("XPTitle") or os.path.splitext(file_name)[0], 
        "description": data.get("XPComment") or data.get("UserComment") or "No description provided.",
        "cameraDetails": {
            "camera": str(data.get("Model")) if data.get("Model") else "Unknown",
            "lens": str(data.get("LensModel")) if data.get("LensModel") else "Unknown",
            "iso": str(data.get("ISOSpeedRatings")) if data.get("ISOSpeedRatings") else "Unknown",
            "aperture": formatted_aperture,
            "exposure": formatted_exposure,
            "focalLength": f"{int(float(Fraction(data.get('FocalLength'))))}mm" if data.get("FocalLength") else "Unknown"
        }
    }


def handleAlbumDescriptionUpload(event, album_name):
    """
    Handles album description from txt files with same name as album
    """
    s3_record = event['Records'][0]['s3']
    bucket_name = s3_record['bucket']['name']
    raw_key = s3_record['object']['key']
    actual_key = urllib.parse.unquote_plus(raw_key)

    s3_response = s3.get_object(Bucket=bucket_name, Key=actual_key)
    text_content = s3_response['Body'].read().decode('utf-8').strip()

    today_date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    table = dynamodb.Table(tableName)

    logger.info(f"Adding description to database for: '{album_name}'")
    table.update_item(
        Key={"albumName": album_name},
        UpdateExpression="SET albumDescription = :desc, albumDisplayName = :name, lastUpdated = :date",
        ExpressionAttributeValues={
            ":desc": text_content,
            ":name": album_name.replace("-", " ").replace("_", " "),
            ":date":today_date
        }
    )
    logger.info(f"Successfully updated {album_name} with description.")


def appendImageToAlbumRecord(album_name, image_map):
    """
    Append images data and metadata to dynamoDB.
    """
    table = dynamodb.Table(tableName)
    
    update_expression = (
        "SET images = list_append(if_not_exists(images, :empty_list), :new_image), "
        "albumDisplayName = if_not_exists(albumDisplayName, :default_name)"
    )
    
    try:
        logger.info(f"Adding item to database: PK={album_name}")
        table.update_item(
            Key={"albumName": album_name},
            UpdateExpression=update_expression,
            ExpressionAttributeValues={
                ":new_image": [image_map],
                ":empty_list": [],
                ":default_name": album_name.replace("-", " ").replace("_", " ")
            }
        )
        logger.info("Successfully added record to database.")
    except Exception as e:
        logger.error(f"Failed to add item. Reason: {e}")
        raise e


def lambda_handler(event, context):
    """
    main function but for lambda
    """
    logger.info(f"Started processing for: {event}")
    
    s3_record = event['Records'][0]['s3']
    raw_key = s3_record['object']['key']
    actual_key = urllib.parse.unquote_plus(raw_key)
    
    #Failsafe. Don't want to pay $$$
    if "/thumbnails/" in actual_key or actual_key.split("/")[-1].startswith("thumb_"):        
        logger.info(f"Failsafe early exit due to detecting thumbnail for: '{actual_key}'")
        return {"statusCode": 200, "body": "No need to process this thumbnail."}

    album_name, file_name = getfile_name(event)
    
    # Process description if available. 
    if file_name.lower().endswith('.txt'):
        try:
            handleAlbumDescriptionUpload(event, album_name)
            return {"statusCode": 200, "body": "Successfully added description."}
        except Exception as e:
            logger.error(f"Failed to add description. Abort. Reason: {e}")
            return {"statusCode": 500, "body": "Failed to add description."}

    file_stream = io.BytesIO()
    getImageLocalVersion(file_stream, actual_key) 
    
    data = getExifData(file_stream)
    
    display_file_key = generateDisplayImage(file_stream, file_name, album_name)
    thumbnail_file_key = generateThumbnail(file_stream, file_name, album_name)
    
    file_url = f"https://{cloud}/{urllib.parse.quote(display_file_key)}"
    thumbnail_url = f"https://{cloud}/{urllib.parse.quote(thumbnail_file_key)}"
    
    exif_date_raw = data.get("DateTimeOriginal") or data.get("DateTime")
    if exif_date_raw and isinstance(exif_date_raw, str):
        try:
            date_part = exif_date_raw.split(" ")[0]
            photo_date = date_part.replace(":", "-")
            logger.info(f"The date to be used in the PK is: '{photo_date}'")
        except Exception as date_err:
            logger.warning(f"unexpected date parsing error: {date_err}. Defaulting to system UTC.")
            photo_date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    else:
        logger.info("No date data was found, or there was an error getting the date.")
        photo_date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')

    # Construct final registration metrics payload object
    image_metadata = prepareImageMetadata(data, file_name, file_url, thumbnail_url)
    image_metadata["captureDate"] = photo_date
    
    logger.info(f"Entry for database is prepared. It is: {image_metadata}")
    
    # Write to database using chronological index variables
    appendImageToAlbumRecord(album_name, image_metadata)
    
    logger.info("Pipeline completed.")
    return {
        "statusCode": 200,
        "body": f"Successfully completed processing stage for {file_name}"
    }