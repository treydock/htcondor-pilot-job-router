#!/usr/bin/env python

import logging, logging.handlers
import os, sys
import shlex
import json
import ConfigParser
import optparse
import classad
# Only needed for setuid hack
#import subprocess
#import pwd
from distutils.version import StrictVersion

SUCCESS = 0
FAILURE = 1
CONFIG_FILE = "/etc/default/htcondor-pilot-job-router.ini"
DEFAULT_CONFIG = {
    "grid_mapfile": "/etc/grid-security/grid-mapfile.local",
    "user_requests_json": "/var/tmp/htcondor-pilot-job-router/cms_user_requests.json",
    "ignore_users": "",
    "ignore_routes": "",
    "log_file": "/tmp/pilot-translate.log",
    "log_level": "INFO",
    "syslog_facility": "local0",
}
logger = logging.getLogger("htcondor-pilot-job-router")


def split_gridmap_line(value):
    '''
    Function to act like shlex.split() but handle single quotes inside double quoted values
    '''
    lex = shlex.shlex(value, posix=True)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)


def vanillaToGrid(ad, route_ad):
    '''
    Mimic the transformation performed by condor's VanillaToGrid::vanillaToGrid function which is not called
    when a hook is used.

    Modifications we need to make:
    https://github.com/htcondor/htcondor/blob/master/src/condor_job_router/VanillaToGrid.cpp#L33

    Constants defined here:
    https://github.com/htcondor/htcondor/blob/master/src/condor_includes/condor_attributes.h

    
    '''

    delete_attrs = [
        "ClusterId", "ProcId", "BufferBlockSize", "BufferSize", "CondorPlatform", "CondorVersion",
        "CoreSize", "GlobalJobId", "QDate", "RemoteWallClockTime", "ServerTime", "AutoClusterId",
        "AutoClusterAttrs", "StageInFinish", "StageInStart", "SUBMIT_Iwd"
    ]
    reset_float_attrs = [
        "RemoteUserCpu", "RemoteSysCpu", "LocalSysCpu", "LocalUserCpu"
    ]
    reset_int_attrs = [
        "ExitStatus", "CompletionDate", "NumCkpts", "NumRestarts", "NumSystemHolds", "CommittedTime",
        "CommittedSlotTime", "CumulativeSlotTime", "TotalSuspensions", "LastSuspensionTime",
        "CumulativeSuspensionTime", "CommittedSuspensionTime"
    ]

    for _attr in delete_attrs:
        if _attr in ad.keys(): del ad[_attr]
    for _attr in reset_float_attrs:
        ad[_attr] = 0.0
    for _attr in reset_int_attrs:
        ad[_attr] = 0

    ad["JobStatus"] = 1
    ad["ExitBySignal"] = False

    orig_universe = ad["JobUniverse"]
    route_universe = route_ad.get("TargetUniverse", 9)
    ad["JobUniverse"] = route_universe
    ad["Remote_JobUniverse"] = orig_universe

    if ad["JobUniverse"] == 9:
        if "CurrentHosts" in ad.keys(): del ad["CurrentHosts"]
        ad["GridResource"] = route_ad.get("GridResource")

    # TODO: https://github.com/htcondor/htcondor/blob/master/src/condor_job_router/VanillaToGrid.cpp#L147-L165

    return ad


def get_local_grid_map(dn, grid_mapfile):
    '''
    Get the user data from local grid-mapfile for a specific DN.

    Value returned is a list with grid-mapfile DN, FQAN and username.
    '''
    grid_mapfile = open(grid_mapfile, "r")
    grid_mapfile_lines = grid_mapfile.read().splitlines()
    grid_mapfile.close()

    local_grid_map = {}
    for line in grid_mapfile_lines:
        if line.startswith("#"):
            continue
        if not line:
            continue
        try:
            parts = split_gridmap_line(line)
        except:
            logger.error("Error parsing grid-mapfile line: %s", line)
            return None
        grid_map_dn = parts[0]
        grid_map_fqan = parts[1]
        local_username = parts[2]

        if grid_map_dn == dn:
            logger.debug("grid-mapfile match found DN='%s',FQAN='%s',USERNAME='%s'", grid_map_dn, grid_map_fqan, local_username)
            local_grid_map = {"dn": grid_map_dn, "username": local_username}
            break

    return local_grid_map


def get_pending_requests(data_file):
    data = {}
    if not os.path.isfile(data_file):
        logger.error("Pending job data file '%s' does not exist", data_file)
        return None
    with open(data_file) as f:
        data = json.load(f)
    logger.debug("Loaded pending requests:\n%s", json.dumps(data))

    return data


