
#Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

#Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#http://aws.amazon.com/apache2.0/
#or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.


#!/usr/bin/env python

from __future__ import print_function
import boto3
import botocore
import time
import sys
import argparse
import os
import urllib
import json
from botocore.vendored import requests

'''AWS Organizations Create Account and Provision Resources via CloudFormation

This module creates a new account using Organizations, then calls CloudFormation to deploy baseline resources within that account via a local tempalte file.

'''

__version__ = '1.1'
__author__ = '@SYK@'
__email__ = 'khasnis@'

def get_client(service):
  client = boto3.client(service)
  return client

def create_account(accountname,accountemail,accountrole,access_to_billing,scp,root_id):
    account_id = 'None'
    client = get_client('organizations')
    try:
        create_account_response = client.create_account(Email=accountemail, AccountName=accountname,
                                                        RoleName=accountrole,
                                                        IamUserAccessToBilling=access_to_billing)
    except botocore.exceptions.ClientError as e:
        print(e)
        sys.exit(1)
    #time.sleep(30)
    create_account_status_response = client.describe_create_account_status(CreateAccountRequestId=create_account_response.get('CreateAccountStatus').get('Id'))
    account_id = create_account_status_response.get('CreateAccountStatus').get('AccountId')
    while(account_id is None ):
        create_account_status_response = client.describe_create_account_status(CreateAccountRequestId=create_account_response.get('CreateAccountStatus').get('Id'))
        account_id = create_account_status_response.get('CreateAccountStatus').get('AccountId')
    #move_response = client.move_account(AccountId=account_id,SourceParentId=root_id,DestinationParentId=organization_unit_id)
    return(create_account_response,account_id)

def get_template(sourcebucket,baselinetemplate):
    '''
        Read a template file and return the contents
    '''
    #print("Reading resources from " + templatefile)
    s3 = boto3.resource('s3')
    #obj = s3.Object('cf-to-create-lambda','5-newbaseline.yml')
    obj = s3.Object(sourcebucket,baselinetemplate)
    return obj.get()['Body'].read().decode('utf-8')

def delete_default_vpc(credentials,currentregion):
    #print("Default VPC deletion in progress in {}".format(currentregion))
    ec2_client = boto3.client('ec2',
                          aws_access_key_id=credentials['AccessKeyId'],
                          aws_secret_access_key=credentials['SecretAccessKey'],
                          aws_session_token=credentials['SessionToken'],
                          region_name=currentregion)

    vpc_response = ec2_client.describe_vpcs()
    for i in range(0,len(vpc_response['Vpcs'])):
        if((vpc_response['Vpcs'][i]['InstanceTenancy']) == 'default'):
            default_vpcid = vpc_response['Vpcs'][0]['VpcId']

    subnet_response = ec2_client.describe_subnets()
    subnet_delete_response = []
    default_subnets = []
    for i in range(0,len(subnet_response['Subnets'])):
        if(subnet_response['Subnets'][i]['VpcId'] == default_vpcid):
            default_subnets.append(subnet_response['Subnets'][i]['SubnetId'])
    for i in range(0,len(default_subnets)):
        subnet_delete_response.append(ec2_client.delete_subnet(SubnetId=default_subnets[i],DryRun=False))

    #print("Default Subnets" + currentregion + "Deleted.")

    igw_response = ec2_client.describe_internet_gateways()
    for i in range(0,len(igw_response['InternetGateways'])):
        for j in range(0,len(igw_response['InternetGateways'][i]['Attachments'])):
            if(igw_response['InternetGateways'][i]['Attachments'][j]['VpcId'] == default_vpcid):
                default_igw = igw_response['InternetGateways'][i]['InternetGatewayId']
    #print(default_igw)
    detach_default_igw_response = ec2_client.detach_internet_gateway(InternetGatewayId=default_igw,VpcId=default_vpcid,DryRun=False)
    delete_internet_gateway_response = ec2_client.delete_internet_gateway(InternetGatewayId=default_igw)

    #print("Default IGW " + currentregion + "Deleted.")

    time.sleep(10)
    delete_vpc_response = ec2_client.delete_vpc(VpcId=default_vpcid,DryRun=False)
    print("Deleted Default VPC in {}".format(currentregion))
    return delete_vpc_response

