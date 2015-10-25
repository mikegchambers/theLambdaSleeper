#!/usr/bin/env python

import boto3
from croniter import croniter
from datetime import datetime

class thelambdasleeper:

	# Setting vars:

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

	# Vars used by the class:

	ec2Client = ""
	elbClient = ""
	elbMembers = {}	
	describe_instances = ""
	message = ""

	def __init__(self):
		print ('INFO: theLambdaSleeper has started')
		
		# Load the AWS clients
		self.loadEc2Client()
		self.loadElbClient()

		# Get details of the instances
		self.loadInstanceData()
		self.loadInstanceElbMembership()
		
		# Main loop through instances
		self.iterateInstances()

		# Send SNS notification
		print ('INFO: The message: {}'.format(self.message))
		self.sendNotification()
		
		print ('INFO: theLambdaSleeper has completed')
						
	def loadEc2Client(self):
		try:
			self.ec2Client = boto3.client('ec2',  region_name=self.awsRegionName)
		except:
			exit("ERROR: Failed to connect to EC2 (boto3 ec2 client)")
		
	def loadElbClient(self):
		try:
			self.elbClient = boto3.client('elb',  region_name=self.awsRegionName)
		except:
			exit("ERROR: Failed to connect to ELB (boto3 elb client)")
		
	def loadInstanceElbMembership(self):
		try:
			describe_load_balancers = self.elbClient.describe_load_balancers()
			for elb in describe_load_balancers['LoadBalancerDescriptions']:
				for i in elb['Instances']:
					self.elbMembers[ i['InstanceId'] ] = elb['LoadBalancerName']
		except:
			print('ERROR: Failed to get ELB membership details. (describe_load_balancers)' )
		
	def loadInstanceData(self):
		try:
			try:
				self.awsInstanceIdList
			except:
				self.describe_instances = self.ec2Client.describe_instances(Filters=[{"Name": "vpc-id", "Values": self.awsVpcList}])
			else:
				self.describe_instances = self.ec2Client.describe_instances(Filters=[{"Name": "vpc-id", "Values": self.awsVpcList}, {"Name": "instance-id", "Values": self.awsInstanceIdList}])
		except:
			exit("ERROR: Failed to get EC2 instance data. (describe_instances)")
		
	def iterateInstances(self):

		for reservation in self.describe_instances['Reservations']:
			for instance in reservation['Instances']:

				instanceDetails = self.getDetailsForInstance( instance )
				print ( 'INFO: Found instance details: {}'.format(instanceDetails))
				
				if instanceDetails['timestartstop']:
					
					targetState = self.gettargetStateFromTag(instanceDetails['timestartstop'])
					
					if targetState:
						print ( 'INFO: Target state of instance {} is {}'.format(instanceDetails['id'], targetState))
						
						if targetState != instanceDetails['state']:
							# The instance is not in the state that it should be:

							if instanceDetails['state'] != 'running':
								# The instance should be running:								
								self.message = self.message + "Starting instance ({}) {} \n".format(instanceDetails['id'], instanceDetails['name'])
								self.startInstance( instanceDetails['id'] )
								
								try:
									# If the instance is a member of an ELB, re-register it with that ELB.
									
									# Why?   :

									# Problem:  The instances launched in a VPC have been stopped and then started. 
									#           The load balancer is not able to connect to the restarted instance.
									# Cause:    When you stop and then start your VPC instance, it might take some 
									#		    time for the load balancer to recognize that the instance has restarted. 
									#           During this time, the load balancer is not connected with the restarted instance.
									# Solution: Re-register the instance with the load balancer after the restart. For 
									#           more information, see De-register and Register EC2 Instances with Your 
									#           Load Balancer.
									# Source:   http://docs.aws.amazon.com/ElasticLoadBalancing/latest/DeveloperGuide/ts-elb-healthcheck.html

									if self.elbMembers[instanceDetails['id']]:
										print ('INFO: This instance ({}) is a member of the elb: {}'.format( instanceDetails['id'], self.elbMembers[instanceDetails['id']] ))
										self.message = self.message + "Instance {} ({}) is registered with ELB {} and has been reregistered \n".format(instanceDetails['id'], instanceDetails['name'], self.elbMembers[instanceDetails['id']])
										self.reRegisterInstanceWithElb( self.elbMembers[instanceDetails['id']], instanceDetails['id'] )
								except:
									pass
							else:
								# The instance should be stopped:
								self.message = self.message + "Stopping instance ({}) {} \n".format(instanceDetails['id'], instanceDetails['name'])
								self.stopInstance( instanceDetails['id'] )
					else:
						print ( 'WARNING: Unable to READ timestartstop tag for instance {}'.format(instanceDetails['id']))
				else:
					print ( 'WARNING: Unable to FIND timestartstop tag for instance {}'.format(instanceDetails['id']) )
	
	def getDetailsForInstance(self, instancedata):
		try:
			instanceId = instancedata['InstanceId']
			instanceStateName = instancedata['State']['Name']
		except:
			print ('ERROR: An unexpected error occured.  Failed to get basic instace details.')
			return

		instanceStartStopTag = self.getValueForTag( 'timestartstop', instancedata )
		instanceName = self.getValueForTag( 'Name', instancedata )

		return {'id':instanceId, 'state':instanceStateName, 'timestartstop':instanceStartStopTag, 'name':instanceName}
		
	def getValueForTag(self, tag, instancedata):
		try:
			for tags in instancedata['Tags']:
				if tags['Key'] == tag:
					return tags['Value']
			return False
		except:
			print ('ERROR: An unexpected error occured when trying to get the "{}" tag.'.format(tag))
			return False
	
	
	def startInstance(self, instanceid):
		print('INFO: Request to start {}'.format(instanceid))
		try:
			start_instances = self.ec2Client.start_instances(InstanceIds=[instanceid])
			print(start_instances)
		except:
			print('ERROR: There was an error trying to start instance {}'.format(instanceid) )
	
	def stopInstance(self, instanceid):
		print('INFO: Request to stop {}'.format(instanceid))
		try:
			stop_instances = self.ec2Client.stop_instances(InstanceIds=[instanceid])
			print(stop_instances)
		except:
			print('ERROR: There was an error trying to stop instance {}'.format(instanceid) )

	def reRegisterInstanceWithElb(self, elbname, instanceid):
		print('INFO: DEregistering instance from ELB')
		try:
			deregister_instances_from_load_balancer = self.elbClient.deregister_instances_from_load_balancer( LoadBalancerName=elbname,Instances=[{'InstanceId': instanceid}])
			print(deregister_instances_from_load_balancer)
		except:
			print('ERROR: There was an error trying to deregister instance {} from elb {}'.format(instanceid, elbname) )

		print('INFO: Registering instance from ELB')
		try:
			register_instances_with_load_balancer = self.elbClient.register_instances_with_load_balancer( LoadBalancerName=elbname,Instances=[{'InstanceId': instanceid}])
			print(register_instances_with_load_balancer)
		except:
			print('ERROR: There was an error trying to register instance {} from elb {}'.format(instanceid, elbname) )


	def gettargetStateFromTag(self, startstoptag):
		
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

	def sendNotification(self):
		try:
			if self.message != '' and self.snsTopicArn:
				try:
					snsclient = boto3.client('sns',  region_name=self.awsRegionName)
					publish = snsclient.publish( TopicArn=self.snsTopicArn, Message=self.message, Subject='theLambdaSleeper - stop start notification')
					print ( publish )
				except:
					print('WARNING: Failed to publish SNS notification.')
		except:
			pass
			
def lambda_handler(event, context):
	tls = thelambdasleeper()
	
if __name__ == '__main__':
	tls = thelambdasleeper()

	
	