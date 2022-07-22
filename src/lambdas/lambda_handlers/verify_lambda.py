import json

import requests


def lambda_handler(event, context):
    """
    NOTE: This lambda is written for testing our internal workflow logic and tracking status outside the Amperity App.

    curl -X PUT 'https://app.amperity.com/webhook/v1/{{ webhook-id }}' \
        -H 'X-Amperity-Tenant: {{ tenant-id }}' \
        -H 'Authorization: Bearer {{ access-token }}' \
        -H 'Content-Type: application/json' -d '{"state": "succeeded", "progress": 1, "errors": ["no errors :)"]}}'
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
            "errors": ["no errors :)"]
        })
    )

    print(resp.status_code)
    print(resp.content)

    return {'statusCode': 200}
