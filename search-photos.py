import json
import os
import inflection

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

REGION = 'us-east-2'
HOST = 'search-photos-f3jsmmbtuddm7gpl2qwuhmylxm.us-east-2.es.amazonaws.com'
INDEX = 'photos'

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

def query(term):
    q = {'size': 5, 'query': {'multi_match': {'query': term}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)
    print(res)

    hits = res['hits']['hits']
    results = []
    for hit in hits:
        results.append(hit['_source'])

    return results


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

def contructSearchResponse(results):
    '''An array of photos where each photo is an object with keys of
    url:string, labels: [string]'''
    
    response = []
    
    for item in results:
        for picture in item:
            pictureName = picture["objectKey"]
            url = "https://vedantgannuphotos.s3.us-east-2.amazonaws.com/{}".format(pictureName)
            labels = picture["labels"]
            response.append({"Photo":{"url":url, "labels":labels}})
    searchResponse = {"SearchResponse":response}
   
    return searchResponse
    

def lambda_handler(event, context):
    #print('Received event: ' + json.dumps(event))
    
    # Initiate conversation with Lex
    response = client.recognize_text(
            botId='ASSCGMZQAZ', # MODIFY HERE
            botAliasId='UOX5QAUFIU', # MODIFY HERE
            localeId='en_US',
            sessionId='testuser',
            text=event["queryStringParameters"]["q"])
    
    msg_from_lex = response.get('messages', [])
    #print(response)
    
    objects = []
    
    firstObject = response["sessionState"]["intent"]["slots"]["firstObject"]["value"]["originalValue"]
    objects.append(inflection.singularize(firstObject).title())
    
    secondObject = ""
    
    if response["sessionState"]["intent"]["slots"]["secondObject"]:
        secondObject = response["sessionState"]["intent"]["slots"]["secondObject"]["value"]["originalValue"]
        objects.append(inflection.singularize(secondObject).title())
        
   
    if msg_from_lex:

        resp = {
            'statusCode': 200,
            'body': objects
        }
    
    openSearchResults = []
    
    for i in range(len(objects)):
       result = query(objects[i])
       openSearchResults.append(result)
       
    structuredResults = contructSearchResponse(openSearchResults)
       
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
            
        },
        'body': json.dumps(structuredResults)
    }