def mark_job_invalid(ad, jobid, reason):
    logger.error("Job=%s Invalid. Reason='%s', setting JobStatus=5.", jobid, reason)
    ad["JobStatus"] = 5
    ad["SITELocalUser"] = False
    ad["HoldReason"] = "Job invalid - %s" % reason
    print ad.printOld()
    return(FAILURE)
    #return(SUCCESS)


def setup_log(level, logfile, syslog_facility, debug):
    log_level = getattr(logging, level)
    logger.setLevel(log_level)
    logFormatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    if syslog_facility != "None":
        syslogHandler = logging.handlers.SysLogHandler(address="/dev/log", facility="local0") #getattr(logging.handlers.SysLogHandler.LOG_LOCAL0)
        syslogFormatter = logging.Formatter(fmt='%(name)s: [%(levelname)s] %(message)s')
        syslogHandler.setFormatter(syslogFormatter)
        logger.addHandler(syslogHandler)

    if debug:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        logger.addHandler(consoleHandler)


def get_config():
    config = {}
    conf = ConfigParser.ConfigParser(DEFAULT_CONFIG)
    conf.read(CONFIG_FILE)

    if not conf.has_section("hook"):
        conf.add_section("hook")

    config["grid_mapfile"] = conf.get("hook", "grid_mapfile")
    config["user_requests_json"] = conf.get("hook", "user_requests_json")
    config["ignore_users"] = filter(None, conf.get("hook", "ignore_users").split(","))
    config["ignore_routes"] = filter(None, conf.get("hook", "ignore_routes").split(","))
    config["log_file"] = conf.get("hook", "log_file")
    config["log_level"] = conf.get("hook", "log_level")
    config["syslog_facility"] = conf.get("hook", "syslog_facility")

    return config


def parse_opts():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--debug", help="Print log messages to console", default=False, action="store_true", dest="debug")

    opts, args = parser.parse_args()

    return opts


