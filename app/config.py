import os
from configparser import ConfigParser

# Load the configuration file
path = os.path.dirname(__file__)
parser = ConfigParser()
parser.read(f'{path}/../config.ini')

config = {section: dict(parser[section]) for section in parser.sections()}
