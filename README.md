## AWS Account Vending Machine

This repository contains various versions of the account vending machine used to provision AWS accounts with custom configurations.

### Note
For **AWS GovCloud(US) account vending**, click [here](/govcloud/README.md).
## Overview
As an organization expands its use of AWS services, there is often a conversation about the need to create multiple AWS accounts to ensure separation of business processes or for security, compliance, and billing. Many of the customers we work with use separate AWS accounts for each business unit so they can meet the different needs of their organization. Although creating multiple accounts has simplified operational issues and provided benefits like security and resource isolation, a smaller blast radius, and simplified billing, it takes a lot of time to create, bootstrap and configure baseline settings. Customers want to manage account creation and bootstrapping in a scalable and efficient manner so that new accounts are created with a defined baseline and some governance guardrails are in place. Most importantly, customers want automation, to save time and resources.

The account builder is an AWS Service Catalog product that uses AWS Lambda and AWS Organizations APIs to create AWS accounts. On each invocation, the AWS Lambda function used in this sample solution does the following:
1. Creates a new AWS account.
2.	If provided, creates an organization unit under the root account in AWS Organizations.
3.	Moves the newly created account from the organization root to the newly created organizational unit.
4.	Creates a service control policy and attaches it to the new account.
5.	Assumes the role OrganizationAccountAccessRole in the new account for the following:
	- Creating an IAM user with the provided password.
	- Adding the IAM user to a new group with least privilege permissions to access AWS Service Catalog.
	- Deploying baseline templates for creating AWS Service Catalog portfolio and products.
	- Deleting the default VPCs in all AWS Regions.
	- Creating AWS Service Catalog products and portfolio inside the newly created account.
	- Adding the provided IAM user and IAM role as principals to the created AWS Service Catalog portfolio.

This approach of bootstrapping accounts will reduce operational overhead and standardize account configurations across the provisioned AWS accounts. The following architecture outlines the process flow involved with account building :

![AVM-Architecture](/resources/images/avm-architecture-dark.png)

## Step by Step walkthrough

### A) Setup the account vending machine (AVM)
As a part of creating a sample account vending machine from this repository, you will first launch a CloudFormation template to create the account vending machine set up in your account.
1. Login to your AWS account which is a **master account** in AWS Organizations. Select one the following 4 regions from the top right corner on the AWS Management Console:
    - Ohio (us-east-2)
    - Oregon (us-west-2)
    - Ireland (eu-west-1)
    - Singapore (ap-southeast-1)
