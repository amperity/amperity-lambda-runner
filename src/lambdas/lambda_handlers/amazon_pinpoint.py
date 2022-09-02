import boto3
import json
import os
from datetime import datetime

from lambdas.amperity_runner import AmperityBotoRunner

PINPOINT_CLIENT = boto3.client("pinpoint", region_name="us-east-1")
PINPOINT_APP_ID = os.getenv("PINPOINT_APP_ID")  # Also known as Project ID
PINPOINT_ORIGINATION_NUMBER = os.getenv("PINPOINT_ORIGINATION_NUMBER")


class AmperityPinpointRunner(AmperityBotoRunner):

    def validate_phone_number(self, phone_number):
        """
        When you provide a phone number to the phone number validation service, you should always include the country code.
        If you don't include the country code, the service might return information for a phone number in a different country.
        https://docs.aws.amazon.com/pinpoint/latest/developerguide/validate-phone-numbers.html
        """
        try:
            validation = PINPOINT_CLIENT.phone_number_validate(NumberValidateRequest={"PhoneNumber": phone_number})
            response = validation["NumberValidateResponse"]
            phone_type = response["PhoneType"]
            print(response)
        except Exception as e:
            print("Couldn't validate phone number.", phone_number, e)
            return False
        else:
            return phone_type != "INVALID"

    def send_sms_message(self, destination_number, message, message_type):
        # https://docs.aws.amazon.com/code-samples/latest/catalog/python-pinpoint-pinpoint_send_sms_message_api.py.html
        try:
            response = PINPOINT_CLIENT.send_messages(
                ApplicationId=PINPOINT_APP_ID,
                MessageRequest={
                    "Addresses": {destination_number: {"ChannelType": "SMS"}},
                    "MessageConfiguration": {
                        "SMSMessage": {
                            "Body": message,
                            "MessageType": message_type,
                            "OriginationNumber": PINPOINT_ORIGINATION_NUMBER}}})
        except Exception as e:
            print("Couldn't send sms message", destination_number, e)
            return None
        else:
            return response["MessageResponse"]["Result"][destination_number]["MessageId"]

    def runner_logic(self, data):
        for item in data:
            phone_number = str(item["phone_number"])
            message = str(item["message"])
            if self.validate_phone_number(phone_number):
                message_id = self.send_sms_message(phone_number, message, message_type="PROMOTIONAL")
                if message_id:
                    print(f"Message '{message}' sent to {phone_number}! Message ID: {message_id}. {str(datetime.now())}")
                else:
                    self.errors.append(item)
            else:
                self.errors.append(f"Couldn't validate phone number {phone_number}")


def lambda_handler(event, context):
    payload = json.loads(event['body'])
    amperity_tenant_id = payload.get("tenant_id")

    pinpoint_runner = AmperityPinpointRunner(
        payload,
        context,
        amperity_tenant_id,
        boto_client=PINPOINT_CLIENT
    )

    status = pinpoint_runner.run()

    return status
