#!/usr/bin/env python
# Usage Engine Proxy Server Tool for Powerwall-Dashboard
# -*- coding: utf-8 -*-
"""
 Python module providing usage data proxy for Powerwall-Dashboard.

 Author: Buongiorno Texas
 For more information see https://github.com/jasonacox/Powerwall-Dashboard and
 https://github.com/BuongiornoTexas/Powerwall-Dashboard-usage-proxy.

 Usage Engine Proxy Server
    This server will pull energy use data from the Powerwall-Dashboard Influx Database
    and process it into energy usage data matching utility usage plans.
"""
# cspell: ignore levelname simplejson
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import simplejson  # type: ignore
import logging

import ssl

from engine import UsageEngine

BUILD = "v0.9"

# Configuration for Proxy - Check for environmental variables
#    and always use those if available (required for Docker)
bind_address = os.getenv("USAGE_BIND_ADDRESS", "")
debug_mode = os.getenv("USAGE_DEBUG", "no")
https_mode = os.getenv("USAGE_HTTPS", "no")
port = int(os.getenv("USAGE_PORT", "9050"))

if https_mode == "yes":
    # run https mode with self-signed cert
    cookie_suffix = "path=/;SameSite=None;Secure;"
    http_type = "HTTPS"
elif https_mode == "http":
    # run http mode but simulate https for proxy behind https proxy
    cookie_suffix = "path=/;SameSite=None;Secure;"
    http_type = "HTTP"
else:
    # run in http mode
    cookie_suffix = "path=/;"
    http_type = "HTTP"

# Logging
log = logging.getLogger("proxy")
logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
log.setLevel(logging.INFO)

if debug_mode == "yes":
    log.info(
        "Powerwall-Dashboard usage proxy Server [%s] - %s Port %d - DEBUG"
        % (BUILD, http_type, port)
    )
    log.setLevel(logging.DEBUG)
else:
    log.info(
        "Powerwall-Dashboard usage proxy Server [%s] - %s Port %d"
        % (BUILD, http_type, port)
    )
log.info("Powerwall-Dashboard usage engine proxy Started")


class handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: tuple[Any]) -> None:
        if debug_mode == "yes":
            log.debug("%s %s" % (self.address_string(), format % args))
        else:
            pass

    def address_string(self) -> str:
        # replace function to avoid lookup delays
        host, host_port = self.client_address[:2]
        return host

    def do_GET(self) -> None:
        self.send_response(200)
        message = "ERROR!"
        contenttype = "application/json"

        if self.path == "/usage_engine":
            # Response of 200 used by grafana to validate
            # usage engine is working. Dummy message to check on
            # web page.
            try:
                # As a side effect of this, (re)-load usage engine configuration.
                UsageEngine.reload_config()
                message = simplejson.dumps(
                    {"Usage Engine Status": "Engine OK, tariffs (re)loaded"}
                )
            except Exception as err:
                # trap all errors so that we don't crash the server.
                log.error("Error loading tariffs [doGET].")
                log.error(f"Details: {err}")
                message = simplejson.dumps(
                    {"Usage Engine Status": f"Error loading tariffs ({err})."}
                )

        else:
            # Everything else - do nothing
            pass

        # Count
        if message is None:
            message = "TIMEOUT!"
        elif message == "ERROR!":
            message = "ERROR!"

        # Send headers and payload
        try:
            self.send_header("Content-type", contenttype)
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(bytes(message, "utf8"))
        except:
            log.error("Socket broken sending response [doGET]")

    def do_POST(self) -> None:
        # do_POST usage engine elements should be duplicated
        # in the test server.
        d_len = int(self.headers.get("content-length")) # type: ignore[arg-type]
        request_content = simplejson.loads(self.rfile.read(d_len).decode("utf-8"))

        self.send_response(200)
        message = "ERROR!"
        contenttype = "application/json"

        if self.path == "/usage_engine/metrics":
            message = UsageEngine.metrics()

        elif self.path == "/usage_engine/query":
            try:
                # finally, we actually instantiate a usage engine to return content.
                message = UsageEngine().usage(request_content)
            except Exception as err:
                # trap all errors so that we don't crash the server.
                log.error("Error getting usage [do_POST].")
                log.error(f"Details: {err}")
                message = simplejson.dumps(
                    {"Usage Engine Status": f"Error getting usage ({err})."}
                )

        if message is None:
            message = "do_POST TIMEOUT!"
        elif message == "ERROR!":
            message = "do_POST Unknown ERROR!"

        # Send headers and payload
        try:
            self.send_header("Content-type", contenttype)
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(bytes(message, "utf8"))
        except:
            log.error("Socket broken sending response [doPOST]")


with ThreadingHTTPServer((bind_address, port), handler) as server:
    if https_mode == "yes":
        # Activate HTTPS
        log.debug("Activating HTTPS")
        server.socket = ssl.wrap_socket(
            server.socket,
            certfile=os.path.join(os.path.dirname(__file__), "localhost.pem"),
            server_side=True,
            ssl_version=ssl.PROTOCOL_TLSv1_2,
            ca_certs=None,
            do_handshake_on_connect=True,
        )

    try:
        server.serve_forever()
    except:
        print(" CANCEL \n")

    log.info("Powerwall-Dashboard usage proxy Stopped")
    os._exit(0)
