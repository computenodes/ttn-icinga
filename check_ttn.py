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
import dateutil.parser
import pytz

CMD_LINE = "/usr/local/bin/ttnctl"
STATUS_CMD = "gateways status"

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNONWN = 3

def check_status(node_id, warning_time, critical_time):
    """
        Compares the last seen time of the specified node ID to
        the thresholds given
    """
    status = _get_status(node_id)
    seen = status["Last seen"]
    last_seen = dateutil.parser.parse(seen[:35])
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    diff = now - last_seen
    print now
    print last_seen
    print diff
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
    if status == 0: #Double check exit status
        return _parse_status(output)

def _run_cmd(args):
    cmd = subprocess.Popen(
        args="%s %s" %(CMD_LINE, args),
        shell=True,
        stdout=subprocess.PIPE)
    exit_status = cmd.wait()
    if exit_status != 0:    #Failed to run happily
        raise TtnCheckError("Unknown: Command execution failed")
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
