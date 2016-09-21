from urllib import parse
import logging
import os
import pkg_resources

from sprockets.mixins.mediatype import content, transcoders
from tornado import web
import sprockets.http
import sprockets.mixins.mediatype.handlers

from readings import handlers, helpers


class Application(web.Application):

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        if kwargs.get('debug', False):
            kwargs['cookie_secret'] = 'secret'
        else:
            kwargs['cookie_secret'] = os.urandom(256)

        kwargs.setdefault(
            'static_path',
            pkg_resources.resource_filename('readings', 'static'))
        kwargs.setdefault('static_url_path', '/static')
        kwargs.setdefault('login_url', '/login')
        super(Application, self).__init__([
                web.url(r'/', handlers.ReadingsHandler, name='readings'),
                web.url(r'/login', handlers.LoginHandler, name='login'),
                web.url(r'/logout', handlers.LogoutHandler),
                web.url(r'/(?P<reading_id>.*)', handlers.ReadingHandler,
                        name='reading')
            ], **kwargs)
        content.set_default_content_type(self, 'application/json',
                                         encoding='utf-8')
        content.add_transcoder(self, transcoders.JSONTranscoder())
        content.add_transcoder(self, FormUrlEncodedTranscoder())

        self._mongo = None

    @property
    def mongo(self):
        if self._mongo is None:
            self._mongo = helpers.MongoClient(
                user=os.environ.get('MONGODB_USER', 'readings'),
                password=os.environ.get('MONGODB_PASSWORD', ''),
                host=os.environ.get('MONGODB_HOST', '127.0.0.1'),
                port=int(os.environ.get('MONGODB_PORT', '27017')),
                database=os.environ.get('MONGODB_DATABASE', 'readings'),
            )
        return self._mongo


class FormUrlEncodedTranscoder(
        sprockets.mixins.mediatype.handlers.TextContentHandler):

    content_type = 'application/x-www-form-urlencoded'

    def __init__(self, content_type='application/x-www-form-urlencoded',
                 default_encoding='utf-8'):
        super(FormUrlEncodedTranscoder, self).__init__(
            content_type, self.dumps, self.loads, default_encoding)

    def dumps(self, obj):
        pass

    def loads(self, str_repr):
        body = {}
        for name, value in parse.parse_qsl(str_repr):
            if name in body:
                if isinstance(body[name], list):
                    body[name].append(value)
                else:
                    body[name] = [body[name], value]
            else:
                body[name] = value
        return body


def main():
    root_level = 'INFO' if os.environ.get('DEBUG', None) is None else 'DEBUG'
    sprockets.http.run(Application, log_config={
        'version': 1,
        'disable_existing_loggers': False,
        'incremental': False,
        'formatters': {
            'console': {
                'format': '%(levelname)-10s %(name)s: %(message)s'
            }
        },
        'handlers': {'console': {'class': 'logging.StreamHandler',
                                 'stream': 'ext://sys.stdout',
                                 'level': 'DEBUG',
                                 'formatter': 'console'}},
        'root': {'level': root_level, 'handlers': ['console']},
        'loggers': {'readings': {'level': 'DEBUG'}},
    })


if __name__ == '__main__':
    main()
