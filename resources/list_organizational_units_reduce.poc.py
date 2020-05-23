
import boto3
import json
import sys

#https://github.com/aws-samples/aws-account-vending-machine/blob/master/resources/AccountCreationLambda.py#L32
def get_client(service):
  client = boto3.client(service)
  return client

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


list_roots_response = get_client('organizations').list_roots()
root_id = list_roots_response['Roots'][0]['Id']

ous = list_organizational_units(root_id)
print(json.dumps(ous, indent=2))
