from elasticsearch_interface.es import ES

from app.config import config

es = ES(config['elasticsearch'], 'graph_en')
