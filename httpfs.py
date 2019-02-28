import socket
import re
import os
from datetime import datetime

DIRNAME = os.path.dirname(__file__)
HOST = 'localhost'
DEFAULT_PORT = 8080
# Default folder is the one where httpfs.py is located (root folder)
DEFAULT_DIR = DIRNAME
BUFFER_SIZE = 4096 # in bytes
APP_NAME = 'httpfs'
COMMAND_QUIT = 'quit'
FLAG_VERBOSE = '-v'
FLAG_PORT = '-p'
FLAG_DIR_PATH = '-d'
VERB_GET = 'GET'
VERB_POST = 'POST'
# Will find command line flags and their parameters
REGEX_FLAGS = r"(?P<flag>-{1,2}\S*)(?:[=:]?|\s+)(?P<params>[^-\s].*?)?(?=\s+[-\/]|$)"
# Taken from https://stackoverflow.com/questions/6038061/regular-expression-to-find-urls-within-a-string
REGEX_URL = r"(http://)([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"
# Command regexes
REGEX_STARTS_WITH_APP_NAME = rf"^{APP_NAME}"
REGEX_NO_COMMAND = rf"^{APP_NAME}$"
REGEX_REQUEST = rf"^({VERB_GET}|{VERB_POST})\s+/([\w\./]+)*"

# TODO: Programatically set value
debug = True
statuses = {
    200: "OK",
    400: "BAD REQUEST",
    403: "FORBIDDEN",
    404: "NOT FOUND"
}

def print_debug_info(address, data):
    if not data:
        print(f'[{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT] {address} end transmission.')
        return
    print(f'[{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT] {address} sent:')
    print(f'{data}')

def handle_request(clientsocket, request):
    # First line of request contains which verb (GET/POST) and which directory/file
    match = re.search(REGEX_REQUEST, request)
    if match is None:
        if debug: 
            print('400 BAD REQUEST')
            print(request)
        response_str = write_response_headers(f'400 BAD REQUEST\r\n{request}\r\n\r\n', 400)
        response_bytes = bytes(response_str, encoding='ASCII')
        conn.sendall(response_bytes)
        return
    verb = match.group(1)
    path = match.group(2)
    if verb == VERB_GET:
        handle_get(clientsocket, path)
        return
    if verb == VERB_POST:
        body = get_request_body(request)
        handle_post(clientsocket, path, body)
        return
        
def handle_get(clientsocket, path):
    # Check that path is not outside server (application) root directory
    if path is not None and DIRNAME.lower() not in os.path.abspath(path).lower():
        response_str = write_response_headers('403 FORBIDDEN\r\n\r\n', 403)
        response_bytes = bytes(response_str, encoding='ASCII')
        clientsocket.sendall(response_bytes)
        return

    if path is None or os.path.isdir(path):
        contents = os.listdir(path)
        response_str = ''
        for f in contents:
            response_str += f + '\r\n'
        # Add another newline to denote end of response
        response_str += '\r\n'
        response_str = write_response_headers(response_str, 200)
        response_bytes = bytes(response_str, encoding='ASCII')
        clientsocket.sendall(response_bytes)
        return
    elif os.path.isfile(path):
        with open(path) as f:
            contents = f.read()
            contents += '\r\n\r\n'
            response_str = write_response_headers(contents, 200)
            response_bytes = bytes(response_str, encoding='ASCII')
            clientsocket.sendall(response_bytes)
            return
    else:
        if debug:
            print('404 NOT FOUND')
        response_str = write_response_headers('404 NOT FOUND\r\n\r\n', 404)
        response_bytes = bytes(response_str, encoding='ASCII')
        clientsocket.sendall(response_bytes)

def handle_post(clientsocket, path, body):

    return

def write_response_headers(response_str, status_code):
        # Prepend string with extra info for httpc's verbose flag
        response_str = f'Content-Length: {len(response_str)}\r\n\r\n{response_str}'
        response_str = f'Date: {datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT\r\n{response_str}'
        response_str = f'Content-Type: text/plain\r\n{response_str}'
        response_str = f'HTTP/1.0 {status_code} {statuses[status_code]}\r\n{response_str}'
        return response_str

def get_request_body(request):
    index = request.find('\r\n\r\n')    
    return request[index:].strip()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, DEFAULT_PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        with conn:
            while True:
                data = conn.recv(BUFFER_SIZE)
                if debug:
                    print_debug_info(addr, data)
                if not data:
                    # Going outside the loop will close the socket
                    break
                # TODO: Handle large requests (e.g. large files in post)
                request = data.decode('ASCII')
                handle_request(conn, request)