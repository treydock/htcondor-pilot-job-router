#!/usr/bin/env python

import logging
import sys
import shlex
import classad

DEBUG = False
LOGFILE = "/tmp/pilot-translate.log"
SUCCESS = 0
FAILURE = 1
GRID_MAPFILE = "/etc/grid-security/grid-mapfile.local"

logger = logging.getLogger(__name__)
#logging_level = logging.DEBUG if DEBUG else logging.INFO
logging_level = logging.DEBUG
logger.setLevel(logging_level)
logFormatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

fileHandler = logging.FileHandler(LOGFILE)
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

if DEBUG:
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

def split_gridmap_line(value):
    lex = shlex.shlex(value, posix=True)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)

def get_user_dn(user):
    grid_mapfile = open(GRID_MAPFILE, "r")
    grid_mapfile_lines = grid_mapfile.read().splitlines()
    grid_mapfile.close()

    for line in grid_mapfile_lines:
        if line.startswith("#"):
            continue
        if not line:
            continue
        try:
            #parts = shlex.split(line)
            parts = split_gridmap_line(line)
        except:
            logger.error("Error parsing grid-mapfile line: %s", line)
            return(FAILURE)
        #print line
        #print parts
        dn = parts[0]
        fqan = parts[1]
        username = parts[2]
        if username != user:
            continue
        if fqan:
            #print "FQAN present: '%s' = %s" % (fqan, type(fqan))
            continue
        logger.debug("DN='%s',FQAN='%s',USERNAME='%s'", dn, fqan, username)
        return dn

def main():
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
    #         sys.stderr.write("Unable to parse classad")
    #         return(FAILURE)
    owner = ad["owner"]
    logger.debug("OWNER: %s", owner)
    user_dn = get_user_dn(owner)

    #if ad.get("HookKeyword"):
    #    logger.debug("Deleting HookKeyword")
    #    ad["HookKeyword"] = classad.Value.Undefined
    #    del ad["HookKeyword"]
    # Set USER_DN environment variable for job
    ad["environment"] += " USER_DN='%s'" % user_dn

    return_ad = ad.printOld()
    logger.debug("Class Ad:\n%s", return_ad)

    print return_ad

    return(SUCCESS)

if __name__ == '__main__':
    sys.exit(main())