def deploy_resources(credentials, template, stackname, stackregion, ServiceCatalogUserName, ServiceCatalogUserPassword,account_id):

    '''
        Create a CloudFormation stack of resources within the new account
    '''

    datestamp = time.strftime("%d/%m/%Y")
    client = boto3.client('cloudformation',
                          aws_access_key_id=credentials['AccessKeyId'],
                          aws_secret_access_key=credentials['SecretAccessKey'],
                          aws_session_token=credentials['SessionToken'],
                          region_name=stackregion)
    print("Creating stack " + stackname + " in " + account_id)
    time.sleep(120)
    creating_stack = True
    while creating_stack is True:
        try:
            creating_stack = False
            create_stack_response = client.create_stack(
                StackName=stackname,
                TemplateBody=template,
                Parameters=[
                    {
                        'ParameterKey' : 'ServiceCatalogUserName',
                        'ParameterValue' : ServiceCatalogUserName
                    },
                    {
                        'ParameterKey' : 'ServiceCatalogUserPassword',
                        'ParameterValue' : ServiceCatalogUserPassword
                    }
                ],
                NotificationARNs=[],
                Capabilities=[
                    'CAPABILITY_NAMED_IAM',
                ],
                OnFailure='ROLLBACK',
                Tags=[
                    {
                        'Key': 'ManagedResource',
                        'Value': 'True'
                    },
                    {
                        'Key': 'DeployDate',
                        'Value': datestamp
                    }
                ]
            )
        except botocore.exceptions.ClientError as e:
            creating_stack = True
            print(e)
            print("Retrying...")
            time.sleep(10)

    stack_building = True
    print("Stack creation in process...")
    print(create_stack_response)
    while stack_building is True:
        event_list = client.describe_stack_events(StackName=stackname).get("StackEvents")
        stack_event = event_list[0]

        if (stack_event.get('ResourceType') == 'AWS::CloudFormation::Stack' and
           stack_event.get('ResourceStatus') == 'CREATE_COMPLETE'):
            stack_building = False
            print("Stack construction complete.")
        elif (stack_event.get('ResourceType') == 'AWS::CloudFormation::Stack' and
              stack_event.get('ResourceStatus') == 'ROLLBACK_COMPLETE'):
            stack_building = False
            print("Stack construction failed.")
            sys.exit(1)
        else:
            print(stack_event)
            print("Stack building . . .")
            time.sleep(10)
    stack = client.describe_stacks(StackName=stackname)
    return stack

def assume_role(account_id, account_role):
    sts_client = boto3.client('sts')
    role_arn = 'arn:aws:iam::' + account_id + ':role/' + account_role
    assuming_role = True
    while assuming_role is True:
        try:
            assuming_role = False
            assumedRoleObject = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="NewAccountRole"
            )
        except botocore.exceptions.ClientError as e:
            assuming_role = True
            print(e)
            print("Retrying...")
            time.sleep(10)

    # From the response that contains the assumed role, get the temporary
    # credentials that can be used to make subsequent API calls
    return assumedRoleObject['Credentials']

#list_organizational_units_for_parent handling NextToken
#https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/organizations.html#Organizations.Client.list_organizational_units_for_parent
def list_organizational_units(ParentId, NextToken=None, current={'OrganizationalUnits': []}):

    kwargs = {'NextToken': NextToken} if NextToken else {}

    try:
        page = get_client('organizations').list_organizational_units_for_parent(
            ParentId=ParentId,
            **kwargs
        )
        current.get('OrganizationalUnits').extend(page.get('OrganizationalUnits'))
    except:
        print(sys.exc_info())
        print('Error: something is wrong. Result may possibly be incomplete')
        return current

    if page.get('NextToken') is None:
        return current
    else:
        return list_organizational_units(ParentId, page.get('NextToken'), current)

def get_ou_name_id(event, root_id,organization_unit_name):

    ou_client = get_client('organizations')
    list_of_OU_ids = []
    list_of_OU_names = []
    ou_name_to_id = {}

    list_of_OUs_response = list_organizational_units(ParentId=root_id)

    for i in list_of_OUs_response['OrganizationalUnits']:
        list_of_OU_ids.append(i['Id'])
        list_of_OU_names.append(i['Name'])

    if(organization_unit_name not in list_of_OU_names):
        print("The provided Organization Unit Name doesnt exist. Creating an OU named: {}".format(organization_unit_name))
        try:
            ou_creation_response = ou_client.create_organizational_unit(ParentId=root_id,Name=organization_unit_name)
            for k,v in ou_creation_response.items():
                for k1,v1 in v.items():
                    if(k1 == 'Name'):
                        organization_unit_name = v1
                    if(k1 == 'Id'):
                        organization_unit_id = v1
        except botocore.exceptions.ClientError as e:
            print("Error in creating the OU: {}".format(e))
            respond_cloudformation(event, "FAILED", { "Message": "Could not list out AWS Organization OUs. Account creation Aborted."})

    else:
        for i in range(len(list_of_OU_names)):
            ou_name_to_id[list_of_OU_names[i]] = list_of_OU_ids[i]
        organization_unit_id = ou_name_to_id[organization_unit_name]

    return(organization_unit_name,organization_unit_id)

