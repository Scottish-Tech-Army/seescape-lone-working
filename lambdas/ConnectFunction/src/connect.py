import requests  
import logging as lg
from datetime import datetime, timedelta
import boto3
import os

logger = lg.getLogger()
logger.setLevel("INFO")

def getauthcode(variables):
    """ Get Authentication Code for MS Graph Calls"""

    # Set the authentication endpoint
    auth_endpoint = 'https://login.microsoftonline.com/' + variables['tenant'] + '/oauth2/v2.0/token'

    # Create the payload for the token request
    payload = {  
        'client_id': variables['client_id'],  
        'client_secret': variables['client_secret'],  
        'username': variables['username'],  
        'password': variables['password'],  
        'scope': 'https://graph.microsoft.com/calendars.readwrite',  
        'grant_type': 'password'  
    }

    # Send the token request
    response = requests.post(auth_endpoint, data=payload)

    # Check if the request was successful
    if response.status_code == 200:
        # Get the access token from the response and return it
        access_token = response.json()['access_token']
        logger.info('Authentication successful')
        return access_token
    else:
        logger.error('Authentication failed')
        logger.error(response.text)
        exit()


def getCalendar(variables, headers):
    """ Get Calendar items from the MS Graph API"""

    # Get the current date
    today = datetime.now().strftime('%Y-%m-%d')  

    # Get the current time  
    current_time = datetime.now()
    
    # Calculate the time 16 minutes in the future and the past based on the current time.
    # This gives an approximate 15 minute window before for the appointment to be checked in.
    future_time = (current_time + timedelta(minutes=16)).strftime("%H:%M:%S.%f")[:-3]
    past_time = (current_time - timedelta(minutes=16)).strftime("%H:%M:%S.%f")[:-3]
    
    # Print the current time and the action selected from the menu.
    logger.info("Current Time: %s", current_time.strftime("%H:%M:%S"))
    logger.info("Action Selected: %s", variables['action'])

    if variables['action'] == "1":
        # Option 1 is to check in an appointment.
        # Sets a filter base on the start time and date of appointments. This uses the past and future time calculated above
        # to give a 30 minute window that the appointment would have started in.
        params = {  
            '$filter': f"start/dateTime ge '{today}T{past_time}Z' and start/dateTime le '{today}T{future_time}Z'"  
        }  
    if variables['action'] == "2":
        # Option 2 is to check out of an appointment.
        # Sets a filter base on the end time and date of appointments. This uses the past and future time calculated above
        # to give a 30 minute window that the appointment would have ended in.
        params = {  
            '$filter': f"end/dateTime ge '{today}T{past_time}Z' and end/dateTime le '{today}T{future_time}Z'"  
        } 

    # Get the appointments from the calendar using MS Graph API
    response = requests.get(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events', headers=headers, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        # Get the appointments from the response
        appointments = response.json()['value']
        return appointments
    else:
        logger.error('Failed to get calendar events!')
        logger.error(response.text)


def process_appointments(appointments, variables, headers):
    """ Process Appointments"""

    for appointment in appointments:
        # Check to see if the staff ID is in the appointment body
        if 'ID:'+variables['staffid'] in appointment['bodyPreview']:
            logger.info('Appointment found for ID: %s', variables['staffid'])
            logger.info('Appointment subject is: %s', appointment['subject'])
            # Checked In
            if variables['action'] == '1':
                if "Checked-In" in appointment['subject']:
                    logger.info('Appointment already Checked-In')
                    return "Your appointment has already been checked into"
                appointment['categories'] = ['Checked-In']
                appointment['subject'] = "Checked-In : " + appointment['subject']
                message = "Your appointment has been checked in"
            
            # Checked Out
            if variables['action'] == '2':
                if "Checked-Out" in appointment['subject']:
                    logger.info('Appointment already Checked-Out')
                    return "Your have already checked out of your appointment"
                
                appointment['categories'] = ['Checked-Out']
                if "Checked-In" in appointment['subject']:
                    appointment['subject'] = appointment['subject'].replace("Checked-In", "Checked-Out")
                elif "Missed-Check-Out" in appointment['subject']:
                    appointment['subject'] = appointment['subject'].replace("Missed-Check-Out", "Checked-Out")
                else:
                    appointment['subject'] = "Checked-Out : " + appointment['subject']
                message = "Your appointment has been checked out"
            
            if variables['action']=='3':
                send_email(headers, {
                    "subject" : "Emergency Assistance Required!",
                    "content" : "Emergency Assistance is required for: " + appointment['subject']
                })

            response = requests.patch(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events/' + appointment['id'], headers=headers, json=appointment)
            logger.info('Appointment updated with code: %s', str(response.status_code))

            if response.status_code == 200:
                return message
            else:
                return "There has been an error, please contact the office for assistance"

def send_email(headers, message):
    """ Send Email"""
    message_payload =   {
                            "message": {
                                "subject": message['subject'],
                                "body": {
                                    "contentType": "Text",
                                    "content": message['content']
                                },
                                "toRecipients": [
                                    {
                                        "emailAddress": {
                                            "address": "LoneWorkerNotifications@seescape.org.uk"
                                        }
                                    }
                                ]
                            }
                        }
    
    response = requests.post('https://graph.microsoft.com/v1.0/me/sendMail', headers=headers, json=message_payload)
    logger.info('Email sent with code: %s', str(response.status_code))

def lambda_handler(event, context):
    """ Lambda Handler"""

    # Set the client ID, client secret, username, and password  
    ssm_prefix = os.environ['ssm_prefix']
    ssm = boto3.client('ssm')
    variables = {}
    variables['client_id'] = ssm.get_parameter(Name='/'+ssm_prefix+'/clientid', WithDecryption=True)['Parameter']['Value']
    variables['client_secret'] = ssm.get_parameter(Name='/'+ssm_prefix+'/clientsecret', WithDecryption=True)['Parameter']['Value']
    variables['username'] = ssm.get_parameter(Name='/'+ssm_prefix+'/emailuser', WithDecryption=True)['Parameter']['Value']
    variables['password'] = ssm.get_parameter(Name='/'+ssm_prefix+'/emailpass', WithDecryption=True)['Parameter']['Value']
    variables['tenant'] = ssm.get_parameter(Name='/'+ssm_prefix+'/tenant', WithDecryption=True)['Parameter']['Value']
    variables['staffid'] = event['Details']['ContactData']['Attributes']['idnumber']
    variables['action'] = event['Details']['Parameters']['buttonpressed']
    variables['token_endpoint'] = 'https://graph.microsoft.com/v1.0/users'

    logger.info("Getting Authentication Code")
    access_token = getauthcode(variables)
    logger.info("Authentication Code Received")

    headers = {
        'Authorization': 'Bearer ' + access_token,  
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="Europe/London"' 
    }

    resultMap = {
            "message" : ""
            }

    if variables['action'] != '3':
        appointments = getCalendar(variables, headers)
        if appointments:
            resultMap["message"] = process_appointments(appointments, variables, headers)
        else:
            resultMap["message"] = "No appointment found, please contact the office."

    if variables['action'] == '3':
        send_email(headers, {
            "subject" : "Emergency Assistance Required!",
            "content" : "Emergency Assistance is required for ID " + variables['staffid']
        })

    return resultMap