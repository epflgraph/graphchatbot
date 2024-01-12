"""
This module instantiates an elasticsearch interface under the name `es` and makes it available for import throughout the application.
"""

from elasticsearch_interface.es import ES

from app.config import config

es = ES(config['elasticsearch'], 'graph_en')
