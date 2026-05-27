A simple photography portfolio inspired by Jay Maisel's photography portfolio. 
See: https://www.jaymaisel.com/

This website will be hosted using AWS Amplify and stored on a S3 bucket. The photos will be on another S3 bucket with a Cloudfront distribution in front of it. Route 53 will be used for simple and sensible URLs. AWS Lambda will be used to generate thumbnails and automatically add records to the noSQL dynamodb database including EXIF data. The website will be a Vue app. 

Over time, I would also like to make a CI/CD pipeline to build the html files and automatically add it to my target bucket for deployment. 