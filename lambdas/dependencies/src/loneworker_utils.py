"""
Module containing common utility functions for the loneworker lambda functions.
"""
# General
import boto3
from collections import namedtuple
from datetime import datetime, timedelta
import datetime as dt
import json
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
    """
    Returns the module's logger instance.

    Returns:
        logging.Logger: Configured logger instance for this module
    """
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
    def __init__(self, app_type, metric_names=[]):
        """
        Initializes a LoneWorkerManager instance for handling lone worker operations.

        Args:
            app_type (str): Type of application, must be either 'Check' or 'Connect'
            metric_names (list, optional): List of metric names to initialize with zero values

        Raises:
            AssertionError: If app_type is not 'Check' or 'Connect'

        The manager:
        - Reads configuration from AWS Parameter Store
        - Initializes metrics tracking
        - Obtains Microsoft Graph API authentication token
        - Sets up API endpoints for calendar, mail, contacts, and users
        """
        logger.info("Get configuration for app %s", app_type)
        assert app_type in ("Check", "Connect"), "app_type must be either 'Check' or 'Connect'"
        self.app_type = app_type
        self.read_config()

        logger.info("Initialise metrics structures")
        self.init_metrics(metric_names)

        logger.info("Get auth token")
        self.get_token()

        # A couple of things it will be useful to work out in advance
        # Note that we use GMT for all times, to try to avoid timezone confusion.
        self.headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Prefer': 'outlook.timezone="Etc/GMT"'
        }
        self.calendar_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/calendar/events"
        self.mail_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/sendMail"
        self.contacts_url = f"https://graph.microsoft.com/v1.0/users/{self.username}/contacts"
        self.users_url = f"https://graph.microsoft.com/v1.0/users"

    def read_config(self):
        """
        Reads and validates configuration settings from AWS Parameter Store.

        The function:
        - Retrieves mandatory parameters (clientid, emailuser, tenant, config, clientsecret)
        - Validates configuration using cfg_parser
        - Stores configuration values as instance attributes

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.app_prefix  = os.environ['ssm_prefix']
        logger.info("Reading configuration from %s", self.app_prefix)

        # Read configuration from the environment
        ssm = boto3.client('ssm')
        self.app_prefix = os.environ['ssm_prefix']
        mand_names = ["clientid", "emailuser", "tenant", "config", "clientsecret"]
        optional_names = []
        values = get_params(ssm, self.app_prefix, mand_names=mand_names, optional_names=optional_names)

        self.client_id = values["clientid"]
        self.client_secret = values["clientsecret"]
        self.username = values["emailuser"]
        self.tenant = values["tenant"]

        # Trace some things.
        logger.info("Tenant: %s, Client ID: %s, username: %s", self.tenant, self.client_id, self.username)

        # More config in the config blob.
        logger.info("Validate and save configuration")
        self.cfg = cfg_parser.LambdaConfig(data=values["config"])

    def get_app_cfg(self):
        """
        Retrieves application-specific configuration.

        Returns:
            dict: Configuration dictionary for the current application type (Check/Connect)
                 containing timing parameters and other app-specific settings
        """
        return self.cfg.get_app_cfg(self.app_type)

    def get_token(self):
        """
        Obtains an authentication token from Microsoft Graph API.

        The function:
        - Uses client credentials flow for authentication
        - Requests token from Microsoft OAuth endpoint
        - Stores token in instance for API calls

        Raises:
            RuntimeError: If authentication fails with status code and error message
        """

        # Set the authentication endpoint and token endpoint
        auth_endpoint = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
        logger.info('Auth endpoint: %s', auth_endpoint)

        # Create the payload for the token request
        payload = {
            'client_id': self.client_id,
            'username': self.username
        }

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
        Retrieves filtered calendar events from Microsoft Graph API.

        Args:
            filter (str): Microsoft Graph API filter string for calendar events

        Returns:
            list: Calendar events matching the specified filter

        Raises:
            RuntimeError: If the calendar API request fails

        Note:
            The filter should be formatted according to Microsoft Graph API's $filter syntax
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
        Updates a calendar event with specified changes.

        Args:
            event_id (str): ID of the calendar event to update
            changes (dict): Dictionary of changes to apply to the event
                          (e.g., {'categories': ['new-category']})

        Raises:
            RuntimeError: If the calendar update operation fails
        """
        logger.info("Updating calendar event %s with new categories %s", event_id, changes.get("categories"))
        response = requests.patch(f"{self.calendar_url}/{event_id}", headers=self.headers, json=changes)

        if response.status_code != 200:
            logger.error('Calendar patch operation failed: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Calendar patch operation failed: {response.status_code}, message: {response.text}")

    def send_email(self, type, subject, content):
        """
        Sends an email using the Microsoft Graph API.

        This method constructs an email payload and sends it to the specified recipients
        using the Microsoft Graph API. It logs the process and raises an exception if the
        email fails to send.

        Args:
            type (str): The type of email to send, used to retrieve the appropriate recipients.
            subject (str): The subject line of the email.
            content (str): The body content of the email.

        Raises:
            RuntimeError: If the email fails to send, an exception is raised with the
                          HTTP status code and error message.

        Logs:
            - Logs the recipients and subject of the email being sent.
            - Logs the constructed payload for debugging purposes.
            - Logs an error if the email fails to send.
        """
        recipients = self.cfg.get_email_recipients(type)

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
        Maps a phone number to associated email addresses from contacts and users.

        Args:
            number (str): Phone number to search for (supports international format)

        Returns:
            tuple: (addresses, display_name) where:
                - addresses (list): List of email addresses associated with the phone number
                - display_name (str): Display name of the first matching contact/user, or "UNKNOWN"

        The function:
        - Searches both contacts and users directories
        - Handles international number format (+44) conversion
        - Returns all matching email addresses in lowercase
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

    def init_metrics(self, metric_names):
        """
        Initializes CloudWatch metrics tracking.

        Args:
            metric_names (list): List of metric names to initialize with zero values

        The function:
        - Sets up CloudWatch client
        - Initializes metrics namespace using app prefix and type
        - Creates tracking dictionaries for both current and to-be-emitted metrics
        """
        # Set up metrics ready to report
        self.cloudwatch = boto3.client('cloudwatch')
        self.metrics_namespace = f"{self.app_prefix}/{self.app_type}"

        # metrics is all the metrics reported; metrics_to_emit is all the metrics that have
        self.metrics = defaultdict(int)
        self.metrics_to_emit = defaultdict(int)

        # Add any metric names supplied to the list ready to emit, with zero values.
        for name in metric_names:
            self.metrics_to_emit[name] = 0

    def increment_counter(self, name, increment=1):
        """
        Increments a named metric counter.

        Args:
            name (str): Name of the metric to increment
            increment (int, optional): Amount to increment by (default: 1)

        The function updates both the current metrics and the to-be-emitted metrics.
        """
        self.metrics[name] += increment
        self.metrics_to_emit[name] += increment

    def emit_metrics(self):
        """
        Emits accumulated metrics to CloudWatch.

        The function:
        - Sends all pending metrics to CloudWatch with current timestamp
        - Uses Count as the unit for all metrics
        - Clears the to-be-emitted metrics after successful emission
        - Preserves the total metrics history in the metrics dictionary
        """
        logging.info("Emit metrics array: %s", self.metrics)
        # Metrics timestamps must be in UTC
        timestamp = datetime.now(dt.timezone.utc)
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
        Retrieves all recorded metrics.

        Returns:
            dict: Dictionary of all metrics that have been recorded,
                 including both emitted and pending metrics
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

class TimeFilter:
    def __init__(self, minutes=None, datetime=None, before_or_after=None, start_or_end=None):
        """
        Initializes a time filter for calendar event queries.

        Args:
            minutes (int, optional): Number of minutes relative to current time
            datetime (str, optional): Explicit datetime string in Microsoft Graph format
            before_or_after (str): Must be either 'before' or 'after'
            start_or_end (str): Must be either 'start' or 'end'

        Raises:
            ValueError: If neither or both minutes and datetime are provided

        Note:
            Either minutes or datetime must be provided, but not both.
            The datetime string must be in Microsoft Graph API format.
        """
        if (minutes is None and datetime is None) or (minutes is not None and datetime is not None):
            raise ValueError("Exactly one of 'minutes' or 'datetime' must be provided.")
        self.minutes = minutes
        self.datetime = datetime
        self.before_or_after = before_or_after
        self.start_or_end = start_or_end
        if datetime:
            self.explicit = True
        else:
            self.explicit = False

def build_time_filter(time_filters):
    """
    Builds a Microsoft Graph API filter string from TimeFilter objects.

    Args:
        time_filters (list): List of TimeFilter objects defining time constraints

    Returns:
        str: Microsoft Graph API filter string combining all time filters with 'and' operators

    Raises:
        ValueError: If any TimeFilter has invalid before_or_after or start_or_end values

    The function:
    - Combines multiple time filters with 'and' operators
    - Handles both relative (minutes-based) and absolute (datetime-based) filters
    - Ensures all datetime strings are in UTC/GMT format
    - Supports filtering on both start and end times of events
    """
    logger.info("Number of clauses in time filter: %d", len(time_filters))
    clauses = []
    current_time = datetime.now(dt.timezone.utc)

    for time_filter in time_filters:
        if time_filter.before_or_after not in [BEFORE, AFTER]:
            raise ValueError(f"Time direction must be either '{BEFORE}' or '{AFTER}' - provided value '{time_filter.before_or_after}'")
        if time_filter.start_or_end not in [START, END]:
            raise ValueError(f"Start or end must be either '{START}' or '{END}' - provided value '{time_filter.start_or_end}'")

        if time_filter.explicit:
            logger.info("Building a filter on %s time, checking that it is %s an explicit time %s",
                        time_filter.start_or_end, time_filter.before_or_after, time_filter.datetime)
            # Truncate anything after the decimal point if present, then put a Z on the end.
            datetime_string = time_filter.datetime.split('.')[0]
        else:
            logger.info("Building a filter on %s time, checking that it is %s a time %d minutes from now",
                        time_filter.start_or_end, time_filter.before_or_after, time_filter.minutes)

            # Calculate the modified datetime
            target_datetime = current_time + timedelta(minutes=time_filter.minutes)
            datetime_string = target_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        if time_filter.before_or_after == BEFORE:
            # Check that appointment time is less than calculated time.
            g_or_l = "le"
        else:
            # Check that appointment time is greater than calculated time.
            g_or_l = "ge"

        # Note that we append a Z to indicate UTC.
        clauses.append(f"{time_filter.start_or_end}/dateTime {g_or_l} '{datetime_string}Z'")

    filter_str = " and ".join(clauses)
    logger.info("Resulting filter: %s", filter_str)
    return filter_str
