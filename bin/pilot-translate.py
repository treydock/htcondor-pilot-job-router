#!/usr/bin/env python

import logging
import sys
import shlex
import ConfigParser
import optparse
import classad
from distutils.version import StrictVersion

SUCCESS = 0
FAILURE = 1
CONFIG_FILE = "/etc/default/htcondor-pilot-job-router.ini"
DEFAULT_CONFIG = {
    "grid_mapfile": "/etc/grid-security/grid-mapfile.local",
    "log_file": "/tmp/pilot-translate.log",
    "log_level": "INFO",
}
logger = logging.getLogger(__name__)


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
        "AutoClusterAttrs", "StageInFinish", "StageInStart"
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

    #if "ClusterId" in ad.keys(): del ad["ClusterId"]
    #if "ProcId" in ad.keys(): del ad["ProcId"]
    #if "BufferBlockSize" in ad.keys(): del ad["BufferBlockSize"]
    #if "BufferSize" in ad.keys(): del ad["BufferSize"]
    #if "CondorPlatform" in ad.keys(): del ad["CondorPlatform"]
    #if "CondorVersion" in ad.keys(): del ad["CondorVersion"]
    #if "CoreSize" in ad.keys(): del ad["CoreSize"]
    #if "GlobalJobId" in ad.keys(): del ad["GlobalJobId"]
    #if "QDate" in ad.keys(): del ad["QDate"]
    #if "RemoteWallClockTime" in ad.keys(): del ad["RemoteWallClockTime"]
    #if "ServerTime" in ad.keys(): del ad["ServerTime"]
    #if "AutoClusterId" in ad.keys(): del ad["AutoClusterId"]
    #if "AutoClusterAttrs" in ad.keys(): del ad["AutoClusterAttrs"]
    #if "StageInFinish" in ad.keys(): del ad["StageInFinish"]
    #if "StageInStart" in ad.keys(): del ad["StageInStart"]

    ad["JobStatus"] = 1
    #ad["RemoteUserCpu"] = 0.0
    #ad["RemoteSysCpu"] = 0.0
    #ad["ExitStatus"] = 0
    #ad["CompletionDate"] = 0
    #ad["LocalSysCpu"] = 0.0
    #ad["LocalUserCpu"] = 0.0
    #ad["NumCkpts"] = 0
    #ad["NumRestarts"] = 0
    #ad["NumSystemHolds"] = 0
    #ad["CommittedTime"] = 0
    #ad["CommittedSlotTime"] = 0
    #ad["CumulativeSlotTime"] = 0
    #ad["TotalSuspensions"] = 0
    #ad["LastSuspensionTime"] = 0
    #ad["CumulativeSuspensionTime"] = 0
    #ad["CommittedSuspensionTime"] = 0
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


def get_user_dn(user, grid_mapfile):
    grid_mapfile = open(grid_mapfile, "r")
    grid_mapfile_lines = grid_mapfile.read().splitlines()
    grid_mapfile.close()

    for line in grid_mapfile_lines:
        if line.startswith("#"):
            continue
        if not line:
            continue
        try:
            parts = split_gridmap_line(line)
        except:
            logger.error("Error parsing grid-mapfile line: %s", line)
            return(FAILURE)
        dn = parts[0]
        fqan = parts[1]
        username = parts[2]
        if username != user:
            continue
        # Skip if FQAN is present as local mappings tend to not have FQAN
        if fqan:
            continue
        logger.debug("DN='%s',FQAN='%s',USERNAME='%s'", dn, fqan, username)
        return dn


def setup_log(level, logfile, debug):
    log_level = getattr(logging, level)
    logger.setLevel(log_level)
    logFormatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)

    if debug:
        logger.addHandler(consoleHandler)


def get_config():
    config = {}
    conf = ConfigParser.ConfigParser(DEFAULT_CONFIG)
    conf.read(CONFIG_FILE)

    if not conf.has_section("hook"):
        conf.add_section("hook")

    config["grid_mapfile"] = conf.get("hook", "grid_mapfile")
    config["log_file"] = conf.get("hook", "log_file")
    config["log_level"] = conf.get("hook", "log_level")

    return config


def parse_opts():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--debug", help="Print log messages to console", default=False, action="store_true", dest="debug")

    opts, args = parser.parse_args()

    return opts


def main():
    opts = parse_opts()
    config = get_config()
    setup_log(level=config["log_level"], logfile=config["log_file"], debug=opts.debug)

    route_ad = classad.ClassAd(sys.stdin.readline())
    logger.debug("Route Ad: %s", route_ad.__str__())
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

    # Determine routed job's owner
    new_owner = ad["owner"]
    logger.debug("Update Job=%s change Owner from %s to %s", jobid, ad["owner"], new_owner)

    # Get new owner's DN and for USER_DN environment variable
    user_dn = get_user_dn(new_owner, grid_mapfile=config["grid_mapfile"])
    if not ad["environment"] or ad["environment"] == "":
        new_environment = "USER_DN='%s'" % user_dn
    else:
        new_environment = ad["environment"] + " USER_DN='%s'" % user_dn

    # Set new ad values
    logger.info("Update Job=%s set Owner=%s", jobid, new_owner)
    logger.info("Update Job=%s set Environment=%s", jobid, new_environment)
    ad["owner"] = new_owner
    ad["environment"] = new_environment


    # Perform transformations normally done by condor when a hook is not used
    # The version that fixes this is not yet defined so comparing against 9.9.9
    condor_version = classad.version()
    if StrictVersion(condor_version) < StrictVersion('9.9.9'):
        vanillaToGrid(ad, route_ad)

    return_ad = ad.printOld()
    logger.debug("Class Ad:\n%s", return_ad)

    print return_ad

    return(SUCCESS)


if __name__ == '__main__':
    sys.exit(main())
