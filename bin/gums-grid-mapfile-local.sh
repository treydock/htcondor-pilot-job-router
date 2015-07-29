#!/bin/bash

CONFIG="/etc/default/htcondor-pilot-job-router.ini"
LOCK_FILE="/var/lock/subsys/gums-grid-mapfile-local"

if [ -f $CONFIG ]; then
  GRID_MAPFILE=$(awk -F "=" '/^grid_mapfile/ {print $2}' $CONFIG | tr -d ' ')

  [ -z "$GRID_MAPFILE" ] && GRID_MAPFILE="/etc/grid-security/grid-mapfile.local"
else
  GRID_MAPFILE="/etc/grid-security/grid-mapfile.local"
fi

(
  flock -x -w 10 200
  [ $? -ne 0 ] && { echo "Cannot acquire lock"; exit 2; }

  gums --host generateEmailMapfile --file $GRID_MAPFILE

) 200>$LOCK_FILE
retval=$?

exit $retval