def main():
    opts = parse_opts()
    config = get_config()
    setup_log(level=config["log_level"], logfile=config["log_file"], syslog_facility=config["syslog_facility"], debug=opts.debug)

    route_ad = classad.ClassAd(sys.stdin.readline())
    #logger.debug("Route Ad: %s", route_ad.__str__())
    separator_line = sys.stdin.readline()
    try:
        assert separator_line == "------\n"
    except AssertionError:
        logger.error("Separator line was not second line of STDIN")
        return(FAILURE)
    try:
        ad = classad.parseOld(sys.stdin)
    except SyntaxError:
        logger.error("Unable to parse classad")
        return(FAILURE)
    # try:
    #     ad = classad.parse(input_classad)
    # except SyntaxError:
    #     try:
    #         ad = classad.parseOld(input_classad)
    #     except SyntaxError:
    #         logger.error("Unable to parse classad")
    #         return(FAILURE)

    # Set some variables based on incoming job ad
    jobid = "%s.%s" % (ad["ClusterId"], ad["ProcId"])

    # Perform transformations normally done by condor when a hook is not used
    # The version that fixes this is not yet defined so comparing against 9.9.9
    condor_version = classad.version()
    if StrictVersion(condor_version) < StrictVersion('9.9.9'):
        vanillaToGrid(ad, route_ad)

    # Test if job is a pilot
    #if "x509UserProxyFirstFQAN" in ad and "/local/Role=pilot" in ad.eval("x509UserProxyFirstFQAN"):
    if "x509UserProxyFirstFQAN" in ad and "/Role=pilot" in ad.eval("x509UserProxyFirstFQAN"):
        logger.debug("Job=%s x509UserProxyFirstFQAN='%s' is a pilot", jobid, ad["x509UserProxyFirstFQAN"])
        pilot_job = True
    else:
        logger.debug("Job=%s x509UserProxyFirstFQAN='%s' is not a pilot", jobid, ad.get("x509UserProxyFirstFQAN", "None"))
        pilot_job = False

    # TEST
    #if ad["Owner"] == "treydock":
    #    logger.error("Job=%s Invalid. Reason='TEST', setting JobStatus=5.", jobid)
    #    ad["JobStatus"] = 5
    #    ad["SITELocalUser"] = False
    #    ad["HoldReason"] = "Job invalid - TEST"
    #    print ad.printOld()
    #    return(SUCCESS)
    # END TEST

    # If not a pilot then return unmodified ad
    if not pilot_job:
        logger.debug("Job=%s is not a pilot job, returning ad", jobid)
        print ad.printOld()
        return(SUCCESS)

    # If owner or route are in ignore_users or ignore_routes then return unmodified ad
    if config["ignore_users"] and ad["owner"] in config["ignore_users"]:
        logger.debug("Job=%s Owner=%s is in ignore_users list, returning ad", jobid, ad["owner"])
        print ad.printOld()
        return(SUCCESS)
    if config["ignore_routes"] and route_ad["name"] in config["ignore_routes"]:
        logger.debug("Job=%s Route=%s is in ignore_routes list, returning ad", jobid, route_ad["name"])
        print ad.printOld()
        return(SUCCESS)

    # Get pending requests data
    pending_requests = get_pending_requests(data_file=config["user_requests_json"])

    # If unable to determine pending requests, mark job invalid
    if not pending_requests or "idle" not in pending_requests or "users" not in pending_requests:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="pending requests missing required data"))
    # If no idle users defined, mark job invalid
    idle_users = pending_requests["idle"]
    if not idle_users:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="pending requests contains no idle users"))
    # If no idle user DNs, mark job invalid
    pending_user_dns = pending_requests["users"]
    if not pending_user_dns:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="pending requests contains no user DNs"))

    # Get all users with idle jobs
    pending_users = {}
    for user, idle in idle_users.iteritems():
        if idle != 0:
            pending_users[user] = idle

    # If no pending user jobs, mark job invalid
    if not pending_users:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="no pending user jobs found"))

    # Determine which user to assign to the pilot
    # Priority: user with most idle jobs
    pending_user = sorted(pending_users, key=pending_users.get, reverse=True)[0]
    logger.debug("Pending users:\n%s", json.dumps(pending_users))
    logger.debug("Job=%s selected user to run job name=%s idle=%s", jobid, pending_user, pending_users[pending_user])

    # If the DN can't be found in the pending request JSON, job is invalid
    pending_user_dn = pending_user_dns.get(pending_user)
    if not pending_user_dn:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="unable to find pending user DN"))

    # The idle user selected is a CERN username, we need to map the associated DN to find local user
    local_grid_map = get_local_grid_map(dn=pending_user_dn, grid_mapfile=config["grid_mapfile"])
    if not local_grid_map:
        return(mark_job_invalid(ad=ad, jobid=jobid, reason="unable to get local gridmap information for DN='%s'" % pending_user_dn))
    new_owner = local_grid_map["username"]

    # Set USER_DN environment variable to new owner's DN
    if not ad["environment"] or ad["environment"] == "":
        new_environment = "USER_DN='%s'" % local_grid_map["dn"]
    else:
        new_environment = ad["environment"] + " USER_DN='%s'" % local_grid_map["dn"]

    # Get location of spooled files and change ownership
    #if "Iwd" in ad.keys():
    #    iwd = ad["Iwd"]
    #    if os.path.isdir(iwd):
    #        _pwd = pwd.getpwnam(new_owner)
    #        _uid = _pwd.pw_uid
    #        _gid = _pwd.pw_gid
    #        logger.debug("Modify permissions for Job=%s Set uid=%s gid=%s Iwd=%s", jobid, _uid, _gid, iwd)
    #        chown_wrapper_cmd = [
    #            os.path.join(os.path.dirname(os.path.realpath(__file__)), "chown_iwd"), str(_uid), str(_gid), iwd
    #        ]
    #        chown_wrapper_exit_code = subprocess.call(chown_wrapper_cmd)
    #        if chown_wrapper_exit_code != 0:
    #            return(mark_job_invalid(ad=ad, jobid=jobid, reason="chown wrapper failed with exit code %s" % chown_wrapper_exit_code))

    # Hack to replace arguments with values we can use
    #if "Arguments" in ad.keys():
    #    job_arguments = ad["Arguments"]
    #    if "-param_GLIDEIN_Glexec_Use OPTIONAL" in job_arguments:
    #        new_job_arguments = job_arguments.replace("-param_GLIDEIN_Glexec_Use OPTIONAL", "-param_GLIDEIN_Glexec_Use NEVER")
    #        logger.info("Update Job=%s set Arguments='%s'", jobid, new_job_arguments)
    #        ad["Arguments"] = new_job_arguments

    # Define remote_cerequirements to pass to submit script

    # Set new ad values
    logger.info("Update Job=%s set Owner=%s", jobid, new_owner)
    logger.info("Update Job=%s set Environment=\"%s\"", jobid, new_environment)
    ad["owner"] = new_owner
    ad["environment"] = new_environment

    #logger.debug("Route Ad:\n%s", route_ad.__str__())
    #logger.debug("Class Ad:\n%s", ad.printOld())
    print ad.printOld()
    return(SUCCESS)


if __name__ == '__main__':
    sys.exit(main())
