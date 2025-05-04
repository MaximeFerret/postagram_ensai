import boto3
from botocore.config import Config
from os import walk, getenv
from data import data
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / 'webservice' / '.env')

bucket = getenv("BUCKET")
table = getenv("DYNAMO_TABLE")
# Create an S3 resource
s3 = boto3.resource('s3')

f = []
for (dirpath, dirnames, filenames) in walk("s3"):
    print(filenames)
    if filenames:
        with open(f"{dirpath}/{filenames[0]}", 'rb') as file:
            s3.Object(bucket, f"{'/'.join(dirpath.split('/')[1:])}/{filenames[0]}" ).put(Body=file)

# Batch upload
# Get the service resource.
# Get the service resource.
my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
# Get the table.
table = dynamodb.Table(table)
# Read file
with table.batch_writer() as batch:
    for row in data:
        batch.put_item(Item=row)