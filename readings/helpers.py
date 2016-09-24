from urllib import parse
import logging
import json

from motor import motor_tornado
from tornado import concurrent, gen, ioloop, web
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

    def is_ajax_request(self):
        xhr = self.request.headers.get('X-Requested-With', '')
        return xhr.lower() == 'xmlhttprequest'

    def redirect(self, url, permanent=False, status=None):
        if self.is_ajax_request():
            self.logger.debug('AJAXin redirect to %s', url)
            self.set_status(200)
            if hasattr(self, 'send_response'):
                self.send_response({'redirect': url, 'status': status})
            else:
                self.set_header('Content-Type', 'application/json')
                self.write(json.dumps({'redirect': url,
                                       'status': status}).encode('utf-8'))
            return self.finish()

        super(AJAXRedirectMixin, self).redirect(url, permanent=permanent,
                                                status=status)


class MongoActor(object):

    def __init__(self, db, collection):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = db
        self.collection = collection
        self.retry_count = 0

    def action(self):
        raise NotImplementedError

    def on_complete(self, result):
        raise NotImplementedError

    @gen.coroutine
    def perform_operation(self):
        coro = self.action()
        iol = ioloop.IOLoop.instance()
        future = concurrent.TracebackFuture()

        def on_future_complete(f):
            exc = f.exception()
            if exc is not None:
                future.set_exception(exc)
            else:
                maybe_future = self.on_complete(f.result())
                if concurrent.is_future(maybe_future):
                    iol.add_future(maybe_future, on_future_complete)
                else:
                    future.set_result(maybe_future)

        iol.add_future(coro, on_future_complete)
        try:
            res = yield future

        except pymongo.errors.AutoReconnect as error:
            if self.retry_count < 5:
                self.logger.warning('mongo reconnecting, retrying operation, '
                                    'attempt %d', self.retry_count)
                res = yield self.perform_operation()
            else:
                self.logger.error('giving up on mongo connection - %r',
                                  error)
                raise error

        raise gen.Return(res)


class FindOne(MongoActor):

    def __init__(self, db, collection, query_spec):
        super(FindOne, self).__init__(db, collection)
        self.query_spec = query_spec

    def action(self):
        return self.db[self.collection].find_one(self.query_spec)

    def on_complete(self, result):
        result_dict = dict(result)
        if '_id' in result_dict and 'id' not in result_dict:
            result_dict['id'] = str(result_dict['_id'])
        return result_dict


class FindMany(MongoActor):

    def __init__(self, db, collection, query_spec, *sort_spec):
        super(FindMany, self).__init__(db, collection)
        self.query_spec = query_spec
        self.sort_spec = sort_spec
        self.cursor = None
        self.results = []

    def action(self):
        self.cursor = self.db[self.collection].find(self.query_spec)
        if self.sort_spec:
            self.cursor = self.cursor.sort(*self.sort_spec)
        return self.cursor.fetch_next

    def on_complete(self, result):
        if result:
            self.results.append(self.cursor.next_object())
            return self.cursor.fetch_next
        return self.results


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
    def find_one(self, collection, query_spec):
        actor = FindOne(self.mongo.readings, collection, query_spec)
        doc = yield actor.perform_operation()
        raise gen.Return(doc)

    @gen.coroutine
    def find(self, collection, query_spec, *sort_spec):
        actor = FindMany(self.mongo.readings, collection,
                         query_spec, *sort_spec)
        results = yield actor.perform_operation()
        raise gen.Return(results)
