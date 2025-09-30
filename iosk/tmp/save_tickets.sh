#!/bin/bash
# Script to save remaining tickets from 34 to 400
for i in $(seq 34 400); do
    echo $i
    sk ticket $i > doc/dmx/ticket/T${i}.md
done
