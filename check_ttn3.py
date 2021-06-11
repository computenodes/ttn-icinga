#!/usr/bin/env python3
"""
Use the TTS API to determine the status of a gateway
A simple wrapper to ttnctl to enable the status of gateways in
the things network https://www.thethingsnetwork.org/ to be monitored
using icinga/nagios

Author: Philip Basford
Date: 04/06/2021
Contact: P.J.Basford@soton.ac.uk

"""
from datetime import datetime, timedelta
import sys
import logging
import urllib.request
import argparse
import json
import pytz
import dateutil.parser

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN = 3

API_ENDPOINT = "/api/v3/gs/gateways/{}/connection/stats"
class TTNIcinga():
    """
        Class to use the TTS API endpoint to check when gateways were last heard from
    """
    def __init__(self, server, api_key, log_level=logging.WARN):
        self._logger = logging.getLogger("TTNIcinga")
        self._logger.setLevel(log_level)
        if api_key is None or api_key == "":
            raise ValueError("Must set api key")
        if server is None or server == "":
            raise ValueError("Must set server")
        self._server = server
        self._api_key = api_key
        self._logger.debug("API key: %s", api_key)
        self._logger.debug("Server: %s", server)

    def check_status(self, node_id, warning_time, critical_time):
        """
            Compares the last seen time of the specified node ID to
            the thresholds given
        """
        status = self.get_status(node_id)
        last_status = dateutil.parser.parse(status["last_status_received_at"])
        self._logger.debug("Gateway last status: %s", last_status)
        last_uplink = dateutil.parser.parse(status["last_uplink_received_at"])
        self._logger.debug("Gateway last uplink: %s", last_uplink)
        last_seen = max(last_uplink, last_status)
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        diff = now - last_seen
        self._logger.debug("Difference: %s", diff)
        if diff < timedelta(seconds=0):
            raise TtnCheckError("Last seen in the future")
        if diff < timedelta(seconds=warning_time):
            return (EXIT_OK, "OK: Last seen %s seconds ago"% diff.seconds)
        if diff > timedelta(seconds=critical_time):
            return (EXIT_CRITICAL, "CRITICAL: Not seen for %s seconds." % diff.seconds)
        if diff > timedelta(seconds=warning_time):
            return (EXIT_WARNING, "WARNING: Not seen for %s seconds." % diff.seconds)
        raise TtnCheckError("Shouldn't be possible to get here")

    def get_status(self, node_id):
        """
            Get all the status information from the API endpoint
        """
        request_path = API_ENDPOINT.format(node_id)
        url = "{}{}".format(self._server, request_path)
        self._logger.debug("URL: %s", url)
        headers = {}
        headers["Authorization"] = "Bearer {}".format(self._api_key)
        headers["Accept"] = "application/json"
        self._logger.debug(headers)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            if response.status != 200:
                self._logger.error("Status: %s", response.status)
                raise TtnCheckError("Unable to get data")
            result = response.read()
            data = json.loads(result)
            return data


class TtnCheckError(Exception):
    """
        Generic error for when things go wrong
    """


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
    PARSER.add_argument(
        "-s", "--server", type=str, action="store", required=True,
        help="The server to use as the API endpoing")
    PARSER.add_argument(
        "-k", "--key", type=str, action="store", required=True,
        help="The key for the API server")
    LOGGING_OUTPUT = PARSER.add_mutually_exclusive_group()
    LOGGING_OUTPUT.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress most ouput")
    LOGGING_OUTPUT.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Maximum verbosity output on command line")
    PARSER.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1")
    ARGS = PARSER.parse_args()
    LOG_LEVEL = logging.WARN
    if ARGS.quiet:
        LOG_LEVEL = logging.ERROR
    elif ARGS.verbose:
        LOG_LEVEL = logging.DEBUG
    FORMATTER = logging.Formatter(
        '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s')
    CONSOLE_HANDLER = logging.StreamHandler(sys.stderr)
    CONSOLE_HANDLER.setLevel(LOG_LEVEL)
    CONSOLE_HANDLER.setFormatter(FORMATTER)
    try:
        CLIENT = TTNIcinga(ARGS.server, ARGS.key, LOG_LEVEL)
        (STATUS, MESSAGE) = CLIENT.check_status(ARGS.gateway, ARGS.warning, ARGS.critical)
    except TtnCheckError as err:
        print(str(err))
        sys.exit(EXIT_UNKNOWN)
    print(MESSAGE)
    sys.exit(STATUS)
