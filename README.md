# HTCondor Pilot Job Router

Route HTCondor pilot jobs to a specific user.

## Install

    make install

Rename `/etc/default/htcondor-pilot-job-router.ini.example` to `/etc/default/htcondor-pilot-job-router.ini` and update values as needed.

## Configuration

The following configuration must be present for HTCondor-CE, typically placed in `/etc/condor-ce/config.d/99-local.conf`

    JOB_ROUTER.USE_PROCD = False
    PILOT_HOOK_TRANSLATE_JOB = /usr/libexec/htcondor-job-router/pilot-translate.py
    JOB_ROUTER_HOOK_KEYWORD = PILOT

For testing do not set `JOB_ROUTER_HOOK_KEYWORD` and instead submit jobs using `+HookKeyword = "PILOT"`.
