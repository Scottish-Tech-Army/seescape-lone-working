# Prerequisites

You must have done all the following before you start installation.

1. [Set up an AWS subscription to use](#aws-subscription)

2. [Set up an M365 mailbox with appropriate client configuration](#m365-account)

3. [Created a configuration file](#config-file)

All processes documented here are assumed to run using the linux command line, and depend on:

- python

- The AWS CLI

- Various command line tools including `bash`, `sed`, `awk`, and `jq`.

## AWS subscription

This depends on an AWS subscription. It's normally best to use a dedicated subscription.

The AWS CLI must be configured with a profile whose name will be used later in the configuration file, and with a default region that matches where everything is to be deployed.

## M365 account

The M365 requirements are to set up an M365 email account with a calendar to use, plus the capability for the application to log into it. This process is fiddly, but that's the trouble with security.

### Process overview

Setting this up requires three steps.

1. Getting an [M365 tenant](#tenant).

2. Creating a [shared mailbox](#shared-mailbox)

3. Setting up an [application](#application)

The outputs from this process will include:

1. Tenant GUID

2. Email address and password

3. ClientID and ClientSecret for the app

Store these off securely; you'll need all of them later.

### Tenant

You must have an M365 business or enterprise tenant to use. Note that you can sign up for a [free M365 tenant as a non-profit](https://www.microsoft.com/en-gb/microsoft-365/nonprofit/), or failing that just create a [new tenant](https://www.microsoft.com/en-gb/microsoft-365/business/microsoft-365-plan-chooser).

Once you have your tenant, you need to [find your organisation's tenant ID](https://learn.microsoft.com/en-us/sharepoint/find-your-office-365-tenant-id), and store it safely for future use.

### Shared mailbox

You'll need a mailbox in your organisation that can be accessed by staff managing the application and appointments. The easiest type of account to use is a [shared mailbox](https://learn.microsoft.com/en-us/microsoft-365/admin/email/about-shared-mailboxes). To create such an account, perform the following steps.

- As an administrator, log into the [Microsoft admin centre](https://admin.microsoft.com/Adminportal/Home#/homepage).

- Select the `Shared mailboxes` option, which is in the `Teams & Groups` section on the left hand bar.

- Click `Add a shared mailbox`, and assign it an email address and a name. A good email is something like `loneworker@mycharity.org`.

- After a little while (up to a minute or so), the new shared mailbox appears in the list of shared mailboxes. Click on it.

    - A window of options will pop up. Click on the link `Read and manage permissions`

    - Add the users in your organisation that you want to be able to view and manage the shared calendar.

Note down the shared mailbox email address.

### Application

You now need to create and configure an *application*. This is the term that Microsoft Entra uses for a logical entity that has access rights, and which therefore can be granted permissions to the email account in question. All of these operations must be done as a user who has high levels of rights within the Office 365 enterprise in question.

- Create the application

    - Go to the [Entra Admin Centre](https://entra.microsoft.com)

    - Select `Applications` on the list on the left of the page, and within that select `App Registrations`.

    - Click the create (plus) button and fill out the form

        - Pick a name (such as `loneworker`). This does not matter, but you'll need to find it again, so pick something memorable.

        - Who can access this API - select the option for just accounts in this organisation.

        - Do not bother with a `Redirect URI` - leave it blank. Nobody is going to use this interactively.

        - Save off the `client ID` (shown as "Application (client) ID" in the overview)

    - You have an app registration. Create it some credentials.

        - Go to `certificates and secrets`. Add a secret and save the value securely. You will never see this value again, so if you lose it, you will have to create a new secret.

        - In the `authentication` tab, enable `Allow public flows`

- Now set up permissions under `API permissions` for the app registration in question. You need to do this *for all of the permissions required*.

    - Click on `Add a permission`

    - Click the "Microsoft Graph" button in the list of services

    - Where there is a button to pick permissions type, pick `Application`

    - Pick the relevant permission. The permissions you need to have checked are as follows.

        - `Calendars.ReadWrite`

        - `Mail.Send`

        - `Contacts.Read`

        - `User.Read.All`

    - Accept the choice; the permissions should appear in the list of permissions for the application.

    - Next to `Add a permission`, there is a button `Grant admin consent for <your tenant name>`. Click it.

#### Further client credentials steps

Unfortunately, this grants the application rights to every mailbox in the enterprise, which is not such a good idea. The solution is to use PowerShell to set up permissions to restrict it to a single mailbox (or more accurately to a group consisting of a single mailbox, the shared mailbox you created above). Instructions for this process are the following.

- Go to the [Entra Admin Centre](https://entra.microsoft.com)

- Create a group.

    - Navigate to `Groups` on the left

    - Create a new group, of type `Mail-Enabled Security`, which we will assume is called `loneworker`.

    - Give it an email. This email should be one that stops people accidentally inviting it to meetings - so do not give it something that can easily be confused with the lone worker shared mailbox mail. `nomailsg@example.com` is a good example.

    - Description I picked was "Users whose accounts the loneworker app can access"

    - Find and store the object ID GUID for the security group. This will be used as the `PolicyScopeGroupId` below.

- Add the shared mailbox to the group

    - Find the group

    - Click on `Members` and add the relevant users (i.e. the shared mailbox which above we called `loneworker@mycharity.org`).

- Use PowerShell to run the commands below; powershell comes with Windows but also exists on linux now.

    - Install the relevant module

        ~~~powershell
        Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser
        ~~~

    - Connect to Exchange Online as the admin user of the account.

        ~~~powershell
        Connect-ExchangeOnline -UserPrincipalName <YOUR_EMAIL>
        ~~~

    - Create a policy; note that you must substitute your application ID (client ID) into the string.

        ~~~powershell
        New-ApplicationAccessPolicy -AppId <YOUR_APP_ID> `
        -PolicyScopeGroupId <THAT_GUID_YOU_SAVED> `
        -AccessRight RestrictAccess `
        -Description "Restrict app access to allowed mailboxes only"
        ~~~

    - Test the policy for a specified mailbox. This should work for the shared mailbox, and fail for any other mailbox.

        ~~~powershell
        Test-ApplicationAccessPolicy -Identity <TEST_USER_EMAIL> -AppId <YOUR_APP_ID>
        ~~~

### Testing the client credentials

Once you have set up all of the M365 tenant information, it is very useful to test it all in isolation. Full instructions for how to validate your credentials are in [the test guide here](testing.md#validating-credentials).

## Config file

You need to create two configuration files for your deployment. Assuming your organisation is called `mycharity`, th

- There is a YAML document with various parameters in it. An example of this is [`example.yaml` in the config directory](../config/example.yaml).

    - Copy this file to create one called `mycharity.yaml` in the `config` directory.

    - Edit it appropriately following the instructions; for most things the defaults are fine, but you'll need to configure email addresses for emergency mails.

- There is a shell script with further parameters that is sourced before running any of the bash commands. An example of this is [`example_env.sh` in the config directory](../config/example_env.sh).

    - Copy this file to create one called `mycharity_env.sh` in the `config` directory.

    - Edit the fields as appropriate. Many will be able to just use the defaults, but you should at least change your `AWS_PROFILE` value, and the name of your config file (`mycharity.yaml` in this example).

