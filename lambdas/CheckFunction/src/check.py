import requests  
import logging as lg
from datetime import datetime, timedelta
import boto3
import os

logger = lg.getLogger()
logger.setLevel("INFO")

def getauthcode(variables):
    """ Get Authentication Code"""

    # Set the authentication endpoint and token endpoint
    auth_endpoint = 'https://login.microsoftonline.com/' + variables['tenant'] + '/oauth2/v2.0/token'
    logger.info('Auth endpoint: %s', auth_endpoint)

    # Create the payload for the token request
    payload = {
        'client_id': variables['client_id'],
        'client_secret': variables['client_secret'],
        'username': variables['username'],
        'password': variables['password'],
        'scope': 'https://graph.microsoft.com/Calendars.ReadWrite',
        'grant_type': 'password'  
    }

    # Send the token request
    response = requests.post(auth_endpoint, data=payload)

    # Check if the request was successful
    if response.status_code == 200:
        # Get the access token from the response
        access_token = response.json()['access_token']
        logger.info('Authentication successful')
        return access_token
    else:
        logger.error('Authentication failed: %d', response.status_code)
        logger.error(response.text)
        exit()


def getCalendar(access_token, variables, headers):
    """ Get Calendar"""

    # Get the current date  
    today = datetime.now().strftime('%Y-%m-%d')  

    # Get the current time  
    current_time = datetime.now()
    
    # Calculate the time 30 minutes in the future  
    future_time = (current_time + timedelta(minutes=18)).strftime("%H:%M:%S.%f")[:-3]
    
    # Calculate the time 30 minutes in the past  
    past_time = (current_time - timedelta(minutes=18)).strftime("%H:%M:%S.%f")[:-3]
    past_one_minute = (current_time - timedelta(minutes=1)).strftime("%H:%M:%S.%f")[:-3]
    
    # Print the results  
    print("Current Time:", current_time.strftime("%H:%M:%S"))
    print("Time 15 Minutes in the Past:", past_time)
    print("Time 15 Minutes in the Future:", future_time)

    params_start = {  
        '$filter': f"start/dateTime ge '{today}T{past_time}Z' and start/dateTime le '{today}T{past_one_minute}Z'"  
    }  

    params_end = {  
        '$filter': f"end/dateTime ge '{today}T{past_time}Z' and end/dateTime le '{today}T{past_one_minute}Z'"  
    }  

    # Send the calendar request  
    response_start = requests.get(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events', headers=headers, params=params_start)
    response_end = requests.get(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events', headers=headers, params=params_end)

    # Check if the request was successful
    if response_start.status_code == 200 and response_end.status_code == 200:
        # Get the appointments from the response
        start_appointments = response_start.json()['value']
        end_appointments = response_end.json()['value']
        return start_appointments, end_appointments
    else:
        logger.error('Failed to get calendar events!')


def process_appointments(appointments, variables, headers):
    """ Process the Appointments"""

    if len(appointments[0]) == 0:
        print('No missed start appointments found!')
    else:
        print('Missed start appointments found!')
        for appointment in appointments[0]:
            if 'Missed-Check-In' not in appointment['categories'] and 'Checked-In' not in appointment['categories']:
                appointment['categories'] = ['Missed-Check-In']
                appointment['subject'] = "Missed-Check-In : " +  appointment['subject']
                
                response = requests.patch(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events/' + appointment['id'], headers=headers, json=appointment)
                logger.info('Appointment updated with code: %s', str(response.status_code))
                message = {
                    "subject" : "Missed Check-In",
                    "content" : "The check-in time has been missed for the appointment: " + appointment['subject']
                }
                send_email(headers, message)
            else:
                logger.info('Appointment already flagged')
        
    
    if len(appointments[1]) == 0:
        print('No missed end appointments found!')
    else:
        print('Missed end appointments found!')
        for appointment in appointments[1]:
            if "Checked-In" in appointment['subject']:
                if 'Missed-Check-Out' not in appointment['categories'] and 'Checked-Out' not in appointment['categories'] and 'Missed-Check-In' not in appointment['categories']:
                    appointment['subject'] = appointment['subject'].replace("Checked-In", "Missed-Check-Out")
                    appointment['categories'] = ['Missed-Check-Out']
    
                    response = requests.patch(variables['token_endpoint'] + '/' + variables['username'] + '/calendar/events/' + appointment['id'], headers=headers, json=appointment)
                    logger.info('Appointment updated with code: %s', str(response.status_code))
                    message = {
                        "subject" : "Missed Check-Out",
                        "content" : "The check-out time has been missed for the appointment: " + appointment['subject']
                    }
                    send_email(headers, message)
                else:
                    logger.info('Appointment already flagged')


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

    ssm_prefix = os.environ['ssm_prefix']

    # Set the client ID, client secret, username, and password  
    ssm = boto3.client('ssm')
    ssm_prefix = os.environ['ssm_prefix']
    variables = {}
    variables['client_id'] = ssm.get_parameter(Name='/'+ssm_prefix+'/clientid', WithDecryption=True)['Parameter']['Value']
    variables['client_secret'] = ssm.get_parameter(Name='/'+ssm_prefix+'/clientsecret', WithDecryption=True)['Parameter']['Value']
    variables['username'] = ssm.get_parameter(Name='/'+ssm_prefix+'/emailuser', WithDecryption=True)['Parameter']['Value']
    variables['password'] = ssm.get_parameter(Name='/'+ssm_prefix+'/emailpass', WithDecryption=True)['Parameter']['Value']
    variables['tenant'] = ssm.get_parameter(Name='/'+ssm_prefix+'/tenant', WithDecryption=True)['Parameter']['Value']
    variables['token_endpoint'] = 'https://graph.microsoft.com/v1.0/users'

    logger.info('client id: %s', variables['client_id'])
    logger.info('tenant   : %s', variables['tenant'])
    logger.info('email    : %s', variables['username'])

    access_token = getauthcode(variables)

    headers = {
        'Authorization': 'Bearer ' + access_token,  
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="Europe/London"' 
    }

    appointments = getCalendar(access_token, variables, headers)

    process_appointments(appointments, variables, headers)
