# Design and architecture

The key elements of the design are shown in the architecture diagram below.


![Architecture Diagram](loneworker.drawio.svg)

The key flows are as follows.

- Shown in black, admin staff create and manage appointments in the shared mailbox calendar in Office 365.

- Shown in green, lone workers make calls to check in and out of appointments. (Although not shown in the diagram, their appointments are visible in their own calendars.)

    - Calls arrive at an AWS Connect instance.

    - The AWS Connect instance triggers a call to an AWS Lambda, the Connect Function

    - The Connect Function updates calendar appointments.

    - Where the emergency option is selected by the user, the Connect Function triggers emergency mails using the shared mailbox email.

- Shown in red, the Check Function, an AWS Lambda, periodically checks the shared mailbox calendar. If it detects that a checkin or checkout has been missed, it updates the calendar and sends an emergency email using the shared mailbox email.

- Finally, the Metrics Function, another AWS Lambda, reads metrics issued by the application every night and stores them for export to visualisation tools.

