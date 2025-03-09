"""
Module containing common utility functions for the loneworker lambda functions.
"""
# General
import boto3
from collections import namedtuple
from datetime import datetime, timedelta
import logging
import os
import requests
from collections import defaultdict

# Our own modules.
import cfg_parser

logger = logging.getLogger(__name__)
# Do not make the log level DEBUG or it explodes
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def get_logger():
    return logger

# Some constants
# Start or end for time filters
START = "start"
END = "end"
BEFORE = "before"
AFTER = "after"

# Categories used - these are also logged in various places.
CHECKED_IN = "Checked-In"
CHECKED_OUT = "Checked-Out"
MISSED_CHECK_IN = "Missed-Check-In"
MISSED_CHECK_OUT = "Missed-Check-Out"
EMERGENCY = "Emergency"

class LoneWorkerManager:
    def __init__(self, app_type):
        """
        Init method just reads the configuration settings.
        """
        logger.info("Get configuration for app %s", app_type)
        self.read_config()

        logger.info("Initialise metrics structures")
        self.init_metrics(app_type)

        logger.info("Get auth token")
        self.get_token()

        # A couple of things it will be useful to work out in advance
        self.headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Prefer': 'outlook.timezone="Europe/London"'
        }
        self.calendar_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/calendar/events"
        self.mail_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/sendMail"
        self.contacts_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/contacts"
        self.users_url = f"https://graph.microsoft.com/v1.0/users"

    def read_config(self):
        """
        Read the configuration settings.
        """
        self.app_prefix  = os.environ['ssm_prefix']
        logger.info("Reading configuration from %s", self.app_prefix)

        # Read configuration from the environment
        ssm = boto3.client('ssm')
        self.app_prefix = os.environ['ssm_prefix']
        mand_names = ["clientid", "emailuser", "tenant", "config"]
        optional_names = ["clientsecret", "emailpass"]
        values = get_params(ssm, self.app_prefix, mand_names=mand_names, optional_names=optional_names)

        self.client_id = values["clientid"]
        self.client_secret = values["clientsecret"]
        self.username = values["emailuser"]
        self.password = values["emailpass"]
        self.tenant = values["tenant"]

        # Trace some things.
        logger.info("Tenant: %s, Client ID: %s, username: %s", self.tenant, self.client_id, self.username)

        if not self.password and not self.client_secret:
            logger.error("Both clientid and emailpass are missing or blank - that is not permitted")
            raise ValueError("Both clientid and emailpass are missing or blank - that is not permitted")

        if self.password:
            logger.info("Password defined - using ROPC flow")
        else:
            logger.info("Password not defined - using ROPC flow")

        # More config in the config blob.
        logger.info("Validate configuration")
        self.cfg = cfg_parser.LambdaConfig(data=values["config"])

    def get_token(self):
        """ Get Authentication Code token"""

        # Set the authentication endpoint and token endpoint
        auth_endpoint = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
        logger.info('Auth endpoint: %s', auth_endpoint)

        # Create the payload for the token request
        payload = {
            'client_id': self.client_id,
            'username': self.username
        }

        if self.password:
            logger.info("ROPC flow")
            payload['password'] = self.password
            payload['grant_type'] = 'password'
            scopes = ['https://graph.microsoft.com/Calendars.ReadWrite',
                      'https://graph.microsoft.com/Mail.Send',
                      'https://graph.microsoft.com/Contacts.Read' ]
            payload['scope'] = "%20".join(scopes)
        else:
            logger.info("Client credentials flow")
            payload['client_secret'] = self.client_secret
            payload['grant_type'] = 'client_credentials'
            payload['scope'] = 'https://graph.microsoft.com/.default'

        # Send the token request
        response = requests.post(auth_endpoint, data=payload)

        # Check if the request was successful
        if response.status_code != 200:
            logger.error('Authentication failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Authentication failed: {response.status_code}, message: {response.text}")

        # Get the access token from the response, and store it. We also build some useful headers here.
        access_token = response.json()['access_token']
        logger.info("Successful authentication")
        self.token = access_token

    def get_calendar_events(self, filter):
        """
        Get calendar events from the calendar.

        These are filtered based on supplied filter
        """
        logger.info("Reading calendar events with filter: %s", filter)
        params = {
            '$filter': filter
        }

        response = requests.get(self.calendar_url, headers=self.headers, params=params)

        if response.status_code != 200:
            logger.error('Calendar operation failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Calendar operation failed: {response.status_code}, message: {response.text}")

        # Get the appointments from the response
        appointments = response.json()['value']
        logger.info("Got %d appointments", len(appointments))
        return appointments

    def patch_calendar_event(self, event_id, changes):
        """
        Update a calender event.
        """
        logger.info("Updating calendar event %s", event_id)
        response = requests.patch(f"{self.calendar_url}/{event_id}", headers=self.headers, json=changes)

        if response.status_code != 200:
            logger.error('Calendar patch operation failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Calendar patch operation failed: {response.status_code}, message: {response.text}")

    def send_mail(self, subject, content):
        """
        Send an email
        """
        recipients = self.cfg.get_email_recipients()
        logger.info("Sending email to %s, subject: %s", recipients, subject)

        recip_array = []
        for recipient in recipients:
            recip_dict = { "emailAddress": { "address": recipient }}
            recip_array.append(recip_dict)

        message_payload = {
                            "message": {
                                "subject": subject,
                                "body": {
                                    "contentType": "Text",
                                    "content": content
                                },
                                "toRecipients": recip_array
                            }
                        }
        logger.info("Payload: %s", message_payload)

        response = requests.post(self.mail_url, headers=self.headers, json=message_payload)
        # The Microsoft Graph API sendMail method returns a 202 in most cases.
        if response.status_code != 200 and  response.status_code != 202:
            logger.error('Error sending mail: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Error sending mail: {response.status_code}, message: {response.text}")

    def phone_to_email(self, number):
        """
        Given a phone number, find all the users and contacts who have that phone number as their
        mobile number, and return an array of matching addresses.
        """
        logger.info("Looking for phone number %s", number)

        addresses = []
        display_name = "UNKNOWN"

        clauses = [f"mobilePhone eq '{number}'"]

        prefix = "+44"
        if number.startswith(prefix):
            alt_number = "0" + number[len(prefix):]
            logger.info("Also checking for number %s", alt_number)
            clauses.append(f"mobilePhone eq '{alt_number}'")
        filter = " or ".join(clauses)

        params = {
            '$filter': filter
        }

        logger.info("Finding contacts with number %s", number)
        response = requests.get(self.contacts_url, headers=self.headers, params=params)

        if response.status_code != 200:
            logger.error('Contacts request failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Contacts request failed: {response.status_code}, message: {response.text}")

        # Get the contacts from the response
        contacts = response.json()['value']
        logger.info("Got %d contacts", len(contacts))
        for contact in contacts:
            for emailaddr in contact['emailAddresses']:
                addresses.append(emailaddr['address'].lower())
                logger.info("Contact with phone %s has email address %s and name %s", number, addresses[-1], contact['displayName'])
            if contact['displayName']:
                display_name = contact['displayName']

        # Now the same for users; we need to add another parameter and another header.
        logger.info("Finding users with number %s", number)
        params['$count'] = 'true'
        headers_with_consistency = self.headers.copy()
        headers_with_consistency['ConsistencyLevel'] = 'eventual'

        response = requests.get(self.users_url, headers=headers_with_consistency, params=params)

        if response.status_code != 200:
            logger.error('User list request failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"User list request failed: {response.status_code}, message: {response.text}")

        # Get the users from the response
        users = response.json()['value']
        logger.info("Got %d users", len(users))
        for user in users:
            addresses.append(user['mail'].lower())
            logger.info("User with phone %s has email address %s and name %s", number, addresses[-1], user['displayName'])
            if user['displayName']:
                display_name = user['displayName']

        logger.info("Full list of returned matching addresses: %s", addresses)
        return addresses, display_name

    def init_metrics(self, app_type):
        # Set up metrics; we only do this when we need to actually report them
        self.cloudwatch = boto3.client('cloudwatch')
        self.metrics_namespace = f"{self.app_prefix}/{app_type}"

        # metrics is all the metrics reported; metrics_to_emit is all the metrics that have
        self.metrics = defaultdict(int)
        self.metrics_to_emit = defaultdict(int)

    def increment_counter(self, name, increment=1):
        """
        Increment the supplied metric name by that amount
        """
        self.metrics[name] += increment
        self.metrics_to_emit[name] += increment

    def emit_metrics(self):
        """
        Emit metrics that have already been stored.
        """
        logging.info("Emit metrics array: %s", self.metrics)
        # TODO: have a panic about timezones
        timestamp = datetime.now()
        if not self.metrics_to_emit:
            logging.info("No metrics in array - drop out")
            return

        metric_data = []
        for key, value in self.metrics_to_emit.items():
            metric_data.append({
                'MetricName': key,
                'Timestamp': timestamp,
                'Value': value,
                'Unit': 'Count'
            })

        logging.info("Putting %d metrics, %s", len(metric_data), metric_data)
        self.cloudwatch.put_metric_data(
            Namespace=self.metrics_namespace,
            MetricData=metric_data
        )

        # This is a pretty useless trace statement EXCEPT that it allows us to track the
        # time of the AWS call
        logging.info("Metrics emission complete")

        # Clear the supplied dict in case we call emit_metrics twice.
        self.metrics_to_emit.clear()

    def get_metrics(self):
        """
        Returns all metrics that have been reported, whether emitted or not.
        """
        return self.metrics

def get_params(ssm, prefix, mand_names, optional_names=[]):
    """
    Retrieves multiple parameters from AWS SSM Parameter Store using get_parameters_by_path.

    Args:
        ssm (boto3.client): The boto3 SSM client.
        prefix (str): The directory prefix (for example, "loneworker" to work with parameters like /loneworker/param).
        mand_names (list): A list of mandatory parameter names (without the prefix) to retrieve.
        optional_names (list): Another list of optional parameter names
    Returns:
        dict: A dictionary mapping each parameter name (without the prefix) to its value.
    Raises:
        ValueError: If a required parameter is not found.
    """
    # Ensure the prefix has a leading and trailing slash for consistency.
    path_prefix = "/" + prefix.strip("/") + "/"
    logger.debug("Retrieving parameters from path: %s", path_prefix)
    names = mand_names + optional_names

    # Use a paginator to handle potentially multiple pages of results.
    paginator = ssm.get_paginator("get_parameters_by_path")
    retrieved = {}

    for page in paginator.paginate(Path=path_prefix, Recursive=False, WithDecryption=True):
        for param in page.get("Parameters", []):
            full_name = param.get('Name')
            # Remove the prefix from the full parameter name to get the key.
            key = full_name[len(path_prefix):] if full_name.startswith(path_prefix) else full_name
            retrieved[key] = param.get('Value')

    # Build the results for only the requested names.
    results = {}
    for name in names:
        if name in retrieved:
            results[name] = retrieved[name]
        else:
            if name in mand_names:
                logger.error("Missing value for non-optional parameter %s%s", path_prefix, name)
                raise ValueError(f"Parameter {path_prefix}{name} not found")
            else:
                results[name] = None

    return results

TimeFilter = namedtuple('TimeFilter', ['minutes', 'before_or_after', 'start_or_end'])

def build_time_filter(time_filters):
    """
    Given an array of TimeFilters, build a string filter for Microsoft graph APIs that
    compares the timestamp in a meeting with provided data. Each value in time_filters is
    a separate clause, and they are all stuck together with "and" statements.

    For each time filter.
    - "minutes" is the number of minutes the test time should be after the current time (negative for past)
    - "before_or_after" checks whether the test should be for appointment times that are before or after that time
    - "start_or_end" tests whether it is the appointment start or end time that is being compared.

    """
    logger.info("Number of clauses in time filter: %d", len(time_filters))
    clauses = []
    current_time = datetime.now()

    # Get the current date
    # TODO: this will not cope with times that go past midnight.
    # TODO: I hope this copes cleanly with timezones; need to double check and test.
    today = datetime.now().strftime('%Y-%m-%d')

    for time_filter in time_filters:
        if time_filter.before_or_after not in [BEFORE, AFTER]:
            raise ValueError("Time direction must be either '{BEFORE}' or '{AFTER}' - provide value '{time_filter.before_or_after}'")
        if time_filter.start_or_end not in [START, END]:
            raise ValueError(f"Start or end must be either '{START}' or '{END}' - provide value '{time_filter.start_or_end}'")

        logger.info("Building a filter on %s time, checking that it is %s a time %d minutes from now",
                    time_filter.start_or_end, time_filter.before_or_after, time_filter.minutes)

        # Calculate the modified time
        modified_time = (current_time + timedelta(minutes=time_filter.minutes)).strftime("%H:%M:%S.%f")[:-3]
        if time_filter.before_or_after == BEFORE:
            # Check that appointment time is less than calculated time.
            g_or_l = "le"
        else:
            # Check that appointment time is greater than calculated time.
            g_or_l = "ge"

        clauses.append(f"{time_filter.start_or_end}/dateTime {g_or_l} '{today}T{modified_time}Z'")

    filter_str = " and ".join(clauses)
    logger.info("Resulting filter: %s", filter_str)
    return filter_str
