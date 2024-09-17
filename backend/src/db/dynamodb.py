import os
import boto3

# Get DynamoDB table names from environment variables
USERS_TABLE = os.environ.get("USERS_TABLE")
DOMAINS_TABLE = os.environ.get("DOMAINS_TABLE")
DOMAIN_MEMBERSHIPS_TABLE = os.environ.get("DOMAIN_MEMBERSHIPS_TABLE")
INVITATIONS_TABLE = os.environ.get("INVITATIONS_TABLE")

dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Table(USERS_TABLE)
domains_table = dynamodb.Table(DOMAINS_TABLE)
memberships_table = dynamodb.Table(DOMAIN_MEMBERSHIPS_TABLE)
invitations_table = dynamodb.Table(INVITATIONS_TABLE)