def respond_cloudformation(event, status, data=None):
    responseBody = {
        'Status': status,
        'Reason': 'See the details in CloudWatch Log Stream',
        'PhysicalResourceId': event['ServiceToken'],
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': data
    }

    print('Response = ' + json.dumps(responseBody))
    print(event)
    requests.put(event['ResponseURL'], data=json.dumps(responseBody))

def delete_respond_cloudformation(event, status, data=None):
    responseBody = {
        'Status': status,
        'Reason': 'See the details in CloudWatch Log Stream',
        'PhysicalResourceId': event['ServiceToken'],
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': data
    }

    print('Response = ' + json.dumps(responseBody))
    print(event)
    lambda_client = get_client('lambda')
    function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    print('Deleting Lambda')
    lambda_client.delete_function(FunctionName=function_name)
    requests.put(event['ResponseURL'], data=json.dumps(responseBody))

def main(event,context):
    print(event)
    client = get_client('organizations')
    ec2_client = get_client('ec2')
    accountname = event['ResourceProperties']['AccountName']
    accountemail = event['ResourceProperties']['AccountEmail']
    organization_unit_name = event['ResourceProperties']['OrganizationalUnitName']
    accountrole = 'OrganizationAccountAccessRole'
    stackname = event['ResourceProperties']['StackName']
    stackregion = event['ResourceProperties']['StackRegion']
    ServiceCatalogUserName = event['ResourceProperties']['ServiceCatalogUserName']
    ServiceCatalogUserPassword = event['ResourceProperties']['ServiceCatalogUserPassword']
    sourcebucket = event['ResourceProperties']['SourceBucket']
    baselinetemplate = event['ResourceProperties']['BaselineTemplate']
    access_to_billing = "DENY"
    scp = None

    if (event['RequestType'] == 'Create'):
        top_level_account = event['ServiceToken'].split(':')[4]
        print("The top level account is "+top_level_account)
        org_client = get_client('organizations')

        try:
            list_roots_response = org_client.list_roots()
            root_id = list_roots_response['Roots'][0]['Id']
        except:
            root_id = "Error"

        if root_id  is not "Error":
            try:
                #Create new account
                print("Creating new account: " + accountname + " (" + accountemail + ")")
                (create_account_response,account_id) = create_account(accountname,accountemail,accountrole,access_to_billing,scp,root_id)
                print(create_account_response)
                print("Created account:{}\n".format(account_id))
                time.sleep(20)
            except:
                print("Error creating new account..")
                sys.exit(0)

            #Create resources in the newly vended account
            try:
                #Move account to OU provided
                if(organization_unit_name!='None'):
                    try:
                        (organization_unit_name,organization_unit_id) = get_ou_name_id(event, root_id,organization_unit_name)
                        move_response = org_client.move_account(AccountId=account_id,SourceParentId=root_id,DestinationParentId=organization_unit_id)
                    except botocore.exceptions.ClientError as e:
                        print("An error occured. Org account move response: {} . Error Stack: {}".format(move_response, e))
                        sys.exit(0)
                credentials = assume_role(account_id, accountrole)
                template = get_template(sourcebucket,baselinetemplate)

                #deploy cloudformation template (AccountBaseline.yml)
                stack = deploy_resources(credentials, template, stackname, stackregion, ServiceCatalogUserName, ServiceCatalogUserPassword,account_id)
                print(stack)
                print("Baseline setup deployment for account " + account_id + " (" + accountemail + ") complete!")

                #delete default vpc in every region
                regions = []
                regions_response = ec2_client.describe_regions()
                for i in range(0,len(regions_response['Regions'])):
                    regions.append(regions_response['Regions'][i]['RegionName'])
                for r in regions:
                    try:
                        delete_vpc_response = delete_default_vpc(credentials,r)
                    except botocore.exceptions.ClientError as e:
                        print("An error occured while deleting Default VPC in {}. Error: {}".format(r,e))
                        i+=1
                respond_cloudformation(event, "SUCCESS", { "Message": "Account created successfully", "AccountID" : account_id, "LoginURL" : "https://" +account_id+".signin.aws.amazon.com/console", "Username" : ServiceCatalogUserName })
            except botocore.exceptions.ClientError as e:
                print("An error occured. Error Stack: {}".format(e))
                sys.exit(0)

    if(event['RequestType'] == 'Update'):
        print("Template in Update Status")
        respond_cloudformation(event, "SUCCESS", { "Message": "Resource update successful!" })

    elif(event['RequestType'] == 'Delete'):
        try:
            delete_respond_cloudformation(event, "SUCCESS", {"Message":"Delete Request Initiated. Deleting Lambda Function."})
        except:
            print("Couldnt initiate delete response.")
