"""
Module containing common utility functions for the loneworker lambda functions.
"""
import boto3
from datetime import datetime, timedelta
import logging
import os
import requests

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
# Checked in or out for categories and body string.
CHECKED_IN = "Checked-In"
CHECKED_OUT = "Checked-Out"
MISSED_CHECK_IN = "Missed-Check-In"
MISSED_CHECK_OUT = "Missed-Check-Out"

class LoneWorkerManager:
    def __init__(self):
        """
        Init method just reads the configuration settings.
        """
        logger.info("Get configuration")
        self.read_config()

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

    def read_config(self):
        """
        Read the configuration settings.
        """
        ssm_prefix = os.environ['ssm_prefix']
        logger.info("Reading configuration from %s", ssm_prefix)

        # Read configuration from the environment
        ssm = boto3.client('ssm')
        ssm_prefix = os.environ['ssm_prefix']
        variables = {}
        self.client_id = get_param(ssm, ssm_prefix, "clientid")
        self.client_secret = get_param(ssm, ssm_prefix, "clientsecret", optional=True)
        self.username = get_param(ssm, ssm_prefix, "emailuser")
        self.password = get_param(ssm, ssm_prefix, "emailpass", optional=True)
        self.tenant = get_param(ssm, ssm_prefix, "tenant")

        # Trace some things.
        logger.info("Tenant: %s, Client ID: %s, username: %s", self.tenant, self.client_id, self.username)

        if not self.password and not self.client_secret:
            logger.error("Both clientid and emailpass are missing or blank - that is not permitted")
            raise ValueError("Both clientid and emailpass are missing or blank - that is not permitted")

        if self.password:
            logger.info("Password defined - using ROPC flow")
        else:
            logger.info("Password not defined - using ROPC flow")

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
            payload['scope'] = 'https://graph.microsoft.com/Calendars.ReadWrite'
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

    def send_mail(self, recipient, subject, content):
        """
        Send an email
        """
        logger.info("Sending email to %s, subject: %s", recipient, subject)
        message_payload =   {
                                "message": {
                                "subject": subject,
                                "body": {
                                    "contentType": "Text",
                                    "content": content
                                },
                                "toRecipients": [
                                    {
                                        "emailAddress": {
                                            "address": recipient
                                        }
                                    }
                                ]
                            }
                        }

        response = requests.post(self.mail_url, headers=self.headers, json=message_payload)
        if response.status_code != 200:
            logger.error('Error sending mail: %d, message: %s', response.status_code, response.text)
            raise RuntimeError(f"Error sending mail: {response.status_code}, message: {response.text}")

def get_param(ssm, prefix, name, optional=False):
    try:
        param = f"/{prefix}/{name}"
        logger.debug("Getting parameter %s", param)
        return ssm.get_parameter(Name=param, WithDecryption=True)['Parameter']['Value']
    except ssm.exceptions.ParameterNotFound:
        if optional:
            return None
        else:
            logger.error("Missing value for non-optional parameter %s", param)
            raise ValueError(f"Parameter {prefix}/{name} not found")

def build_time_filter(past_min, future_min, start_or_end):
    """
    Build a filter for Microsoft graph APIs that
    - checks on start or end date (which should be one of START and END)
    - starts past_min minutes in the past
    - ends future_min minutes in the future
    """
    logger.info("Build a filter on %s date from %d minutes in the past to %d minutes in the future", start_or_end, past_min, future_min)
    # Get the current date
    today = datetime.now().strftime('%Y-%m-%d')

    # Get the current time
    current_time = datetime.now()

    # Calculate the past and future times
    future_time = (current_time + timedelta(minutes=future_min)).strftime("%H:%M:%S.%f")[:-3]
    past_time = (current_time - timedelta(minutes=past_min)).strftime("%H:%M:%S.%f")[:-3]

    filter = f"{start_or_end}/dateTime ge '{today}T{past_time}Z' and {start_or_end}/dateTime le '{today}T{future_time}Z'"
    logger.info("Resulting filter: %s", filter)
    return filter
