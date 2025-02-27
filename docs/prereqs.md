# Prerequisites

You must have done all the following before you start installation.

- [Set up an AWS subscription to use](#aws-subscription)

- [Set up an M365 mailbox with appropriate client configuration](#m365-account)

- [Created a configuration file](#config-file)

*To be provided - AWS CLI, other tools*

## AWS subscription

*To be provided - there are a couple of minor requirements here, including pointing at some AWS docs and setting up CLI.*

## M365 account

The M365 requirements are to set up an M365 email account with a calendar to use, plus the capability for the application to log into it. This process is fiddly, but that's the trouble with security.

Before you start working through the process, you need to decide what OAuth2 flow to use, because we are in that kind of world. There are two choices, either [ROPC (Resource Owner Password Credentials) flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth-ropc), or [client credentials flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow). The pros and cons of these methods are as follows.

- Using ROPC is simpler. However, it means you must turn off MFA for the email account you use, and will pass the user account password around.

- Using client credentials is a little more complex to set up, but avoids the above disadvantages.

If this is all Greek to you, then you are very lucky to have been spared understanding OAuth2, and you should follow this flow.

- If you cannot turn off MFA, use client credentials.

- Otherwise, use ROPC.

Good - we have a decision. Remember it.

### Process overview

Setting this up requires three steps.

1. Getting an [M365 tenant](#tenant).

2. Creating an [email account](#account)

3. Setting up an [application](#application)

The outputs from this process will include:

1. Tenant GUID

2. Email address and password

3. ClientID and ClientSecret for the app

Store these off securely; you'll need all of them later.

### Tenant

There are four options here.

1. If you have Microsoft accounts managed by your organisation, you already have a tenant and should use that. You do need to [find your organisations tenant ID](https://learn.microsoft.com/en-us/sharepoint/find-your-office-365-tenant-id), and store it safely for future use, but can skip to [setting up an account](#account).

2. Alternatively, you can sign up for your [free M365 tenant as a non-profit](https://www.microsoft.com/en-gb/microsoft-365/nonprofit/), and then proceed as above. This takes a few days and requires Microsoft to validate your charity. You should do this if you are thinking "wouldn't having some Microsoft managed email be useful".

3. You can create an M365 tenant using the [the Microsoft developer program](https://learn.microsoft.com/en-us/entra/identity-platform/test-setup-environment?tabs=microsoft-365-developer-program). This only works if you have a paid for account of some kind already. I have not tested this.

If none of these works, you can just bite the bullet and create a [new enterprise subscription](https://www.microsoft.com/en-gb/microsoft-365/business/microsoft-365-plan-chooser). This is free for 30 days, after which you have to pay £4.60 plus VAT per month (assuming you only have a single email address).

### Account

You'll need a user in your organisation with email to use. You can either use an existing user (if this is a test tenant - do not use some real person's account!), or create a new user in the [Microsoft admin centre](https://admin.microsoft.com/Adminportal/Home#/homepage).

Note down their email address and password.

### Application

You now need to create an *application*. This is the term that Microsoft Entra uses for a logical entity that has access rights, and which therefore can be granted permissions to the email account in question.

- Go to the [Entra Admin Centre](https://entra.microsoft.com]

- Select `Applications` on the list on the left of the page, and within that select `App Registrations`.

- Click the create (plus) button and fill out the form

    - Pick a name (such as `loneworker`). This does not matter, but you'll need to find it again, so pick something memorable.

    - Who can access this API - just accounts in this organisation.

    - Do not bother with a `Redirect URI` - leave it blank. Nobody is going to use this interactively.

- You have an app registration. *If you are using the client credentials model only*, create it some credentials.

    - Save off the `client ID` (shown as "Application (client) ID" in the overview)

    - Go to `certificates and secrets`. Add a secret and save the value securely. You will never see this value again, so if you lose it, you will have to create a new secret.

    - In the `authentication` tab, enable `Allow public flows`

- Now set up permissions under `API permissions`.

    - Click on `Add a permission`

    - Click the "Microsoft Graph" button in the list of services

    - Where there is a button to pick permissions type:

        - Pick `Application` for client credentials

        - Pick `Delegated permissions` for ROPC.

    - Pick the `Calendars.ReadWrite` permission, and select it.

    - Next to `Add a permission`, there is a button `Grant admin consent for <your tenant name>`. Click it.

#### Further client credentials steps

Unfortunately, this grants the application rights to every mailbox in the client credentials case, which is not such a good idea. The solution is to use PowerShell to set up permissions to restrict it to a single mailbox (or more accurately to a group consisting of a single mailbox). Instructions for this process are the following.

- Go to the [Entra Admin Centre](https://entra.microsoft.com]

- Create a group.

    - Navigate to `Groups` on the left

    - Create a new group, of type `Security`, which we will assume is called `loneworker`.

    - Description I picked was "Users whose accounts the loneworker app can access"

- Add the worker that you want to the group

    - Find the group

    - Click on `Members` and add the relevant users

- Install PowerShell. This exists on linux.

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
  -PolicyScopeGroupId "loneworker" `
  -AccessRight RestrictAccess `
  -Description "Restrict app access to allowed mailboxes only"
~~~

- Test the policy for a specified mailbox/

~~~powershell
Test-ApplicationAccessPolicy -Identity <TEST_USER_EMAIL> -AppId <YOUR_APP_ID>
~~~

*TODO: Need to test and probably script the above.*

## Config file

Config files - example is `plw_env.sh`

*TODO: Some documentation in the example file, needs beefing up*


