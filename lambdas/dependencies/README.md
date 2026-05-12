# Dependencies

Dependencies and utility code for the other lambda functions.

This dependency layer contains the `loneworker_utils.py` module, shared by `CheckFunction`, `ConnectFunction`, and `MetricsFunction`. Its main responsibilities are:

- Microsoft Graph authentication (acquiring and caching the application access token).

- Calendar I/O against the shared mailbox — reads via `/calendarView` (so recurring series are expanded into per-occurrence appointments) and PATCHes against the occurrence id.

- Category and appointment-body manipulation used to record check-in / check-out / missed / emergency state.

- The `LoneWorkerManager` helper that wraps logging, configuration, and CloudWatch metric emission shared by all three Lambdas.
