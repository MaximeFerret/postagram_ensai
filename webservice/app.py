#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
import boto3
from botocore.config import Config
import os
import uuid
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from getSignedUrl import getSignedUrl

load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################

from botocore.exceptions import ClientError

def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):
    """
    Poste un post ! Les informations du poste sont dans post.title, post.body et le user dans authorization
    """
    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")


    post_id = f"POST#{uuid.uuid4()}"
    user = f"USER#{authorization}"

    item = {
        "user": user,
        "id": post_id,
        "title": post.title,
        "body": post.body,
        "image": "",
    }

    res = table.put_item(Item=item)
    return res


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    if user:
        logger.info(f"Récupération des postes de : {user}")
        response = table.scan()
        items = [item for item in response.get("Items", []) if item.get("user") == f"USER#{user}"]
    else:
        logger.info("Récupération de tous les postes")
        response = table.scan()
        items = response.get("Items", [])

    # Ajout de l'URL présignée si une image est présente
    for post in items:
        if post.get("image"):
            try:
                url = create_presigned_url(bucket, post.get("image"))
                post["image"] = url
            except Exception as e:
                logger.error(f"Erreur génération URL signée : {e}")
                post["image"] = ""
        if "labels" in post:
            logger.info(f"Labels trouvés pour le post {post['id']}: {post['labels']}")
        else:
            post["labels"] = []
            
    return items



    
@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, authorization: str | None = Header(default=None)):
    user_key = f"USER#{authorization}"
    post_key = f"POST#{post_id}"

    logger.info(f"Suppression du post : {post_key} de l'utilisateur : {user_key}")

    # On récupère le post pour voir s'il y a une image
    response = table.get_item(
        Key={
            "user": user_key,
            "id": post_key
        }
    )

    item = response.get("Item", None)

    if item is None:
        return {"message": "Post non trouvé"}

    # Suppression de l'image dans S3 si présente
    if item.get("image"):
        try:
            s3_client.delete_object(
                Bucket=bucket,
                Key=item["image"]
            )
            logger.info(f"Image {item['image']} supprimée du bucket")
        except Exception as e:
            logger.error(f"Erreur suppression image S3 : {e}")

    # Suppression de la ligne dans DynamoDB
    res = table.delete_item(
        Key={
            "user": user_key,
            "id": post_key
        }
    )

    return res




#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str,filetype: str, postId: str,authorization: str | None = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################