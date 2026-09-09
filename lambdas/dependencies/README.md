# Dependencies

Dependencies and utility code for the other lambda functions.

This dependency layer contains the `loneworker_utils.py` module, shared by `CheckFunction`, `ConnectFunction`, and `MetricsFunction`. Its main responsibilities are:

- Microsoft Graph authentication (acquiring and caching the application access token).

- Calendar I/O against the shared mailbox — reads via `/calendarView` (so recurring series are expanded into per-occurrence appointments) and PATCHes against the occurrence id.

- Category and appointment-body manipulation used to record check-in / check-out / missed / emergency state.

- The `LoneWorkerManager` helper that wraps logging, configuration, and CloudWatch metric emission shared by all three Lambdas.

- Phone-number-to-identity lookup (`phone_to_email`), used by `ConnectFunction` to work out who is calling.

## Phone number lookup

`phone_to_email` maps the number a caller is ringing from to the email addresses that identify them, in two stages.

**Stage one** asks Graph for an exact match: a `$filter` on `mobilePhone` across both the shared mailbox's contacts and the tenant's user accounts. A UK number is looked up in both its `+44` and `0` forms, so either may be stored.

**Stage two** runs only when stage one found nothing at all. It fetches the tenant's user accounts in a single request and compares each stored number with the calling number after reducing both to a canonical form, which ignores spaces, hyphens and non-breaking spaces. This is what lets a number typed as `07123 123456` still identify its owner, and it exists because Graph has no way to express "ignore the spacing" in a server-side filter.

For this second stage:

- **It covers user accounts only; contacts are not re-examined.** A contact's number can be corrected by any member of staff in seconds, whereas a lone worker cannot normally edit the `mobilePhone` on their own account — that needs an M365 administrator. Tolerance is worth most where self-service repair is unavailable. There may also be thousands of contacts but only dozens of staff.
- **Any exact match in stage one ends the lookup**, a contact's included. A contact created against the lone worker mailbox is taken to have been set up deliberately for that worker.

Stage two is bounded by a per-request timeout (`PHONE_FALLBACK_REQUEST_TIMEOUT_SECONDS`), and by Graph's own cap on how many users one request returns (`PHONE_FALLBACK_MAX_USERS`): if the tenant is too large, then it will fail and raise an exception. This is never expected to happen for a real tenant.

Note that this tolerance is a safety net for numbers that were entered wrongly. The instruction given to administrators in [the M365 setup guide](../../docs/m365.md#configure-mobile-phone-numbers) is deliberately more strict.
