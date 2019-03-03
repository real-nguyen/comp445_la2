import socket
import re
from sys import exit
from datetime import datetime
from os import listdir
from os import chdir
from os.path import abspath
from os.path import join
from os.path import isdir
from os.path import isfile
from os.path import dirname

HOST = 'localhost'
DEFAULT_PORT = 8080
# Default folder is the one where httpfs.py is located (root folder)
DEFAULT_DIR = dirname(__file__)
BUFFER_SIZE = 4096 # in bytes
APP_NAME = 'httpfs'
COMMAND_QUIT = 'quit'
COMMAND_HELP = 'help'
COMMAND_LISTEN = 'listen'
FLAG_DEBUG = '-v'
FLAG_PORT = '-p'
FLAG_DIR_PATH = '-d'
VERB_GET = 'GET'
VERB_POST = 'POST'
# Will find command line flags and their parameters
REGEX_FLAGS = r"(?P<flag>-{1,2}\S*)(?:[=:]?|\s+)(?P<params>[^-\s].*?)?(?=\s+[-\/]|$)"
# Taken from https://stackoverflow.com/questions/6038061/regular-expression-to-find-urls-within-a-string
REGEX_URL = r"(http://)([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"
# Command regexes
REGEX_REQUEST = rf"^({VERB_GET}|{VERB_POST})\s+/([\w\./]+)*"
# Taken from https://www.regextester.com/96741
REGEX_PATH = r"(^[a-zA-Z]:(\\|/)[(\\|/)\S|*\S]?.*$)"

debug = False
directory = DEFAULT_DIR
port = DEFAULT_PORT
statuses = {
    200: "OK",
    400: "BAD REQUEST",
    403: "FORBIDDEN",
    404: "NOT FOUND"
}

def help():
    print(f'{APP_NAME} is a simple file server.')
    print(f'Usage: {COMMAND_LISTEN} [{FLAG_DEBUG}] [{FLAG_PORT} PORT] [{FLAG_DIR_PATH} PATH-TO-DIR]')
    print(f'\t{FLAG_DEBUG} Prints debugging messages.')
    print(f'\t{FLAG_PORT} Specifies the port number that the server will listen and serve at. Default is {DEFAULT_PORT}.')
    print(f'\t{FLAG_DIR_PATH} Specifies the directory that the server will use to read/write requested files. Default is the current directory when launching the application.')

def print_debug_info(address, data):
    if not data:
        print(f'[{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT] {address} end transmission.')
        print()
        print('=' * 50)
        print()
        return
    print(f'[{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT] {address} sent:')
    print(f'{data}')

def handle_request(clientsocket, request):
    # First line of request contains which verb (GET/POST) and which directory/file
    match = re.search(REGEX_REQUEST, request)
    if match is None:
        # Bad request
        status = get_status(400)
        if debug: 
            print(status)
            print(request)
        response_str = write_response_headers(f'{status}\r\n{request}\r\n\r\n', 400)
        send_response(clientsocket, response_str)
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
    if path is not None and directory.lower() not in abspath(path).lower():
        status = get_status(403)
        msg = 'You do not have the permissions to GET outside the working directory.'
        if debug:
            print(status)
            print(msg)
        response_str = write_response_headers(f'{status}\r\n{msg}\r\n\r\n', 403)
        send_response(clientsocket, response_str)
        return

    if path is None or isdir(path):
        # No need to print status code in response body if status is 200
        contents = listdir(path)
        if debug:
            print(get_status(200))
            path_str = path if path else 'root'
            print(f'Directory {path_str} has {len(contents)} item(s)')
            print(contents)
        response_str = ''
        for f in contents:
            response_str += f + '\r\n'
        # Add another newline to denote end of response
        response_str += '\r\n'
        response_str = write_response_headers(response_str, 200)
        send_response(clientsocket, response_str)
        return
    elif isfile(path):
        with open(path) as f:
            contents = f.read()
            contents += '\r\n\r\n'
            response_str = write_response_headers(contents, 200)
            send_response(clientsocket, response_str)
            return
    else:
        status = get_status(404)
        if debug:
            print(status)
        response_str = write_response_headers(f'{status}\r\n\r\n', 404)
        send_response(clientsocket, response_str)

