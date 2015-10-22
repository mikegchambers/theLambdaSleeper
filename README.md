# theLambdaSleeper

Use AWS Lambda to start and stop EC2 instances to a schedule that is maintained in EC2 tags.

This script is Inspired by the work of monk-ee and [TheSleeper](https://github.com/monk-ee/TheSleeper "TheSleeper").

## Settings

For each EC2 instance that you want to stop and start, simply add a Tag called ‘timestartstop’ with a value of two cron strings.  Example:

    0 7 * * mon-fri | 0 18 * * mon-fri

The above tag will result in the server turning on at 7am UTC and off again at 6pm UTC.

For the moment options are set via class variables within the top of the class definition:

    awsregionname='ap-southeast-2' # REQUIRED, string, the AWS region that contains the target instances. 
    awsvpclist=["vpc-xxxxxxx"]    # REQUIRED, string list, the ids of the VPC(s) that contain the target instances.
    awsinstanceidlist=["i-xxxxxxx", "i-xxxxxxx", "i-xxxxxxx"] #OPTIONAL, string list (or None), a white-list of instance ids to target.
    snstopicarn='arn:aws:sns:ap-southeast-2:xxxxxxxxxxxxxx:theLambdaSleeper' #OPTINAL, string, the ARN of a SNS topic to message.

