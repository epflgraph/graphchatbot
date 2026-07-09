"""
This module reads the config file and stores its contents in a `config` variable that can be imported throughout the application.
"""

import os
from configparser import ConfigParser

from dotenv import load_dotenv

load_dotenv()

# Load the configuration file
path = os.path.dirname(__file__)
parser = ConfigParser()
parser.read(f'{path}/../config.ini')

config = {section: dict(parser[section]) for section in parser.sections()}