def handle_post(clientsocket, path, body):
    msg = ''
    response_str = ''
    # Cannot write to file if no path (filename) in request
    # If path is a directory, then program needs explicit filename to write to
    if path is None or isdir(path):
        status = get_status(400)
        msg = f'Path {path} is not a filename.'
        if debug: 
            print(status)
            print(msg)
        response_str = write_response_headers(f'{status}\r\n{msg}\r\n\r\n', 400)
        send_response(clientsocket, response_str)
        return
    
    # Check that path is not outside server (application) root directory
    if path is not None and directory.lower() not in abspath(path).lower():
        status = get_status(403)
        msg = 'You do not have the permissions to POST outside the working directory.'
        if debug:
            print(status)
            print(msg)
        response_str = write_response_headers(f'{status}\r\n{msg}\r\n\r\n', 403)
        send_response(clientsocket, response_str)
        return   

    # Prevent writing to this file
    if __file__.lower() == abspath(path).lower():
        status = get_status(403)
        msg = 'You cannot write to this file.'
        if debug:
            print(status)
            print(msg)
        response_str = write_response_headers(f'{status}\r\n{msg}\r\n\r\n', 403)
        send_response(clientsocket, response_str)
        return

    # Write to file
    # Overwrite file if exists, otherwise create it
    try:
        if isfile(path):
            msg = f'Overwrote contents of {path} with:\r\n{body}'
        else:
            msg = f'File {path} created with contents:\r\n{body}'
        with open(path, 'w+') as f:
            f.write(body)
        if debug:
            print(get_status(200))
            print(msg)
        response_str = write_response_headers(msg + '\r\n\r\n', 200)
    except PermissionError:
        status = get_status(403)
        msg = 'You do not have permissions to modify the contents of this file or directory.'        
        if debug:
            print(status)
            print(msg)
        response_str = write_response_headers(f'{status}\r\n{msg}\r\n\r\n', 403)
    send_response(clientsocket, response_str)

def write_response_headers(response_str, status_code):
    # Prepend string with extra info for httpc's verbose flag
    response_str = f'Content-Length: {len(response_str)}\r\n\r\n{response_str}'
    response_str = f'Date: {datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")} GMT\r\n{response_str}'
    response_str = f'Content-Type: text/plain\r\n{response_str}'
    response_str = f'HTTP/1.0 {status_code} {statuses[status_code]}\r\n{response_str}'
    return response_str

def send_response(clientsocket, response_str):
    response_bytes = bytes(response_str, encoding='ASCII')
    clientsocket.sendall(response_bytes)

def get_request_body(request):
    # Get text immediately after headers
    index = request.find('\r\n\r\n')    
    return request[index:].strip()

def get_status(status_code):
    return f'{status_code} {statuses[status_code]}'

def get_flags(query):
    flags = re.findall(REGEX_FLAGS, query)
    return flags

def is_number(value):
    try:
        int(value)
    except ValueError:
        return False
    return True

def parse_query(query):
    if query == COMMAND_HELP:
        help()
        return False
    if not query.startswith(COMMAND_LISTEN):
        print(f"Unknown command. Type '{COMMAND_HELP}' for usage information.")
        return False
    flags = get_flags(query)
    global debug, directory, port
    for flag, value in flags:
        if flag == FLAG_DEBUG:
            debug = True
        if flag == FLAG_DIR_PATH:
            # Only tested for Windows
            # Windows usually uses a backslash for its paths but is unintuitive to type in
            path = value.strip("'").replace('/', '\\')            
            if not re.search(REGEX_PATH, path):
                print('Please enter a valid absolute path for the working directory.')
                return False
            if not isdir(path):
                print('This path does not exist or is not a directory. Please create the directory or enter the absolute path of an existing directory.')
                return False
            chdir(path)
            directory = path
        if flag == FLAG_PORT:
            if not value or not is_number(value) or not(0 < int(value) < 65535):
                print('Please enter a positive number from 0 to 65535 for the port.') 
                return False
            port = int(value)
    return True
    # print(f"Unknown command. Type '{COMMAND_HELP}' for usage information.")
    # return False

is_valid = False
# Enter app parameters before activating socket
while True:
    print()
    print(f'{APP_NAME} > ', end='')
    query = input()
    if query == COMMAND_QUIT:
        exit()
    is_valid = parse_query(query)
    if is_valid:
        break

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, port))
    s.listen()
    print(f'Listening on port {port} in directory {directory}...')
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