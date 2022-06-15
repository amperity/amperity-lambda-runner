import json

def http_response(status_code, status, message):
    body = {
        "status": status,
        "message": message
    }

    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }