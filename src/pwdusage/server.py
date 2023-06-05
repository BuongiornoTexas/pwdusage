#!/usr/bin/env python
# Usage Engine Proxy Server Tool for Powerwall-Dashboard
# -*- coding: utf-8 -*-
"""
 Python module providing usage data proxy for Powerwall-Dashboard.

 Author: Buongiorno Texas
 For more information see https://github.com/jasonacox/Powerwall-Dashboard and
 https://github.com/BuongiornoTexas/PW-Dashboard-usage-proxy.

 Usage Engine Proxy Server
    This server will pull energy use data from the Powerwall-Dashboard Influx Database
    and process it into energy usage data matching utility usage plans.
"""
# cspell: ignore levelname simplejson pwdusage
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import simplejson  # type: ignore
import ssl
from importlib.metadata import version

from pwdusage.common import log, PACKAGE
from pwdusage.engine import UsageEngine
from logging import DEBUG as LOG_DEBUG

HTTP_GET_ERROR = "GET Error."
HTTP_PUT_ERROR = "PUT Error."
HTTPS = "HTTPS"
HTTP = "HTTP"

class handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: tuple[Any]) -> None:
        log.debug("%s %s" % (self.address_string(), format % args))

    def address_string(self) -> str:
        # replace function to avoid lookup delays
        host, host_port = self.client_address[:2]
        return host

    def do_GET(self) -> None:
        contenttype = "application/json"
        message = simplejson.dumps(HTTP_GET_ERROR)

        if self.path == "/usage_engine":
            try:
                # As a side effect of this, (re)-load usage engine configuration.
                UsageEngine.reload_config()
                # Response of 200 used by grafana to validate usage engine is working.
                # Also provide message to check on web page.
                self.send_response(200)
                message = simplejson.dumps(
                    {"Usage Engine Status": "Engine OK, tariffs (re)loaded"}
                )
            except Exception as err:
                # Trap errors and provide some debugging information.
                self.send_response(
                    599, "Error loading usage engine configuration file."
                )
                log.error("Error loading usage engine configuration file.")
                log.error(f"Details: {err}")
                message = simplejson.dumps(
                    {
                        "Usage Engine Status": f"599 Error loading usage engine configuration file ({err})."
                    }
                )

        else:
            # Everything else - return a 404.
            self.send_response(404)
            # This is a hack, as I'm not going to learn how to pass an HTML formatted
            # message.
            message = simplejson.dumps(
                [
                    "Invalid page request. ",
                    "Usage engine API URL must be <host address>:port/usage_engine.",
                    f"Got {self.path}.",
                ]
            )

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
        d_len = int(self.headers.get("content-length"))  # type: ignore[arg-type]
        request_content = simplejson.loads(self.rfile.read(d_len).decode("utf-8"))

        # PUT code will fail silently. User will need to debug via logs or use curl
        # for more detail.
        message = simplejson.dumps(HTTP_PUT_ERROR)
        contenttype = "application/json"

        if self.path == "/usage_engine/metrics":
            self.send_response(200)
            message = UsageEngine.metrics()

        elif self.path == "/usage_engine/query":
            try:
                payload = request_content["targets"][0]["payload"]
            except KeyError:
                payload = None

            try:
                # finally, we actually instantiate a usage engine to return content.
                message = UsageEngine().usage(
                    start_utc=request_content["range"]["from"],
                    stop_utc=request_content["range"]["to"],
                    payload=payload,
                    request_content=request_content,
                )
                self.send_response(200)
            except Exception as err:
                # trap all errors so that we don't crash the server.
                log.error("Error getting usage [do_POST].")
                log.error(f"Details: {err}")
                self.send_response(599, f"Usage engine - metric query error.")
                message = simplejson.dumps(
                    {"Usage Engine Status": f"Error getting usage ({err})."}
                )
        else:
            self.send_response(599)
            message = simplejson.dumps(f"Usage engine - unknown url '{self.path}'.")

        # Send headers and payload
        try:
            self.send_header("Content-type", contenttype)
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(bytes(message, "utf8"))
        except:
            log.error("Socket broken sending response [doPOST]")


if __name__ == "__main__":
    # Configuration for usage proxy - Check for environmental variables
    # and always use those if available (required for Docker)
    port = int(os.getenv("USAGE_PORT", "9050"))

    match os.getenv("USAGE_HTTPS", "no"):
        case "yes", "https", "HTTPS":
            # run https mode with self-signed cert
            http_type = HTTPS
        case _:
            http_type = HTTP

    log.info(
        "Powerwall-Dashboard usage proxy server [%s] - %s Port %d"
        % (version(PACKAGE), http_type, port)
    )

    if os.getenv("USAGE_DEBUG", "no") == "yes":
        log.setLevel(LOG_DEBUG)
        log.debug("Debugging active.")

    with ThreadingHTTPServer(
        (os.getenv("USAGE_BIND_ADDRESS", ""), port), handler
    ) as server:
        if http_type == HTTPS:
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

        log.info("Powerwall-Dashboard usage engine proxy Started")
        try:
            server.serve_forever()
        except:
            print(" CANCEL \n")

        log.info("Powerwall-Dashboard usage proxy Stopped")
        os._exit(0)
