# User instructions

## Instructions for office staff

All data is stored in a Microsoft 365 (Outlook) calendar of a shared user specifically configured for the purpose.

### Accessing the shared user account

Users who are managing this mailbox can now (or later) view it in Outlook Web or the Outlook Application. *These users must have permissions configured by a user [as documented here](prereqs.md#account)*

- In Outlook Web, follow these steps.

    - Open your [Outlook Web mailbox](https://outlook.office.com/)

    - Click on your user's picture / initials in the circle at top right, and select `Open another mailbox`. This gives you another tab with a view of the shared mailbox including the calendar.

    - Optionally, to add a view of the mailbox's emails, right click on `Folders` and select `Add shared folder or mailbox`.

- In the Outlook application, follow these steps.

    - Open Outlook and go to the `Calendar` view.

    - In the Manage Calendars section, click `Open Calendar`, then `Open Shared Calendar`.

    - In the `Open a Shared Calendar` dialog box, enter the name of the shared mailbox.

    - Optionally, to add a view of the shared mailbox's emails via `Add shared folder or mailbox`.

### Configuring user accounts

Every person who is to be tracked by the Lone Worker application must have a mobile phone configured. This can be done in two ways.

- If the person has an account and email in the Office 365 tenant, the Office 365 admin should set it. *No, I don't understand why sometimes why users sometimes can and sometimes cannot set their own phone numbers. If you can just set it yourself, hooray*.

    - Go to the [users tab](https://admin.microsoft.com/Adminportal/Home?#/users) in the Office 365 admin portal.

    - Select the user in question.

    - Click `Manage contact information`

    - Set up the `mobilePhone` field (called `Mobile phone` in some places).

- If the person does not have an account but still needs to be tracked, then create a personal contact in the shared mailbox.

### Creating and configuring meetings

Whenever a meeting is to occur that must be tracked, it should be created in Outlook. It is best to create the meeting in the shared mailbox calendar

- Access the shared mailbox calendar

- Create the meeting and invite whichever workers are expected to attend.

- Attendees receive a meeting invite that they should accept as usual.

*It is also possible to create the meeting in the user's mailbox and invite the shared mailbox. If you do it that way round, you have to have somebody accept the meeting invite in the shared mailbox to avoid being buried in meeting invites.*

## Monitoring meetings

Meetings are monitored by the lone worker application.

- When a lone worker checks in or out of a meeting, an Outlook category "Checked-In" or "Checked-Out" respectively is added to the calendar appointment in the central calendar.

    - If a lone worker fails to make this call on time, the categories can be manually added (such as if the worker phones up to report that a meeting ended so early they cannot check out yet), or there is an error.

- If a worker calls in and selects "3" then:

    - An email is sent to the emergency address or DL

    - Any meeting that is found that seems to match is marked with an "Emergency" category in the shared mailbox calendar.

- If a worker fails to check in or check out on time then

    - An email is sent to the emergency address or DL

    - Any meeting that is found that seems to match is marked with an "Emergency" category in the shared mailbox calendar.


## Instructions for lone workers

Call the phone number for the application when you arrive at or leave from a meeting.

- When prompted, enter your user ID.

- When prompted enter

    - "1" to check into a meeting scheduled to start within 15 minutes of the current time

    - "2" to check out of a meeting scheduled to end within 15 minutes of the current time

    - "3" in case of emergency, where you wish the office staff to call the police or otherwise react. You will hear a message saying that all operators are busy; this is in case the call is overheard.
