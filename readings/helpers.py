from urllib import parse
import logging
import json

from motor import motor_tornado
from tornado import gen, web
import pymongo.errors


class AbsoluteReverseUrlMixin(web.RequestHandler):

    def reverse_url(self, name, *args):
        url = super(AbsoluteReverseUrlMixin, self).reverse_url(name, *args)
        return '{}://{}{}'.format(
            self.request.protocol, self.request.host, url)


class AJAXRedirectMixin(web.RequestHandler):

    def initialize(self):
        super(AJAXRedirectMixin, self).initialize()
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(__name__)

    def redirect(self, url, permanent=False, status=None):
        try:
            xhr = self.request.headers['X-Requested-With']
            if xhr.lower() == 'xmlhttprequest':
                self.logger.debug('AJAXin redirect to %s', url)
                self.set_status(200)
                if hasattr(self, 'send_response'):
                    self.send_response({'redirect': url, 'status': status})
                else:
                    self.set_header('Content-Type', 'application/json')
                    self.write(json.dumps({'redirect': url,
                                           'status': status}).encode('utf-8'))
            return self.finish()

        except KeyError:
            pass

        super(AJAXRedirectMixin, self).redirect(url, permanent=permanent,
                                                status=status)


class MongoClient(object):

    def __init__(self, host, port, user, password, database):
        super(MongoClient, self).__init__()
        self.logger = logging.getLogger(__name__)
        dsn = 'mongodb://{user}:{password}@{host}:{port}/{database}'.format(
            user=parse.quote(user, safe=''),
            password=parse.quote(password, safe=''),
            host=host, port=port, database=parse.quote(database, safe=''))
        self.mongo = motor_tornado.MotorClient(dsn)

    @gen.coroutine
    def find_one(self, collection, query_spec, **kwargs):
        retry_count = kwargs.pop('retry_count', 0)
        self.logger.debug('searching %s for %r (attempt %d)',
                          collection, query_spec, retry_count)
        db = self.mongo.readings
        coll = db[collection]
        try:
            res = yield coll.find_one(query_spec)
            if res:
                doc = dict(res)
                if '_id' in doc and 'id' not in doc:
                    doc['id'] = str(doc['_id'])
            else:
                self.logger.debug('document not found')
                doc = None

        except pymongo.errors.AutoReconnect as error:
            if retry_count < 5:
                self.logger.warning('mongo reconnecting, retrying operation, '
                                    'attempt %d', retry_count)
                doc = yield self.find_one(collection, query_spec,
                                          retry_count=retry_count+1)
            else:
                self.logger.error('giving up on mongo connection - %r',
                                  error)
                raise error

        raise gen.Return(doc)

    @gen.coroutine
    def find(self, collection, query_spec, *sort_spec, **kwargs):
        retry_count = kwargs.pop('retry_count', 0)
        db = self.mongo.readings
        coll = db[collection]
        try:
            cursor = coll.find(query_spec)
            if sort_spec:
                cursor = cursor.sort(*sort_spec)
            results = []
            while (yield cursor.fetch_next):
                doc = cursor.next_object()
                results.append(doc)

        except pymongo.errors.AutoReconnect as error:
            if retry_count < 5:
                self.logger.warning('mongo reconnecting, retrying operation, '
                                    'attempt %d', retry_count)
                results = yield self.find(collection, query_spec, sort_spec,
                                          retry_count=retry_count+1)
            else:
                self.logger.error('giving up on mongo connection - %r',
                                  error)
                raise error

        raise gen.Return(results)
