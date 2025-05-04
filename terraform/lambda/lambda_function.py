import json
from urllib.parse import unquote_plus
import boto3
import os
import logging
print('Loading function')
logger = logging.getLogger()
logger.setLevel("INFO")
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
reckognition = boto3.client('rekognition')

table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))

def lambda_handler(event, context):
    logger.info(json.dumps(event, indent=2))
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    # Récupération de l'utilisateur et de l'UUID de la tâche
    try:
        user, post_id = key.split('/')[:2]
        logger.info(f"user: {user}\npost_id: {post_id}")
    except ValueError:
        logger.error("Format du nom de fichier invalide.")
        return

    # Ajout des tags user et task_uuid
    #user, post_id = f"USER#{user}", f"POST#{post_id}"

    # Appel à reckognition
    try:
        response = reckognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MaxLabels=5,
            MinConfidence=0.75
        )
    except Exception as e:
            logger.error(f"Erreur Rekognition : {e}")
            return
    
    # Récupération des résultats des labels
    labels = [label["Name"] for label in response["Labels"]]
    logger.info(f"Labels detected: {labels}")

    # Mise à jour de la table dynamodb
    table.update_item(
        Key={
             "user":user,
             "id":post_id
        },
        UpdateExpression="SET labels =:labels",
        ExpressionAttributeValues={":labels": labels},
        ReturnValues="UPDATED_NEW"
    )

    return {
        'statusCode': 200,
        'body': json.dumps({"success": True})
    }