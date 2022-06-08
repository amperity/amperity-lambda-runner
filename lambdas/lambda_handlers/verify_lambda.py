import json

import requests


def lambda_handler(event, context):
    """
    NOTE: This lambda is written for testing our internal workflow logic and tracking status outside the Amperity App.
    """
    payload = json.loads(event['body'])

    print(payload)

    resp = requests.get(payload.get('data_url'))

    print(resp.status_code)

    file_content = resp.content.decode('utf-8').splitlines()
    print(file_content[0])
    
    report_url = payload.get('callback_url') + payload.get('webhook_id')
    auth_str = f"Bearer {payload.get('access_token')}"
    
    resp = requests.put(
        report_url,
        headers={
            'Content-Type': 'application/json',
            'X-Amperity-Tenant': 'noodles',
            'Authorization': auth_str
        }, 
        data=json.dumps({
            "state": "succeeded",
            "progress": 1,
            "errors": ["no errors ever :)"]}))

    print(resp.status_code)
    print(resp.content)
    
    return { 'statusCode': 200 }
