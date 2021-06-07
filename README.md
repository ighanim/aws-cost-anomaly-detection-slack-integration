# AWS Cost Anomaly Detection Slack Integration
The project is a plug and play solution to detect cost anomalies in your AWS accounts relying on the [AWS Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/) feature in Cost Explorer and push to a Slack channel. 

### Solution Overview

![alt text](https://github.com/ighanim/aws-cost-anomaly-detection-slack-integration/blob/main/images/architecture-diagram.png)


### Create a Slack Webhook URL

First, create a Slack Webhook URL linked to one of your Slack channels. Follow the steps in the Slack public [documentation](https://api.slack.com/messaging/webhooks). Here is a a sample of the Slack notification:

![alt text](https://github.com/ighanim/aws-cost-anomaly-detection-slack-integration/blob/main/images/slack-notification-sample.png)

### Create Artifact store

Second, create an S3 bucket to store your build artifacts -- Lambda code and CloudFormation template. For more information, see [create bucket](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html). Create the bucket in the same region as the CloudFormation deployment.  

### Build

Third, build/package the Lambda function Python code using `zip`. For more information on the process; see [Python package](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html). On your local machine or build server, run the following command. It is important to change the Lambda package version with each and everybuild so that CloudFormation can detect the change and update the Lambda function accordingly. 

`zip -r ./lambda-package-v1.0.0.zip lambda-code/lambda_function.py lambda-code/slack-sdk`

Now, upload the Lambda package to the S3 bucket created in the first step. Use CLI, CloudFormation or API (as part of the build process) to upload the file. Here is a CLI sample command: 

`aws s3 cp ./lambda-package-v1.0.0.zip S3://newly-created-bucket`

### Deployment

Fourth, deploy the solution using AWS CloudFormation. As a start, upload the `deployment.yml` file into the S3 bucket created in the first step. Use CLI, CloudFormation or API (as part of the build process) to upload the file. Here is a CLI sample command: 

`aws s3 cp ./deployment.yml S3://newly-created-bucket`

> At the time being, deploy the solution in the payer account (aka Management Account). As a future enhancement, a new feature will allow the solution to deployed in any account.

In AWS CloudFormation, start deploying `deployment.yml`. For more information, see [create stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html). CloudFormation template is accepting multiple input parameters, following are the definitions:

Parameter | Description
--- | ---
`s3Bucket` | The name of the S3 bucket where project artifacts (Lambda package and `deployment.yml` are stored. The bucket has to be in the same region as the CloudFormation deployment
`codePackage` | The name of the Lambda code package (i.e.`lambda-package-v1.0.0.zip`)
`slackWebhookURL` | The Slack webhook URL

## Configure Cost Anomaly Detection

Finally, configure Cost Anomaly Detection in AWS Cost Explorer in your Payer/Management Account. To create a new cost anomaly monitor using AWS Management Console, follow the steps in the [public documentation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/getting-started-ad.html#create-ad-alerts). Customise the steps as follows:

Coniguration | Value
--- | ---
Monitor Type | AWS services
Subscription.Alerting Frequency | Individual Alerts
SNS Topic Arn | Copy the `snsTopicArn` output from the CloudFormation deployment.  

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.


