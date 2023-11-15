import json
import urllib.parse
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
import requests
from requests_aws4auth import AWS4Auth
from dateutil.tz import tzutc
import datetime
import base64

'''
Change 1 to trigger LF1-HW2 code update
'''


region = 'us-east-2' # e.g. us-west-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-photos-f3jsmmbtuddm7gpl2qwuhmylxm.us-east-2.es.amazonaws.com' # the OpenSearch Service domain, e.g. https://search-mydomain.us-west-1.es.amazonaws.com
index = 'photos'
datatype = '_doc'
url = host + '/' + index + '/' + datatype


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

'''
def query():
    q = {'query': {'multi_match': {'query': "Car"}}}
    
    region = 'us-east-2' # e.g. us-west-1
    service = 'es'
    #credentials = boto3.Session().get_credentials()
    #awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    HOST = 'search-photos-f3jsmmbtuddm7gpl2qwuhmylxm.us-east-2.es.amazonaws.com' # the OpenSearch Service domain, e.g. https://search-mydomain.us-west-1.es.amazonaws.com
    INDEX = 'photos'

    client = OpenSearch(hosts=[{
            'host': HOST,
            'port': 443
        }],
        http_auth=get_awsauth(region, service),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)

    hits = res['hits']['hits']
    print(hits)
'''

def lambda_handler(event, context):
    print("Printing Lambda event")
    print(event)
    
    # query()
    # return
    
    # Get the object from the event and show its content type
    print("PUT on s3 bucket triggered")
    bucket = event['Records'][0]['s3']['bucket']['name']
    print("BUCKET:", bucket)
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print("KEY:",key)
    
    try:
        # Get uploaded image from S3
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket, Key=key)
        print("Printing get_object Response")
        print(response)
        print("CONTENT TYPE: " + response['ContentType'])
        createdTimestamp = response["LastModified"].strftime("%Y-%m-%dT%H:%M:%S")
        print("Created Timestamp: ", createdTimestamp)
        
        # Using Rekognition to mine labels
        #
        # rekognition = boto3.client('rekognition')
        # response = rekognition.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':key}},
        #     MaxLabels=10,
        # )
        
        image_bytes = response['Body'].read()
        rekognition = boto3.client('rekognition')
        response = rekognition.detect_labels(Image={'Bytes': image_bytes},
            MaxLabels=10,
        )
        
        # Get labels from x-amz-meta-customlabels header
        print("Getting user specified custom labels from header")
        customLabels = response['ResponseMetadata'].get('x-amz-meta-customlabels', "")
        print("Custom labels:", customLabels)
        labels = list(set([customLabel.title() for customLabel in customLabels.split(",")])) if customLabels else []
        
        print('Detected labels for ' + key)
        print()
        for label in response['Labels']:
            print("Label: " + label['Name'])
            labels.append(label['Name'])
            print("Confidence: " + str(label['Confidence']))
        
        
        # Create JSON object and insert into OpenSearch
        # Data storage schema:
        # {
        #     'objectKey': 'my-photo.jpg',
        #     'bucket': 'my-photo-bucket',
        #     'createdTimestamp': '2018-11-05T12:40:02',
        #     'labels': [
        #           'person',
        #           'dog',
        #           'ball',
        #           'park'
        #       ]
        # }
        document = {
                    "objectKey": key,
                    "bucket": bucket,
                    "createdTimestamp": createdTimestamp,
                    "labels":  list(set(labels + [label_dict["Name"] for label_dict in response['Labels']]))
        }
        
        # #print(document)

        r = requests.post(url, auth=awsauth, json=document, headers={"Content-Type": "application/json"})
        print("Printing response from OpenSearch")
        print(r)
        
    except Exception as e:
        print(e)
        raise e
    
    
    return {
        'statusCode': 200
    }
    
    