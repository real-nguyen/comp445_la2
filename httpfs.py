import socket
import re
import os

DIRNAME = os.path.dirname(__file__)
# Default folder is the one where httpfs.py is located (root folder)
DEFAULT_DIR = DIRNAME
DEFAULT_PORT = 8080
BUFFER_SIZE = 4096 # in bytes
APP_NAME = 'httpfs'
COMMAND_GET = 'get'
COMMAND_POST = 'post'
COMMAND_QUIT = 'quit'
FLAG_VERBOSE = '-v'
FLAG_PORT = '-p'
FLAG_DIR_PATH = '-d'
# Will find command line flags and their parameters
REGEX_FLAGS = r"(?P<flag>-{1,2}\S*)(?:[=:]?|\s+)(?P<params>[^-\s].*?)?(?=\s+[-\/]|$)"
# Taken from https://stackoverflow.com/questions/6038061/regular-expression-to-find-urls-within-a-string
REGEX_URL = r"(http://)([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"
# Command regexes
REGEX_STARTS_WITH_APP_NAME = rf"^{APP_NAME}"
REGEX_NO_COMMAND = rf"^{APP_NAME}$"
REGEX_GET = rf"^({APP_NAME} {COMMAND_GET})"
REGEX_POST = rf"^({APP_NAME} {COMMAND_POST})"

