# theLambdaSleeper

Use AWS Lambda to start and stop EC2 instances to a schedule that is maintained in EC2 tags.

This script is Inspired by the work of monk-ee and [TheSleeper](https://github.com/monk-ee/TheSleeper "TheSleeper").

## Settings

### EC2 Instance Tags

For each EC2 instance that you want to stop and start, simply add a Tag called ‘timestartstop’ with a value of two cron strings.  Example:

    0 7 * * mon-fri | 0 18 * * mon-fri

The above tag will result in the server turning on at 7am UTC and off again at 6pm UTC.

### Python Lambda Function

For the moment options are set via class variables within the top of the class definition:

	# name: awsRegionName 
	# REQUIRED
	# type: string
	# Comment: The AWS region that contains the target instances. 
	awsRegionName='ap-southeast-2' 
	
	# name: awsVpcList 
	# REQUIRED
	# type: string list
	# Comment: The ids of the VPC(s) that contain the target instances. 
	awsVpcList=["vpc-xxxxxxx"] 
	
	# name: awsInstanceIdList 
	# OPTIONAL
	# type: string list
	# Comment: A white-list of instance ids to target. 
	#awsInstanceIdList=["i-xxxxxxx", "i-xxxxxxx", "i-xxxxxxx"] 
	
	# name: snsTopicArn 
	# OPTIONAL
	# type: string
	# Comment: The ARN of a SNS topic to message.
	#snsTopicArn='arn:aws:sns:ap-southeast-2:xxxxxxxxxxxxxx:theLambdaSleeper'

### AWS Role

The Lambda function requires a role with access to the following actions with respect to the relative resources - in addition to the permissions required for Lambda itself: (work in progress)

- EC2: describe_instances, start_instances, stop_instances
- ELB: describe_load_balancers, deregister_instances_from_load_balancer, register_instances_with_load_balancer
- SNS: publish


## ELB Support

If an instance that is being started is found to be registered with an ELB, theLambdaSleeper will re-register the instance with that ELB to ensure that it has an opportunity to pass health checks.  This capability is automatic and requires no settings other than to give the Lambda function the necessary permissions.

In line with recommended solution [here](http://docs.aws.amazon.com/ElasticLoadBalancing/latest/DeveloperGuide/ts-elb-healthcheck.html).
