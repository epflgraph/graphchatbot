from configparser import ConfigParser

# Load the configuration file
parser = ConfigParser()
parser.read('../config.ini')

config = {section: dict(parser[section]) for section in parser.sections()}
