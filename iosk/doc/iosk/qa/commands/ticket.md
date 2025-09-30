# /bin/ticket.py
**Description:** View ticket details from the database.
**Usage:** `/bin/ticket.py <ticket-number>`
**Example:** `/bin/ticket.py 1`
**Output:**
```
# Ticket T1

- Status: **open**

## Description

Take the HTML and JavaScript demos that are currently running at https://join.lanno.cc and develop a custom videoconferencing experience from them.

## Comments

Find the sources in rEBUILD (`lannocc-web/join`)
```
**Status:** Working.

# /bin/ticket.py
**Description:** Attempts to view details for a non-existent ticket.
**Usage:** `/bin/ticket.py <non-existent-ticket-number>`
**Example:** `/bin/ticket.py 999`
**Output:** `!! ticket: Ticket T999 not found`
**Status:** Working (error handling).
