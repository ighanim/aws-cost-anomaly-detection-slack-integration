import json
from slack_sdk.webhook import WebhookClient
import boto3
import base64
from botocore.exceptions import ClientError
import os


def get_secret():

    secret_name = os.environ['SLACK_WEBHOOK_URL']
    region_name = region = os.environ['AWS_REGION']

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])

class Field:
	def __init__(self,  type, text, emoji):
		#type: plain_text
		self.type = type
		#text: text to be displayed
		self.text = text
		#emoji: boolean
		self.emoji = emoji

class Block:
	#def __init__(self, type,  text=None, fields=None):
	def __init__(self, type, **kwargs):
		#type: section
		self.type = type
		#fields: an array of fields in the section
		if kwargs.get("fields"):
			self.fields = kwargs.get("fields")
		if kwargs.get("text"):
			self.text = kwargs.get("text")

class Text:
	#def __init__(self, type, text, emoji):
	def __init__(self, type, text, **kwargs):
		#type: plain_text
		self.type = type
		#text: text to be displayed
		self.text = text
		#emoji: boolean
		if kwargs.get("emoji"):
			self.emoji = kwargs.get("emoji")


def lambda_handler(event, context):

    print("testing a new lambda version -- xyz")
    
    url = json.loads(get_secret())["anomaly-detection-slack-webhook-url"]
    
    print("Slack Webhook URL retrieved")
    print("Initialise Slack Webhook Client")
    
    webhook = WebhookClient(url)
    
    print("Decoding the SNS Message")
    anomalyEvent = json.loads(event["Records"][0]["Sns"]["Message"])
    
    #Total Cost of the Anomaly
    totalcostImpact = anomalyEvent["impact"]["totalImpact"]

    #Anomaly Detection Interval
    anomalyStartDate =  anomalyEvent["anomalyStartDate"]
    anomalyEndDate = anomalyEvent["anomalyEndDate"]
    
    #anomalyDetailsLink
    anomalyDetailsLink = anomalyEvent["anomalyDetailsLink"]
   
    #Now, will start building the Slack Message. 
    #Blocks is the main array thagit git holds the full message.
    #Instantiate an Object of the Class Block
    blocks = []
    
    #MessageFormatting - Keep Appending the blocks object. Order is important here.
    #First, Populating the 'Text' Object that is a subset of the Block object. 
    headerText = Text("plain_text", ":warning: Cost Anomaly Detected ", emoji = True)
    totalAnomalyCostText = Text("mrkdwn", "*Total Anomaly Cost*: $" + str(totalcostImpact))
    rootCausesHeaderText = Text("mrkdwn", "*Root Causes* :mag:")
    anomalyStartDateText = Text("mrkdwn", "*Anomaly Start Date*: " + str(anomalyStartDate))
    anomalyEndDateText = Text("mrkdwn", "*Anomaly End Date*: " + str(anomalyEndDate))
    anomalyDetailsLinkText = Text("mrkdwn", "*Anomaly Details Link*: " + str(anomalyDetailsLink))
    

    #Second, Start appending the 'blocks' object with the header, totalAnomalyCost and rootCausesHeaderText
    blocks.append(Block("header", text=headerText.__dict__))
    blocks.append(Block("section", text=totalAnomalyCostText.__dict__))
    blocks.append(Block("section", text=anomalyStartDateText.__dict__))
    blocks.append(Block("section", text=anomalyEndDateText.__dict__))
    blocks.append(Block("section", text=anomalyDetailsLinkText.__dict__))
    blocks.append(Block("section", text=rootCausesHeaderText.__dict__))
    
    #Third, iterate through all possible root causes in the Anomaly Event and append the blocks as well as fields objects. 
    for rootCause in anomalyEvent["rootCauses"]:
    	fields = []
    	for rootCauseAttribute in rootCause:
    		fields.append(Field("plain_text", rootCauseAttribute  + " : " 
    		+ rootCause[rootCauseAttribute], False))
    	blocks.append(Block("section", fields = [ob.__dict__ for ob in fields]))
    	
    #print(json.dumps([ob.__dict__ for ob in blocks]))

    
    #print("The Block Format:" +json.dumps([ob.__dict__ for ob in blocks]))
    
    #Finally, send the message to the Slack Webhook. 
    response = webhook.send(
        text= anomalyEvent, 
    	blocks= json.dumps([ob.__dict__ for ob in blocks])

    	)
    
    #print(str(json.dumps(response.body)))
    assert response.status_code == 200
    assert response.body == "ok"
    
    
    return {
        'statusCode': 200,
        'responseMessage': 'Posted to Slack Channel Successfully'
    }
