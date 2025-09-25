# Diametrix (dmx) Command Exploration

This document serves as a personal log of exploration into the `dmx` command-line tool, as per instructions from `lannocc`.

## Overview
The `dmx` command is the main interface for interacting with the Diametrix Loan-Processing Application.

### Installed Version:
`dmx ver`: Installed version is 0.6.3

### Main `dmx` commands:
```
help - help for this program
ver - version information
db - database commands
web - web backend module
staging - staging for document upload batch processing
ai - artificial intelligence
mod - list modules
proc - list processors
test - test module
bank - banks
policy - policies
user - users
session - sessions
app - applications
doc - documents
profile - profile
issue - issues
```

## Subcommand: `dmx db`
The `dmx db` subcommand provides functionalities for database management.

### `dmx db` commands:
```
help - help for database commands
info - database information
backup - create a backup of the database and related data
restore - restore database and related data from backup
new - create a new database
list - list saved backups
```

## Subcommand: `dmx web`
The `dmx web` subcommand manages the web backend module.

### `dmx web` commands:
```
help - help for web commands
run - run the web process (backend)
dev - run the web process in developer mode (no security)
debug - debug enable / disable
alert - maintenance alert message
close - close connections and shut down at a specified time
status - show overall web status
```

## Subcommand: `dmx staging`
The `dmx staging` subcommand handles document upload batch processing.

### `dmx staging` commands:
```
help - help for staging commands
run - run the staging process
legend - display the legend
upload - uploads
step - steps
batch - batches
```

## Subcommand: `dmx ai`
The `dmx ai` subcommand provides artificial intelligence functionalities.

### `dmx ai` commands:
```
help - help for AI commands
prompt - prompt the AI
```

## Subcommand: `dmx mod`
The `dmx mod` subcommand lists available modules.

### `dmx mod` output:
```
  << Retrieving Modules...
    [10] Individual
    [20] Business
    [30] Farm/Ag
    [40] Consolidated
```

## Subcommand: `dmx proc`
The `dmx proc` subcommand lists processors for a given module. It requires a module ID as an argument.

### `dmx proc` exploration:
- `dmx proc help` resulted in an error (`ValueError: invalid literal for int() with base 10: 'help'`), indicating it expects a module ID.
- `dmx proc` without arguments prompted for input, leading to an `EOFError`.
- `dmx proc 10` (for 'Individual' module) successfully listed processors.

### `dmx proc 10` output:
```
  << Retrieving Processors...
    [0] No-Processor
    [10] Bank Statement
    [20] Pay Slip
    [1002] IRS W-2
    [1040] IRS 1040
    [1041] IRS 1040 SCH 1
    [1042] IRS 1040 SCH A
    [1044] IRS 1040 SCH C
    [1045] IRS 1040 SCH D
    [1046] IRS 1040 SCH E
    [1047] IRS 1040 SCH F
    [1077] IRS 1065 SCH K-1
    [1151] IRS 1120-S SCH K-1
    [4835] IRS 4835
    [10000] Credit Report
```

## Subcommand: `dmx test`
The `dmx test` subcommand generates test data.

### `dmx test` commands:
```
help - help for test commands
policy - generate some test policies
user - generate some test users
app - generate some test applications
```

<h2>Subcommand: `dmx bank`</h2>
The `dmx bank` subcommand manages bank entities.

<h3>`dmx bank` commands:</h3>
```
help - help for bank commands
create - create a bank
delete - delete a bank (only if it has no references)
list - list banks
```

<h2>Subcommand: `dmx policy`</h2>
The `dmx policy` subcommand manages loan policies.

<h3>`dmx policy` commands:</h3>
```
help - help for policy commands
create - create a policy
delete - permamently delete a policy
list - list policies
```

<h2>Subcommand: `dmx user`</h2>
The `dmx user` subcommand manages user accounts.

<h3>`dmx user` commands:</h3>
```
help - help for user commands
create - create a user
delete - delete a user (only if it has no references)
list - list users
```

<h2>Subcommand: `dmx session`</h2>
The `dmx session` subcommand manages user sessions.

<h3>`dmx session` commands:</h3>
```
help - help for session commands
open - start a new session (log in)
close - close a session (log out)
list - list active sessions
```

<h2>Subcommand: `dmx app`</h2>
The `dmx app` subcommand manages loan applications.

<h3>`dmx app` commands:</h3>
```
help - help for application commands
reset - delete ALL applications
create - start a new application
delete - permanently delete an application
show - show application details
list - list open applications
```

<h2>Subcommand: `dmx doc`</h2>
The `dmx doc` subcommand manages documents attached to applications.

<h3>`dmx doc` commands:</h3>
```
help - help for document commands
debug - feed a file to a processor and see retrieved data
attach - attach input document to application
show - show data for attached document
remove - logically remove attached document
delete - permanently delete attached document
list - list attached documents
```

<h2>Subcommand: `dmx profile`</h2>
The `dmx profile` subcommand manages application profiles.

<h3>`dmx profile` commands:</h3>
```
help - help for profile commands
tree - show the (module) profile layout
new - create new (app) profile list item
delete - delete (app) profile list item
show - display the (app) profile data
checksum - compute the profile checksum (integrity key)
```

<h2>Subcommand: `dmx issue`</h2>
The `dmx issue` subcommand manages open issues.

<h3>`dmx issue` commands:</h3>
```
help - help for issue commands
list - list open issues
```
