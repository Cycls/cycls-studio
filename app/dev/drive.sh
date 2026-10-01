#!/bin/sh
# Send a JS function body to the running driver (driver.mjs) and print its JSON answer.
#   app/dev/drive.sh 'return await evalApp("__studio.state.status")'
#   app/dev/drive.sh - < app/dev/checks/drag.js
if [ "$1" = "-" ]; then curl -s --data-binary @- http://127.0.0.1:9400; else printf '%s' "$1" | curl -s --data-binary @- http://127.0.0.1:9400; fi
echo
