#!/usr/bin/env python

import boto3

from croniter import croniter
from datetime import datetime

class thelambdasleeper:

	awsregionname='ap-southeast-2'
	awsvpclist=["vpc-xxxxxxxx"]

	client = ""
	response = ""
	
	def __init__(self):
		print ('theLambdaSleeper has started')
		self.loadclient()
		self.loadinstancedata()
		self.iterateinstances()
		print ('theLambdaSleeper has completed')
						
	def loadclient(self):
		self.client = boto3.client('ec2',  region_name=self.awsregionname)
		
	def loadinstancedata(self):
		self.response = self.client.describe_instances(Filters=[{"Name": "vpc-id", "Values": self.awsvpclist}])
						
	def iterateinstances(self):
		for reservation in self.response['Reservations']:
			for instance in reservation['Instances']:
				instancedetails = self.getdetailsforinstance( instance )
				if instancedetails:
					print ('Found instance details: {}'.format(instancedetails))
					targetstatus = self.gettargetstatusfromtag(instancedetails[2])
					print ('Target status of instance: {}'.format(targetstatus))
					if targetstatus != instancedetails[1]:
						if instancedetails[1] != 'running':
							self.startinstance( instancedetails[0] )
						else:
							self.stopinstance( instancedetails[0] )
				else:
					print ( 'Error trying to read instance data, is the startstoptag set?' )
	
	def getdetailsforinstance(self, instancedata):
		try:
			instanceid = instancedata['InstanceId']
			instancestatename = instancedata['State']['Name']
			for tags in instancedata['Tags']:
				if tags['Key'] == 'timestartstop':
					instagestartstoptag = tags['Value']
			return instanceid, instancestatename, instagestartstoptag
		except:
			pass
	
	def startinstance(self, instanceid):
		print('Request to start {}'.format(instanceid))
		self.client.start_instances(InstanceIds=[instanceid])
	
	def stopinstance(self, instanceid):
		print('Request to stop {}'.format(instanceid))
		self.client.stop_instances(InstanceIds=[instanceid])
	
	def gettargetstatusfromtag(self, startstoptag):
		
		startStopTimesList = startstoptag.strip('"').split("|")
		startTimeString = startStopTimesList[0]
		stopTimeString = startStopTimesList[1]
		
		startIter = croniter( startTimeString )				
		stopIter = croniter( stopTimeString )

		nowTime = datetime.utcnow()

		prevStartTime = startIter.get_prev()
		prevStopTime = stopIter.get_prev()

		if prevStartTime > prevStopTime:
			return 'running'
		else:
			return 'stopped'
	
def lambda_handler(event, context):
	ts = thelambdasleeper()
	
thelambdasleeper()
	
	
	
	