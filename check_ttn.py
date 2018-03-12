#!/usr/bin/env python
"""
A simple wrapper to ttnctl to enable the status of gateways in
the things network https://www.thethingsnetwork.org/ to be monitored
using icinga/nagios

Author: Philip Basford
Date: 17/07/2017
Contact: P.J.Basford@soton.ac.uk

"""
import subprocess
from datetime import datetime, timedelta
import argparse
import re
import pytz
import dateutil.parser

CMD_LINE = "/usr/local/bin/ttnctl"
CMD_ENV = {"HOME":"/var/lib/nagios", "USER": "nagios"}
STATUS_CMD = "gateways status"

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

def check_status(node_id, warning_time, critical_time):
    """
        Compares the last seen time of the specified node ID to
        the thresholds given
    """
    status = _get_status(node_id)
    seen_str = status["Last seen"]
    seen = seen_str[:re.search("[A-Z]", seen_str).start()]
    last_seen = dateutil.parser.parse(seen)
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    diff = now - last_seen
    if diff < timedelta(seconds=0):
        raise TtnCheckError("Last seen in the future")
    elif diff < timedelta(seconds=warning_time):
        return (EXIT_OK, "OK: Last seen %s seconds ago"% diff)
    elif diff > timedelta(seconds=critical_time):
        return (EXIT_CRITICAL, "CRITICAL: Not seen for %s seconds." % diff)
    elif diff > timedelta(seconds=warning_time):
        return (EXIT_WARNING, "WARNING: Not seen for %s seconds." % diff)
    else:
        raise TtnCheckError("Shouldn't be possible to get here")

def _get_status(node_id):
    (status, output) = _run_cmd("%s %s" % (STATUS_CMD, node_id))
    if status == 0:
        return _parse_status(output)
    else:    #something went wrong
        _parse_error(output)
        raise TtnCheckError("Unknown: Command execution failed")

def _parse_error(output):
    for line in output:
        if  line.find("Could not get status of gateway.") > 0:
            raise TtnCriticalError("CRTICAL: Gateway not found")


def _run_cmd(argumentss):
    cmd = subprocess.Popen(
        args="%s %s" %(CMD_LINE, argumentss),
        shell=True,
        env=CMD_ENV,
        stdout=subprocess.PIPE)
    exit_status = cmd.wait()
    output = cmd.communicate()[0]
    return exit_status, output.split("\n")

def _parse_status(output):
    data = {}
    for line in output:
        if line.startswith(" "):
            key = line[1:20].strip()
            value = line[22:].strip()
            data[key] = value
    return data


class TtnCheckError(Exception):
    """
        Generic error for when things go wrong
    """
    pass

class TtnCriticalError(Exception):
    """
        Used when early parsing of string means the output should be
        critical not unknown
    """
    pass

if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description="The Things Network gateway status checker")
    PARSER.add_argument(
        "-w", "--warning", type=int, action='store', required=True,
        help="The time to be disconnected for before generating a warning ")
    PARSER.add_argument(
        "-c", "--critical", type=int, action='store', required=True,
        help="The time to be disconnected for before being critical")
    PARSER.add_argument(
        "-g", "--gateway", type=str, action='store', required=True,
        help="The ID of the gateway to check")
    ARGS = PARSER.parse_args()
    try:
        (STATUS, MESSAGE) = check_status(ARGS.gateway, ARGS.warning, ARGS.critical)
    except TtnCheckError as err:
        print str(err)
        exit(EXIT_UNKNOWN)
    except TtnCriticalError as err:
        print str(err)
        exit(EXIT_CRITICAL)
    print MESSAGE
    exit(STATUS)
