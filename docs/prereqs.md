# Prerequisites

You must have done all the following before you start installation of the software application.

1. [Set up an AWS subscription to use](#aws-subscription)

2. [Set up an M365 mailbox with appropriate client configuration](#m365-account)

3. [Created the configuration files](#config-files)

All processes documented here are assumed to run using the Linux command line, and depend on the following tools being installed.

- Python 3.14 specifically, with the `venv` module, and `python3` on your `PATH` resolving to it. The required version is pinned in [`config/global_config.sh`](../config/global_config.sh) and checked automatically by `scripts/check_python.sh`.

- An x86_64 build host. The lambdas are deployed as `x86_64`. `code_build.sh` explicitly targets `manylinux2014_x86_64` wheels when installing dependencies, so this is enforced automatically rather than relying on the host's own architecture matching.

- The AWS CLI

- Various command line tools including `bash`, `sed`, `awk`, and `jq`.

### A note for Windows users

[WSL](https://learn.microsoft.com/en-us/windows/wsl/) gives you a genuine Linux environment, and the instructions above should work as-is there. Running via Git Bash with native Windows Python (i.e. *not* WSL) also works, but needs a few things WSL doesn't:

- `jq` and `zip` are not installed by default (available via [Scoop](https://scoop.sh/) - `scoop install jq zip`).
- any `aws` command whose argument starts with a single `/` (e.g. `aws ssm get-parameter --name /loneworker/config`) needs `MSYS_NO_PATHCONV=1` set first, since Git Bash otherwise silently rewrites that argument into a Windows path before `aws` ever sees it.
- watch out for `python3` resolving to the wrong interpreter. Windows ships a `python3` [app execution alias](https://learn.microsoft.com/en-us/windows/apps/desktop/manage-app-execution-aliases) that can silently shadow a real install with an unrelated (often older) Python version - `command -v python3` and `python3 --version` are worth checking explicitly before relying on `scripts/check_python.sh` to catch a mismatch. Installing the pinned version via Scoop (`scoop install python`) puts its own `python3` shim ahead of the Windows one on `PATH`.

### A note for AWS CloudShell users

CloudShell is a convenient alternative to a local machine - no local install needed for most of the prerequisites above - but AWS updates its default Python version over time and doesn't publish a fixed number for it, so don't assume what it currently is; check with `python3 --version` first. Unless it happens to exactly match the version pinned in `config/global_config.sh`, `scripts/check_python.sh` will refuse to run until a matching Python is installed. Two things about CloudShell's environment matter for how you do that:

- Only your **home directory persists between sessions** - anything a package manager installs elsewhere is wiped when the session ends and has to be reinstalled next time, and the same applies to *active session settings* (shell exports, etc. that aren't saved into a file under `$HOME` like `.bashrc`) - those need reloading every session too, not just files outside `$HOME`.
- Persistent storage is limited to **1 GB total**, so this isn't the place to install much beyond what's needed here.

The standard way to get a specific Python version on Amazon Linux is [pyenv](https://github.com/pyenv/pyenv), which builds Python from source into your home directory - so the build itself survives across sessions, even though the compiler and libraries used to build it don't.

- Install the build dependencies (needed once per session, since these land outside `$HOME`; if a package name below has changed on CloudShell's current Amazon Linux version, `dnf search <name>` will find the current equivalent):

    ~~~bash
    sudo dnf install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel
    ~~~

- Install pyenv itself and load it into your shell (this only needs doing once - pyenv installs into `$HOME/.pyenv`, so it persists):

    ~~~bash
    curl https://pyenv.run | bash
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    source ~/.bashrc
    ~~~

- Find and install the pinned version (match this to whatever [`config/global_config.sh`](../config/global_config.sh) currently pins - substitute the exact patch version pyenv lists):

    ~~~bash
    pyenv install --list | grep '^  3\.14'
    pyenv install 3.14.<patch>
    pyenv global 3.14.<patch>
    python3 --version
    ~~~

Since `$HOME/.pyenv` and the `.bashrc` lines both persist, the pinned Python is available automatically in future CloudShell sessions without repeating the pyenv install step - only the `dnf install` step needs rerunning if you ever need to rebuild it.

*This sequence is based on general Amazon Linux / pyenv guidance rather than something run against this project's exact scripts on CloudShell - if a step doesn't match what you see, that's worth fixing here rather than working around silently.*

## AWS account

This depends on an AWS account (subscription). It's normally best to use a dedicated account. The AWS CLI must be configured with the correct environment variables to log into that account.

## M365 account

You must have an M365 business or enterprise tenant to use. If you do not have such a tenant, for test purposes you can sign up for a [free M365 tenant as a non-profit](https://www.microsoft.com/en-gb/microsoft-365/nonprofit/), or failing that just create a [new paid tenant](https://www.microsoft.com/en-gb/microsoft-365/business/microsoft-365-plan-chooser) (which is free for a couple of months).

Full instructions for how to perform this process are given in the [M365 instructions](m365.md), which is intended to be suitable to give to the M365 administrator. This process will give you:

1. Tenant GUID

2. Email address (the shared mailbox has no password of its own - the app authenticates via the ClientID/ClientSecret below, not by signing in to the mailbox)

3. ClientID for the app registration

4. ClientSecret and expiry date for the app registration

These will be needed to enter into Parameter Store when the [AWS Application is configured](creation.md#update-secrets).

### Testing the client credentials

Once you have set up all of the M365 tenant information, it is very useful to test it all in isolation. Full instructions for how to validate your credentials are in [the test guide here](testing.md#validating-credentials).

## Config files

You need to create two configuration files for your deployment. Assuming your organisation is called `mycharity`, then you should probably create config files called `mycharity_env.sh` and `mycharity.yaml`.

- There is a YAML document with various parameters in it. An example of this is [`example.yaml` in the config directory](../config/example.yaml).

    - Copy this file to create one called `mycharity.yaml` in the `config` directory.

    - Edit it appropriately following the instructions; for most things the defaults are fine, but you'll need to configure email addresses for emergency mails. *These email addresses are the only thing in config files that might be confidential; if so, then you should not check the yaml file in and store it elsewhere.*

- There is a shell script with further parameters that is sourced before running any of the bash commands. An example of this is [`example_env.sh` in the config directory](../config/example_env.sh).

    - Copy this file to create one called `mycharity_env.sh` in the `config` directory.

    - Edit the fields as appropriate. Many will be able to just use the defaults, but you should at least change your `AWS_PROFILE` value, and the name of your config file (`mycharity.yaml` in this example).
