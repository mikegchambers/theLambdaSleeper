#!/usr/bin/env python

import boto3

from croniter import croniter
from datetime import datetime

class thelambdasleeper:

	awsregionname='ap-southeast-2' # REQUIRED, string, the AWS region that contains the target instances. 
	awsvpclist=["vpc-xxxxxxx"]    # REQUIRED, string list, the ids of the VPC(s) that contain the target instances.
	awsinstanceidlist=["i-xxxxxxx", "i-xxxxxxx", "i-xxxxxxx"] #OPTIONAL, string list (or None), a white-list of instance ids to target.
	snstopicarn='arn:aws:sns:ap-southeast-2:xxxxxxxxxxxxxx:theLambdaSleeper' #OPTINAL, string, the ARN of a SNS topic to message.

	ec2client = ""
	response = ""
	message = ""

	def __init__(self):
		print ('INFO: theLambdaSleeper has started')
		self.loadec2client()
		self.loadinstancedata()
		self.iterateinstances()
		print ('INFO: The message: {}'.format(self.message))
		self.sendnotification()
		print ('INFO: theLambdaSleeper has completed')
						
	def loadec2client(self):
		try:
			self.ec2client = boto3.client('ec2',  region_name=self.awsregionname)
		except:
			exit("ERROR: Failed to connect to EC2")
		
	def loadinstancedata(self):
		try:
			try:
				self.awsinstanceidlist
			except:
				self.response = self.ec2client.describe_instances(Filters=[{"Name": "vpc-id", "Values": self.awsvpclist}])
			else:
				self.response = self.ec2client.describe_instances(Filters=[{"Name": "vpc-id", "Values": self.awsvpclist}, {"Name": "instance-id", "Values": self.awsinstanceidlist}])
		except:
			exit("ERROR: Failed to get EC2 instance data. (describe_instances)")
		
	def iterateinstances(self):
		for reservation in self.response['Reservations']:
			for instance in reservation['Instances']:
			
				instancedetails = self.getdetailsforinstance( instance )
				print ( 'INFO: Found instance details: {}'.format(instancedetails))
				
				if instancedetails['timestartstop']:
					
					targetstatus = self.gettargetstatusfromtag(instancedetails['timestartstop'])
					
					if targetstatus:
						print ( 'INFO: Target status of instance {} is {}'.format(instancedetails['id'], targetstatus))
						
						if targetstatus != instancedetails['status']:
							if instancedetails['status'] != 'running':
								self.message = self.message + "Starting instance ({}) {} \n".format(instancedetails['id'], instancedetails['name'])
								self.startinstance( instancedetails['id'] )
							else:
								self.message = self.message + "Stopping instance ({}) {} \n".format(instancedetails['id'], instancedetails['name'])
								self.stopinstance( instancedetails['id'] )
					else:
						print ( 'WARNING: Unable to READ timestartstop tag for instance {}'.format(instancedetails['id']))
				else:
					print ( 'WARNING: Unable to FIND timestartstop tag for instance {}'.format(instancedetails['id']) )
	
	def getdetailsforinstance(self, instancedata):
		try:
			instanceid = instancedata['InstanceId']
			instancestatename = instancedata['State']['Name']
		except:
			print ('ERROR: An unexpected error occured.  Failed to get basic instace details.')
			return

		instagestartstoptag = self.getvaluefortag( 'timestartstop', instancedata )
		instancename = self.getvaluefortag( 'Name', instancedata )

		return {'id':instanceid, 'status':instancestatename, 'timestartstop':instagestartstoptag, 'name':instancename}
		
	def getvaluefortag(self, tag, instancedata):
		try:
			for tags in instancedata['Tags']:
				if tags['Key'] == tag:
					return tags['Value']
		except:
			print ('An unexpected error occured when trying to get the "{}" tag.'.format(tag))
			return False
	
	
	def startinstance(self, instanceid):
		print('INFO: Request to start {}'.format(instanceid))
		response = self.ec2client.start_instances(InstanceIds=[instanceid])
		print(response)
		
	
	def stopinstance(self, instanceid):
		print('INFO: Request to stop {}'.format(instanceid))
		response = self.ec2client.stop_instances(InstanceIds=[instanceid])
		print(response)
		
		
	def gettargetstatusfromtag(self, startstoptag):
		
		try:
			startStopTimesList = startstoptag.strip('"').split("|")
			startTimeString = startStopTimesList[0]
			stopTimeString = startStopTimesList[1]
		except:
			return False
		
		try:
			startIter = croniter( startTimeString )				
			stopIter = croniter( stopTimeString )
			nowTime = datetime.utcnow()
			prevStartTime = startIter.get_prev()
			prevStopTime = stopIter.get_prev()
		except:
			return False
			
		if prevStartTime > prevStopTime:
			return 'running'
		else:
			return 'stopped'

	def sendnotification(self):
		if self.message != '' and self.snstopicarn:
			try:
				snsclient = boto3.client('sns',  region_name=self.awsregionname)
				snsclient.publish( TopicArn=self.snstopicarn, Message=self.message, Subject='theLambdaSleeper - stop start notification')
			except:
				print('WARNING: Failed to publish SNS notification.')
			
def lambda_handler(event, context):
	tls = thelambdasleeper()
	
if __name__ == '__main__':
	tls = thelambdasleeper()

	
	