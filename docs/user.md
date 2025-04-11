# User instructions

The lone worker application tracks whether lone workers have checked in or out of meetings, and warns if they fail to check in or out in good time. This allows office staff to tell if workers are potentially at risk.

Office staff set up meetings in the calendar of a shared mailbox (the `loneworker` mailbox). The application allows workers to check in or out by phone, and reports by email when they fail to do so.

- A lone worker can check in or out of a meeting by calling the application phone number and pressing "1" or "2" respectively.

    - If something goes wrong with the phone call, office staff can manually check a lone worker in or out, by updating fields in the calendar.

- If a worker fails to check in or check out on time then office staff should investigate.

    - The application sends an email to a list of addresses to inform the office staff that a checkin or checkout was missed, including information about the worker and the meeting.

    - The meeting in the shared mailbox calendar is marked to indicate that there is a problem.

- If a lone worker feels threatened or unsafe, they can call the application phone number and select "3".

    - This plays a message about contacting the office and a callback from Veronica, in case the call is overheard.

    - The application sends an email to the emergency list.

    - Any meeting that is found that seems to match is marked with an "Emergency" category in the shared mailbox calendar.

The two sections below give specific instructions for using the application for the two different types of user.

1. [Office staff managing the lone worker calendar](#instructions-for-office-staff)

2. [Lone workers attending meetings](#instructions-for-lone-workers)

## Instructions for office staff

All data is stored in the calendar of the lone worker shared mailbox in Microsoft 365 (Outlook). Office staff monitor this calendar to track staff status, and monitor their emails for reported issues.

### Accessing the shared mailbox calendar

Users who are managing the shared mailbox calendar can view it in Outlook Web or the Outlook Application. *Office staff doing this must have permissions configured [as documented here](prereqs.md#account)*

- In Outlook Web, follow these steps.

    - Open your [Outlook Web mailbox](https://outlook.office.com/)

    - Click on your user's picture / initials in the circle at top right, and select `Open another mailbox`. This gives you another browser tab with a view of the shared mailbox including the calendar.

- In the Outlook application, follow these steps.

    - Open Outlook and go to the `Calendar` view.

    - In the Manage Calendars section, click `Open Calendar`, then `Open Shared Calendar`.

    - In the `Open a Shared Calendar` dialog box, enter the name of the shared mailbox.

### Configuring user accounts

Every person who is to be tracked by the lone worker application must have a mobile phone number configured. This can be done in two ways, depending on whether the user has an account in the same organisation or not.

- If the lone worker has an account and email in the Microsoft 365 (Office / Outlook) tenant (organisation), the admin should set the mobile number. *In some tenants, users may have the rights to set their own mobile number, but that is not the Microsoft 365 default.* To set up the mobile number, do the following.

    - Go to the [users tab](https://admin.microsoft.com/Adminportal/Home?#/users) in the Office 365 admin portal.

    - Select the user in question.

    - Click `Manage contact information`

    - Set up the `mobilePhone` field (called `Mobile phone` in some places). This should be the user's phone number. If this is a UK phone number, then you can just use `07123123456` format; for a foreign number you have to use the `+447123123456` format.

- If the person does not have an account in Microsoft 365 organisation but still needs to be tracked, then create a personal contact *in the shared mailbox*.

    - Create a personal contact in the shared mailbox.

    - Set the contact email address to be that of the user.

    - Set the mobile phone field up exactly as above.

Once you have set up a lone worker's mobile number, you should have them test it, in case the number was entered incorrectly.

- Have the user call the application number and press "1".

- If they hear a message saying that no meeting was found, then all is well. If they hear a message saying that the number was not recognised, then things have gone wrong, and the number was not entered correctly.

### Creating and managing meetings

Whenever a meeting is to occur that must be tracked, it should be created in the shared mailbox calendar in Outlook. Any lone workers who are to attend must be invited (if more than one is invited, any one of them can check the meeting in or out). Alternatively, you can create the meeting in the user mailbox and invite the shared mailbox - whichever is more convenient.

When a meeting has been created, you can view its categories (click on the `Categories` field in the meeting). The following categories may be set by the lone worker application.

- `Checked-In` - the lone worker has checked in for this meeting.

- `Checked-Out` - the lone worker has checked out from this meeting.

- `Missed-Check-In` - the lone worker was due to check in but failed to do so.

- `Missed-Check-Out` - the lone worker checked in, but did not check out.

- `Emergency` - the lone worker made an emergency call at a time when they may have been in this meeting.

You may set these categories manually. For example, if a lone worker has left the meeting but did not check out, it is possible to manually set the `Checked-Out` category, and the meeting will not trigger a missed checkout mail.

### Emergency emails

The lone worker application sends emails to a configured list of addresses under two circumstances.

- If a lone worker calls in and selects option "3", indicating an emergency situation.

- If a lone worker was due to check in or out from a meeting, and did not do so.

In either case, office staff must check the content of the email and investigate what happened.

## Instructions for lone workers

### Setting up meetings

All remote meetings must be added to the shared mailbox as well as the user mailbox.

- If you create the meeting in your user account, then invite the shared mailbox as an attendee.

- Alternatively, the office staff may create the meeting for you using the shared mailbox account and invite you; you should accept normally.

### Checking in and out

You must check in within 15 minutes of the start of the meeting, and check out within 15 minutes of the end. To do this, call the phone number for the application when you arrive at or leave from a meeting.

- When prompted enter

    - "1" to check into a meeting (which must start within 15 minutes of the current time)

    - "2" to check out of a meeting (which must end within 15 minutes of the current time).

    - "3" in case of emergency, where you wish the office staff to call the police or otherwise react. You will hear a message saying that all operators are busy; this is in case the call is overheard.

- If you are unable to check in or out, or cannot attend a meeting, inform the office staff (who can cancel the meeting or manually check it in or out).
