#!/usr/bin/env python3

import sys
import logging
import traceback
import json

from urllib.error import URLError, HTTPError

from k8s.components import MAPPINGS
from k8s.cli import parse_cmdline
from k8s.http import build_url, request
from k8s.consts import NAGIOS_MSG, NaemonState
from k8s.result import Output


def main():
    parsed = parse_cmdline(sys.argv[1:])

    if parsed.debug:
        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")

    health_check, is_core = MAPPINGS[parsed.resource]

    # Build URL using input arguments
    url = build_url(
        host=parsed.host,
        port=parsed.port,
        resource=parsed.resource,
        is_core=is_core,
        namespace=parsed.namespace
    )

    # Request and check health data
    try:
        response, status = request(url, token=parsed.token, insecure=parsed.insecure)
        output = health_check(response).output
        if not isinstance(output, Output):
            raise TypeError("Unknown health check format")
    except HTTPError as e:
        body = json.loads(e.read().decode("utf8"))
        output = Output(
            NaemonState.UNKNOWN,
            "{0}: {1}".format(e.code, body.get("message")),
            sys.stderr
        )
    except URLError as e:
        output = Output(NaemonState.UNKNOWN, e.reason, sys.stderr)
    except Exception as e:
        if parsed.debug:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, file=sys.stdout)

        output = Output(NaemonState.UNKNOWN, e, sys.stderr)

    msg = NAGIOS_MSG.format(state=output.state.name, message=output.message)
    output.channel.write(msg)
    sys.exit(output.state.value)


if __name__ == "__main__":
    main()
