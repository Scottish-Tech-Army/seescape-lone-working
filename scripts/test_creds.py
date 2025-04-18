# This script just checks that the client can access what it needs to access.
# If it errors out, you know you have a problem - conversely it should ONLY
# work on the shared mailbox.
import requests
import os
from urllib.parse import quote
import json
import jwt

# Get some credentials
def get_token(client_id, client_secret, tenant_id, scope):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': scope
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def get_calendar(user):
    encoded_user = quote(user)
    url = f"https://graph.microsoft.com/v1.0/users/{encoded_user}/calendar"
    print(url)
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_calendar_events(user):
    encoded_user = quote(user)
    url = f"https://graph.microsoft.com/v1.0/users/{encoded_user}/calendar/events"
    print(url)
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_contacts(user, number):
    # number must be E164
    encoded_user = quote(user)
    url = f"https://graph.microsoft.com/v1.0/users/{encoded_user}/contacts"

    clauses = [f"mobilePhone eq '{number}'"]

    prefix = "+44"
    if number.startswith(prefix):
        alt_number = "0" + number[len(prefix):]
        clauses.append(f"mobilePhone eq '{alt_number}'")
    filter = " or ".join(clauses)

    params = {
        '$filter': filter
    }

    print(url)
    print("Params:", params)
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_users(user, number):
    # number must be E164
    # Nonsense with the count and consistency stuff is a quirk of the graph API
    url = "https://graph.microsoft.com/v1.0/users"
    filter = f"mobilePhone eq '{number}'"

    clauses = [f"mobilePhone eq '{number}'"]

    prefix = "+44"
    if number.startswith(prefix):
        alt_number = "0" + number[len(prefix):]
        clauses.append(f"mobilePhone eq '{alt_number}'")
    filter = " or ".join(clauses)

    params = {
        '$filter': filter,
        '$count': 'true'
    }
    print(url)
    print("Params:", params)

    headers_with_consistency = HEADERS.copy()
    headers_with_consistency['ConsistencyLevel'] = 'eventual'

    response = requests.get(url, headers=headers_with_consistency, params=params)
    response.raise_for_status()
    return response.json()

# Do things
client_id = os.getenv('CLIENT_ID')
if client_id is None:
    raise EnvironmentError("CLIENT_ID environment variable not set")
client_secret = os.getenv('CLIENT_SECRET')
if client_secret is None:
    raise EnvironmentError("CLIENT_SECRET environment variable not set")
tenant_id = os.getenv('TENANT_ID')
if tenant_id is None:
    raise EnvironmentError("TENANT_ID environment variable not set")
user  = os.getenv('USERNAME')
if user is None:
    raise EnvironmentError("USERNAME environment variable not set")

scope = 'https://graph.microsoft.com/.default' # Must use this for client credentials

print("Get token")
token_response = get_token(client_id, client_secret, tenant_id, scope)
print(json.dumps(token_response, indent=4))
token = token_response["access_token"]

# Decode without verifying the signature by setting options accordingly
decoded = jwt.decode(token, options={"verify_signature": False})

print("Decoded JWT:")
print(json.dumps(decoded, indent=4))

roles = [role.lower() for role in decoded["roles"]]  # Convert roles to lowercase for case-insensitive comparison
missing_role = False
for permission in ["Calendars.ReadWrite", "User.Read.All", "Mail.Send", "Contacts.Read"]:
    if not permission.lower() in roles:
        print(f"Permission missing from roles: {permission}")
        missing_role = True

HEADERS = {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json',
    'Prefer': 'outlook.timezone="Etc/GMT"'
}

print("Get calendar")
calendar_response = get_calendar(user)
print(json.dumps(calendar_response, indent=4))

print("Get events")
calendar_events = get_calendar_events(user)
print(json.dumps(calendar_events, indent=4))

print("Get contacts")
number = "+447123123456"
contacts = get_contacts(user, number)
print(json.dumps(contacts, indent=4))

print("Get users")
number = "+4471231231234"
users = get_users(user, number)
print(json.dumps(users, indent=4))

# We plough on even if there is a missing role, but want to make the user notice.
if missing_role:
    raise RuntimeError("At least one role missing - see above")
