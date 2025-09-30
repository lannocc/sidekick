#!/bin/bash

# refresh_tickets.sh
#
# This script refreshes all open tickets in the iosk/doc/dmx/ticket directory.
# It iterates through each T*.md file in that specific directory (ignoring
# subdirectories), extracts the ticket number, runs `sk ticket <number>`,
# and overwrites the file with the fresh output from the command. This helps
# keep the local ticket files in sync with the ticket database.

set -e

# Define the directory where open tickets are stored.
TICKET_DIR="iosk/doc/dmx/ticket"

# Check if the directory exists before proceeding.
if [ ! -d "$TICKET_DIR" ]; then
    echo "Error: Ticket directory not found at '$TICKET_DIR'"
    echo "Please run this script from the project root."
    exit 1
fi

echo "Starting to refresh open tickets in $TICKET_DIR..."

# Find files matching T*.md only in the specified directory, not in subdirectories.
# Loop through each found file path.
for ticket_file in "$TICKET_DIR"/T*.md; do
    # Ensure we only process actual files and not the glob pattern itself if no files match.
    [ -f "$ticket_file" ] || continue

    # Get the base filename from the full path (e.g., T123.md)
    filename=$(basename "$ticket_file")

    # Remove the '.md' suffix to get the ticket name (e.g., T123)
    base="${filename%.md}"

    # Remove the 'T' prefix to get just the ticket number (e.g., 123)
    ticket_num="${base#T}"

    # Validate that we have a numeric ticket number before proceeding.
    if [[ ! "$ticket_num" =~ ^[0-9]+$ ]]; then
        echo "Skipping invalid file name format: $filename"
        continue
    fi

    echo "Refreshing T${ticket_num} -> ${ticket_file}"

    # Run the `sk ticket` command with the extracted number and redirect
    # the output to overwrite the original markdown file.
    sk ticket "$ticket_num" > "$ticket_file"
done

echo "Ticket refresh complete."
