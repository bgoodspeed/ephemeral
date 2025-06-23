import http.server
import logging

logging.basicConfig(filename='/scripts/80.log', level=logging.DEBUG, format='%(message)s')

class LoggingHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def base_log_msg(self, verb):
        return f"{self.log_date_time_string()}|{self.address_string()}|{verb} {self.path}| "

    def do_GET(self):
        log_msg = f"{self.base_log_msg('GET')}"
        logging.info(log_msg)
        super().do_GET()

    def do_POST(self):
        log_msg = f"{self.base_log_msg('POST')}"
        logging.info(log_msg)
        super().do_GET()

httpd = http.server.HTTPServer(('0.0.0.0', 80), LoggingHTTPRequestHandler)
httpd.serve_forever()

