#!/bin/bash

CONFIG="/etc/default/htcondor-pilot-job-router.ini"
LOCK_FILE="/var/lock/subsys/get-cms-user-requests"

if [ -f $CONFIG ]; then
  CONDOR_INSTALL=$(awk -F "=" '/^condor_install/ {print $2}' $CONFIG | tr -d ' ')
  USER_REQUESTS_JSON=$(awk -F "=" '/^user_requests_json/ {print $2}' $CONFIG | tr -d ' ')

  [ -z "$CONDOR_INSTALL" ] && CONDOR_INSTALL="system"
  [ -z "$USER_REQUESTS_JSON" ] && USER_REQUESTS_JSON="/var/tmp/htcondor-pilot-job-router/cms_user_requests.json"
else
  CONDOR_INSTALL="system"
  USER_REQUESTS_JSON="/var/tmp/htcondor-pilot-job-router/cms_user_requests.json"
fi

(
  flock -x -w 10 200
  [ $? -ne 0 ] && { echo "Cannot acquire lock"; exit 2; }

  [[ "x$CONDOR_INSTALL" == "xsystem" ]] || export PYTHONPATH=$CONDOR_INSTALL/lib/python:$PYTHONPATH
  [[ -d `dirname $USER_REQUESTS_JSON` ]] || mkdir `dirname $USER_REQUESTS_JSON`

  /usr/libexec/htcondor-pilot-job-router/get_user_requests.py 2>/dev/null 1>$USER_REQUESTS_JSON

) 200>$LOCK_FILE
retval=$?

exit $retval
