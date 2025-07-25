# Lone working project

This project provides tooling to allow lone remote workers to call back and report for safety purposes.

## User experience and overview

The issue is that charities who arrange home visits need to monitor their visiting staff's arrival and departure at appointments. Those visitors may not have smartphones, or have some disability which makes using a smartphone app tricky. Hence the model is that each visitor calls in when they arrive and leave appointments, and their status is reported to a Microsoft 365 calendar. Staff at the charity can view where and when visitors arrived and left, and are notified if a visitor is overdue.

## Implementation overview

The implementation consists of three parts.

- There is an M365 calendar showing the current status.

- There are multiple AWS resources including Amazon Connect and lambda functions to implement the call handling.

- There is a lambda function that checks the calendar to report issues.

This repository contains scripts and instructions for deploying, using and managing an implementation.

## Detailed instructions

There are documents covering the following.

- There is an [architecture document](docs/architecture.md) that shows the design.

- Before you deploy a new instance, you must have satisfied the [prerequisites to installation](docs/prereqs.md).

- You can then run various steps to perform [deployment creation](docs/creation.md).

- Once installed, you should test using the [testing procedures](docs/testing.md).

- Upgrade, monitoring, and diagnostics collection are covered in the [operations document](docs/operations.md).

- If you are just using the system (making calls and managing calendars) you should read the [user instructions](docs/user.md).
