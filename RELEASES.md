# Releases

This document describes all the releases in order, with their key content and upgrade processes.

## v1.0

First full release; no upgrade process as nothing to upgrade from.

## v1.1

Upgraded version with miscellaneous enhancements and fixes.

### Content

- Add email notification of alarms (issue #37)

- Add API token expiry process and alarms (issue #38)

- Improve metrics to include count of successful meetings (issue #42)

- Fix recurring meetings (issue #39)

### Upgrade process

- Set expiry date in `clientsecretexpiry`

- Build code with `scripts/code_build.sh test` and `scripts/code_push.sh`

- Run `scripts/lambdas.sh` to redeploy

- Configure email for notifications

- Notify Seescape, including pointing them at the new user docs for recurring meetings

    - Mail should CC STA staff too

- Update superset dashboard

## v1.2 (**pending - work in progress**)

Various code and docs cleanups on moving to the next customer.

### Content

- Python moving to 3.14

- Tweaks to allow longer expiry time of credentials (issue #55)

### Upgrade process

- Rerun `scripts/lambdas.sh`

- Rebuild and push the code (`scripts/code_build.sh` and `scripts/code_push.sh`)
