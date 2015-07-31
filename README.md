# HTCondor Pilot Job Router

Route HTCondor pilot jobs to a specific user.

## Install

    make install

Rename `/etc/default/htcondor-pilot-job-router.ini.example` to `/etc/default/htcondor-pilot-job-router.ini` and update values as needed.

## Configuration

The following configuration must be present for HTCondor-CE, typically placed in `/etc/condor-ce/config.d/99-local.conf`

    JOB_ROUTER.USE_PROCD = False
    PILOT_HOOK_TRANSLATE_JOB = /usr/libexec/htcondor-pilot-job-router/pilot-translate.py
    JOB_ROUTER_HOOK_KEYWORD = PILOT

For testing do not set `JOB_ROUTER_HOOK_KEYWORD` and instead submit jobs using `+HookKeyword = "PILOT"`.

The existing `JOB_ROUTER_ENTRIES` must sandbox the pilot jobs that are going to be translated.  This is an example of an attribute to add to the `JOB_ROUTER_ENTRIES` that will be applied to the incoming pilot jobs.

    JobShouldBeSandboxed = regexp("\/Role\=pilot", TARGET.x509UserProxyFirstFQAN);
