
import boto3
import json
import sys

def list_organizational_units_reduce(ParentId, NextToken=None, previous={'OrganizationalUnits': []}):

  kwargs = {'NextToken': NextToken} if NextToken else {}

  try:
    page = boto3.client('organizations').list_organizational_units_for_parent(
      ParentId=ParentId,
      **kwargs
    )
    previous.get('OrganizationalUnits').extend(page.get('OrganizationalUnits'))
  except:
    print(sys.exc_info())
    print('Error: something is wrong. Result may possibly be incomplete')
    return previous

  if page.get('NextToken') is None:
    return previous
  else:
    return list_organizational_units_reduce(ParentId, page['NextToken'], previous)

client = boto3.client('organizations')
list_roots_response = client.list_roots()
root_id = list_roots_response['Roots'][0]['Id']

ous = list_organizational_units_reduce(root_id)
print(json.dumps(ous, indent=2))
