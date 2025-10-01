import json
import boto3
import base64
import os
import urllib.request
import urllib.error
from botocore.exceptions import ClientError
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret():
    """Retrieve Slack webhook URL from AWS Secrets Manager"""
    secret_name = os.environ['SLACK_WEBHOOK_URL']
    region_name = os.environ['AWS_REGION']

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret

class Field:
    def __init__(self, type, text, emoji):
        self.type = type
        self.text = text
        self.emoji = emoji

class Block:
    def __init__(self, type, **kwargs):
        self.type = type
        if kwargs.get("fields"):
            self.fields = kwargs.get("fields")
        if kwargs.get("text"):
            self.text = kwargs.get("text")

class Text:
    def __init__(self, type, text, **kwargs):
        self.type = type
        self.text = text
        if kwargs.get("emoji"):
            self.emoji = kwargs.get("emoji")

def get_aws_account_name(account_id):
    """Function to fetch account name corresponding to an account number"""
    logger.info(f"Fetching Account Name for accountId: {account_id}")

    try:
        client = boto3.client('organizations')
        response = client.describe_account(AccountId=account_id)
        account_name = response["Account"]["Name"]
        logger.info(f"Account Name retrieved: {account_name}")
        return account_name
    except ClientError as e:
        logger.error(f"Error fetching account name for {account_id}: {e}")
        return f"Account-{account_id}"  # Fallback to account ID

def get_application_features():
    """Retrieve feature flags from AppConfig"""
    url = 'http://localhost:2772/applications/cost-anomaly-to-slack-application/environments/cost-anomaly-to-slack-environment/configurations/cost-anomaly-to-slack-configuration-profile'
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            config = response.read()
        return config
    except urllib.error.URLError as e:
        logger.error(f"Error retrieving AppConfig: {e}")
        # Return default configuration if AppConfig fails
        return b'{"feature-flags": {"displayAccountName": false}}'

def send_slack_message(webhook_url, blocks):
    """Send message to Slack using webhook"""
    try:
        import urllib.request
        import urllib.parse
        
        payload = {
            'blocks': json.dumps([ob.__dict__ for ob in blocks])
        }
        
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode('utf-8')
            
        if response.status == 200 and response_body == "ok":
            logger.info("Successfully sent message to Slack")
            return True
        else:
            logger.error(f"Slack API error: Status {response.status}, Body: {response_body}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending to Slack: {e}")
        return False

def lambda_handler(event, context):
    """Main Lambda handler function"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Retrieve Slack URL from Secrets Manager
        logger.info("Retrieving Slack URL from Secrets Manager")
        slack_url = json.loads(get_secret())["anomaly-detection-slack-webhook-url"]
        logger.info("Slack Webhook URL retrieved successfully")
        
        # Decode the SNS Message
        logger.info("Decoding SNS Message")
        anomaly_event = json.loads(event["Records"][0]["Sns"]["Message"])
        
        # Extract anomaly details
        total_cost_impact = anomaly_event["impact"]["totalImpact"]
        anomaly_start_date = anomaly_event["anomalyStartDate"]
        anomaly_end_date = anomaly_event["anomalyEndDate"]
        anomaly_details_link = anomaly_event["anomalyDetailsLink"]
       
        # Build Slack message blocks
        blocks = []
        
        # Header and basic information
        header_text = Text("plain_text", ":warning: Cost Anomaly Detected ", emoji=True)
        total_anomaly_cost_text = Text("mrkdwn", f"*Total Anomaly Cost*: ${total_cost_impact}")
        anomaly_start_date_text = Text("mrkdwn", f"*Anomaly Start Date*: {anomaly_start_date}")
        anomaly_end_date_text = Text("mrkdwn", f"*Anomaly End Date*: {anomaly_end_date}")
        anomaly_details_link_text = Text("mrkdwn", f"*Anomaly Details Link*: {anomaly_details_link}")
        root_causes_header_text = Text("mrkdwn", "*Root Causes* :mag:")
        
        # Add blocks
        blocks.append(Block("header", text=header_text.__dict__))
        blocks.append(Block("section", text=total_anomaly_cost_text.__dict__))
        blocks.append(Block("section", text=anomaly_start_date_text.__dict__))
        blocks.append(Block("section", text=anomaly_end_date_text.__dict__))
        blocks.append(Block("section", text=anomaly_details_link_text.__dict__))
        blocks.append(Block("section", text=root_causes_header_text.__dict__))
        
        # Load feature flags
        try:
            feature_list = get_application_features()
            feature_flag_display_account_name = json.loads(feature_list)["feature-flags"]["displayAccountName"]
            logger.info(f"Display account name feature flag: {feature_flag_display_account_name}")
        except Exception as e:
            logger.warning(f"Error loading feature flags, using default: {e}")
            feature_flag_display_account_name = False
        
        # Process root causes
        for root_cause in anomaly_event["rootCauses"]:
            fields = []
            for root_cause_attribute in root_cause:
                if feature_flag_display_account_name and root_cause_attribute == "linkedAccount":
                    account_name = get_aws_account_name(root_cause[root_cause_attribute])
                    fields.append(Field("plain_text", f"accountName: {account_name}", False))
                fields.append(Field("plain_text", f"{root_cause_attribute}: {root_cause[root_cause_attribute]}", False))
            blocks.append(Block("section", fields=[ob.__dict__ for ob in fields]))
        
        # Send message to Slack
        success = send_slack_message(slack_url, blocks)
        
        if success:
            return {
                'statusCode': 200,
                'responseMessage': 'Posted to Slack Channel Successfully'
            }
        else:
            return {
                'statusCode': 500,
                'responseMessage': 'Failed to post to Slack Channel'
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'responseMessage': f'Error processing anomaly event: {str(e)}'
        }