_Note: You can customize this implementation to work with linked accounts as well, but for the purposes of this exercise, we will use the master account._
2. Click on the `Launch Stack` image below this sentence to launch a Cloudformation template that will setup the required infrastructure for account vending machine in your AWS account.
[![Launch Stack](/resources/images/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-avm-infrastructure-setup&templateURL=https://mpsa-reinvent19-us-east-2.s3.us-east-2.amazonaws.com/AccountCreationLambdaSetup-cfn.yaml)
3. On the `Create Stack` page, click `Next`.
4. On the `Specify stack details` page, enter the following parameters:
	- `AccountAdministrator` - Enter the ARN of the IAM entity (role or user or group) that will be performing account creation from AWS Service Catalog. You can go to the IAM console to find the ARN of the role/user/group. (eg. arn:aws:iam::010010011111:role/Administrator)
	- `SourceBucket` - Keep the default value for the S3 bucket. _Note_: To use your own S3 bucket, you can upload all the files in the /resources folder in Github to your own S3 bucket.
	- `SourceTemplate` - Keep the default value. _Note_: To launch your own CloudFormation template in the new account, make sure the template parameters have a default value, and replace the `Accountbaseline.yml` template we've provided for this demo. You will also have to edit the lambda function to reflect the parameters in your custom template.
5. On the `Configure stack options` page, click `Next`.
6. On the `Review` page, check the checkbox for `I acknowledge that AWS CloudFormation might create IAM resources.`, and click `Create Stack`.
7. Once status of the stack changes to `CREATE COMPLETE`, click on the stack and open the `Outputs` tab to see the output values.
8. In the the `Outputs` section of CloudFormation, copy the key and value column contents for `AccountLambda`. You will be using this value during the execution of the account vending machine.

At this point, you have successfully set up the account vending machine in your account.

### B) Launch the AVM to create a new AWS account
In this section, you will launch the account vending machine product created in AWS Service Catalog to create a new AWS account pre-configured with custom settings defined in this lab.
1. Login to your AWS account using the IAM role/user/group that you provided in the `AccountAdministrator` in the set up phase.
2.  On the Services menu, search and then choose `Service Catalog`. You will see an AWS Service Catalog product named `Account Vending Machine`.
![product-list](/resources/images/product-list.png)
3. In the `Products list` page, click `Account Vending Machine`, and then click `LAUNCH PRODUCT`.
6. On the `Product Version` page, configure:
    a. `Name`: my-new-account-001
    b. Select the available version.
7. Click `NEXT`
8. On the `Parameters` page, configure:
    - `MasterLambdaArn`: **choose the value of 'AccountLambda' from the CloudFormation outputs noted in Lab Setup**
    - `AccountEmail`: Enter a unique email address to be associated with the newly created account
    - `OrganizationalUnitName`: Name of the organizational unit (OU) to which the account should be moved to. Keep the default value for placing the account at the root level.
	- `AccountName`: Enter an account name
	- `StackRegion`: Choose the region where the preconfigured settings should be applied
	- `SourceBucket`: Keep the default value. OR Enter the name of the source bucket where your baseline CloudFormation template exists.
	- `BaselineTemplate`: Keep the default value. OR Enter the name of the account baseline CloudFormation template.

9. Click `NEXT`.
10. On the `TagOptions` page, click `NEXT`.
11. On the Notifications page, click `NEXT`.
12. On the Review page, review the configuration information, and click `LAUNCH`. This will create a CloudFormation stack. The initial status of the product is shown as `Under change`. Wait for about 5 minutes, then refresh the screen till the status changes to `AVAILABLE`. _Note: You can go to the CloudFormation page to monitor the stack progress, or go to CloudWatch to view the step by step execution of the account vending lambda function._
13. In the the `Outputs` section of AWS Service Catalog, you will see the account details of the newly created account as follows.
![output](/resources/images/output.png)

### C) Login to the newly created AWS account for end-user experience
In this section, we will log in to the newly vended account using the user created as a part of the set up and explore the account configuration.
1. Login to your AWS account using the `LoginURL` provided in the Outputs of the previous section. **Make sure you are in the same region as the `StackRegion` in the previous section.**
2. On the credentials page, enter the following information:
	- Username: `service-catalog-user`
	- Password: `service-catalog-2019`
	_Note: You will be prompted to change your password at first log in._
3. On the Services menu, search and then choose `Service Catalog`. On the products list page, you will be to see the pre-configured AWS Service Catalog products allowed for the current user to provision.
![end-user](/resources/images/end-user.png)
4. As a part of the account setup, all the default VPCs from every region have been deleted for this account. You can validate this by going to the Services menu, search and then choose 'VPC'. 
![vpc](/resources/images/vpc.png)
5. As a security best practice of least privilege, we have restricted the current user to launch AWS Service Catalog products only. You can validate this by trying to create a new VPC from the [Amazon VPC console](https://console.aws.amazon.com/vpc/home).
	- Click on the `Launch VPC Wizard` button, and then click on `Select` for `VPC with a Single Public Subnet`.
	- In the `VPC Name` field, enter `demo`, and click `Create VPC`.
	- You will not be able to move forward from this page, due to lack of permissions.
	![vpc-error](/resources/images/vpc-error.png)
6. Now, we will try to perform the same function using AWS Service Catalog. But first, the user will need a key pair. 
	- Go to the [Amazon EC2 console](https://console.aws.amazon.com/ec2/v2/home)
	- In the left navigation menu, select `Key Pairs` under `Network & Security`
	- Click on the `Create a key pair` button, add name as `demo`, and click `Create`.
	- Now, on the Services menu, search and then choose `Service Catalog`. On the products list page, select `Amazon VPC`, and click on `Launch Product`.
	- On the `Product Version` page, configure:
    a. `Name`: `my-custom-vpc-001`
    b. Select the available version.
7. Click `NEXT`
8. On the `Parameters` page, configure:
    - `RegionAZ1Name`: Choose the availability zone for a region. eg. us-west-2a
    - `RegionAZ2Name`: Choose another availability zone for the **same** region as above. eg. us-west-2b
    - `VPCCIDR`: Keep the default value OR change it to a CIDR you want.
	- `SubnetAPublicCIDR`: Keep the default value OR change it to a CIDR you want
	- `SubnetAPublicCIDR`: Keep the default value OR change it to a CIDR you want
	- `SubnetAPrivateCIDR`: Keep the default value OR change it to a CIDR you want
	- `SubnetBPrivateCIDR`: Keep the default value OR change it to a CIDR you want
	- `CreateBastionInstance`: Keep the default value OR change it to `true` if you want a bastion instance created.
	- `BastionInstanceType`: Keep the default value OR change it to an instance type you want
	- `EC2KeyPair`: Choose the key pair you created in Step 6
	- `BastionSSHCIDR`: Enter any value you want eg. 0.0.0.0/0
	- `LatestAmiId`: Keep the default value OR change it to an AMI ID you want

9. Click `NEXT`.
10. On the `TagOptions` page, click `NEXT`.
11. On the Notifications page, click `NEXT`.
12. On the Review page, review the configuration information, and click `LAUNCH`. This will create a CloudFormation stack. The initial status of the product is shown as `Under change`. Wait for about 5 minutes, then refresh the screen till the status changes to `AVAILABLE`.
13. Validate the Outputs section on AWS Service Catalog screen to see the details of the VPC created. 
	![sc-vpc-output](/resources/images/sc-vpc-output.png)
14. Finally, on the [Amazon VPC console](https://console.aws.amazon.com/vpc/home), you can verify that a VPC is now created.
	![vpc-console-created](/resources/images/vpc-console-created.png)

In conclusion, you were able to log in as an end user in the newly vended AWS account, and create AWS resources in a compliant manner using AWS Service Catalog.

## Conclusion
This repository provides a method to enable on-demand creation of AWS accounts that can be customized to the requirements of an organization. Administrators and/or teams who are required to provision new accounts can use this approach to standardize the networking configuration and the resources that be provisioned when the new account is ready for use.

## Credits
This repository was inspired by the AWS blog post on [automation of AWS account creation](https://aws.amazon.com/blogs/mt/automate-account-creation-and-resource-provisioning-using-aws-service-catalog-aws-organizations-and-aws-lambda/).

## Clean Up
Congratulations! :tada: You have completed all the steps for setting up your own custom account vending machine using AWS Service Catalog. 

**To make sure you are not charged for any unwanted services, you can clean up by deleting the stack created in the _Deployment steps_ stage and its resources.**
To delete any AWS Service Catalog products, 
1. Go to the AWS Service Catalog screen and make sure you are in the same region as you selected during the launch phase
2. Go to the `Provisioned Products` screen, and terminate any products that you may have created as a part of the lab

To delete the stack and its resources
1. From the AWS CloudFormation console in the region you used in the _Lab Setup_, select the stack that you created.
2. Click `Delete Stack`.
3. In the confirmation message that appears, click `Yes`, `Delete`.

At this stage, the status for your changes to `DELETE_IN_PROGRESS`. In the same way you monitored the
creation of the stack, you can monitor its deletion by using the `Events` tab. When AWS CloudFormation completes the deletion of the stack, it removes the stack from the list.
[(Back to top)](#aws-account-vending-machine)

## Contributing
Your contributions are always welcome! Please have a look at the [contribution guidelines](CONTRIBUTING.md) first. :tada:

[(Back to top)](#aws-account-vending-machine)

## License Summary

This sample code is made available under the MIT-0 license. See the LICENSE file.

[(Back to top)](#aws-account-vending-machine)