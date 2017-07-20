import datetime

from sprockets.http import mixins
from sprockets.mixins.mediatype import content
from tornado import concurrent, gen, web
import bson.objectid
import jwt.exceptions
import pymongo
import pytz

from readings import helpers


class UserMixin(web.RequestHandler):

    def initialize(self):
        super(UserMixin, self).initialize()
        self.mongo = self.application.mongo
        self.user_info = None

    @gen.coroutine
    def prepare(self):
        maybe_future = super(UserMixin, self).prepare()
        if concurrent.is_future(maybe_future):
            yield maybe_future

        if not self._finished:
            user_id = self.get_secure_cookie('user')
            if not user_id:
                self.redirect(self.get_login_url())
                return

            self.user_info = yield self.mongo.find_one(
                'users', bson.objectid.ObjectId(user_id.decode('ASCII')))

    def get_current_user(self):
        return self.user_info


class LoginHandler(helpers.AbsoluteReverseUrlMixin, content.ContentMixin,
                   mixins.ErrorLogger, mixins.ErrorWriter, web.RequestHandler):

    def initialize(self):
        super(LoginHandler, self).initialize()
        self.mongo = self.application.mongo

    def get(self):
        """
        Retrieve the login page.

        This endpoint returns a login page that contains the login
        form, javascript implementation of JWT, and the CSRF token
        required for login.

        :statuscode 302: this endpoint should never fail since
            it simply redirects to a static HTML+JS.

        """
        self.logger.debug('using csrf %r', self.xsrf_token)
        self.set_cookie('csrf', self.xsrf_token)
        return self.redirect(self.static_url('login.html'))

    @gen.coroutine
    def post(self):
        """
        Try to login.

        :<json str email: email address to login with.
        :<json str token: generated `JWT`_ token.

        The password is used as the secret to generate the JWT-encoded
        token of the following payload object.

        .. json:object:: JWT Payload

          :property string iss: Identifes the issuer.  This is the URL
            of the login page.
          :property integer nbf: The earliest time at which this token
            is valid.  Set this to "now".
          :property integer exp: The latest time at which this token
            is valid.  Usually something like "nbf + 300".
          :property string csrf: The value of the "csrf" cookie.

        :statuscode 303: a ``POST`` results in a *redirect* to either the
            login page or the **list of readings**

        :reqheader Content-Type: identifies the format of the login data.

        .. _JWT: http://jwt.io/

        """
        body = self.get_request_body()

        user_info = yield self.mongo.find_one('users',
                                              {'email': body['email']})
        if not user_info:
            raise web.HTTPError(404)
        scrubbed_info = user_info.copy()
        scrubbed_info['password'] = '*' * len(scrubbed_info['password'])
        self.logger.info('found user information -> %r', scrubbed_info)

        try:
            token = jwt.decode(
                body['token'], key=user_info['password'],
                options={'require_exp': True, 'verify_exp': True,
                         'require_nbf': True, 'verify_nbf': True})
        except jwt.exceptions.DecodeError as err:
            self.logger.warning('JWT decode failed: %s', err)
            self.redirect(self.get_login_url(), status=303)
            raise web.Finish

        try:
            if token['csrf'] != self.get_cookie('csrf'):
                self.logger.warning('CSRF mismatch - expecting %r, got %r',
                                    self.xsrf_token, token['csrf'])
                self.redirect(self.reverse_url('login'), status=303)
                raise web.Finish

        except KeyError:
            self.logger.warning('missing CSRF')
            self.redirect(self.get_login_url(), status=303)
            raise web.Finish

        self.set_secure_cookie('user', str(user_info['_id']), expires_days=1)
        self.redirect(self.static_url('index.html'), status=303)


class LogoutHandler(web.RequestHandler):

    def get(self):
        """
        Simply log out.

        This destroys the secure cookie and redirects you to
        :http:get:`/login`.

        :statuscode 302: redirects to the login page

        """
        self.clear_cookie('user')
        self.redirect(self.reverse_url('login'))


class ReadingsHandler(UserMixin, helpers.AbsoluteReverseUrlMixin,
                      helpers.AJAXRedirectMixin, content.ContentMixin,
                      mixins.ErrorLogger, mixins.ErrorWriter,
                      web.RequestHandler):

    def initialize(self):
        super(ReadingsHandler, self).initialize()
        self.mongo = self.application.mongo

    @web.authenticated
    @gen.coroutine
    def get(self):
        """
        Retrieve a list of readings.

        :>jsonarr str link: canonical link to this reading
        :>jsonarr str href: external link to the reading content
        :>jsonarr str added: date that this reading was added

        Use this method to retrieve the list of readings as a JSON array.
        It requires that you are already *authenticated*.  If you are not
        authenticated, then you will be redirected to the login page.

        :statuscode 200: the response includes the list of readings
        :statuscode 302: you have not logged in.  The :http:header:`Location`
            header will redirect to the login page.
        :statuscode 303: the request is not an AJAX request.  The
            :http:header:`Location` header will redirect to the root
            page since that is probably what you wanted anyway.

        """
        if self.is_ajax_request():
            self.logger.debug('retrieving readings for %s',
                              self.current_user['id'])
            docs = yield self.mongo.find('readings',
                                         {'user_id': self.current_user['id']},
                                         'when', pymongo.DESCENDING)
            readings = [{'link': self.reverse_url('reading', str(doc['_id'])),
                         'href': doc['link'], 'title': doc['title'],
                         'added': doc['when'].replace(tzinfo=pytz.utc)}
                        for doc in docs]
            self.send_response(readings)
            self.finish()
        else:
            self.logger.debug('not an AJAX request, redirecting to index')
            self.logger.debug('headers: %r', dict(self.request.headers))
            self.redirect(self.static_url('index.html'), status=303)

    @web.authenticated
    @gen.coroutine
    def post(self):
        """
        Add something to the list.

        :<jsonarr str title: title of the page/article
        :<jsonarr str link: link to the page

        :statuscode 204: the reading was added and is available by retrieving
            the resource identified by the :http:header:`Location` header.
        :statuscode 302: you have not logged in.  The :http:header:`Location`
            header will redirect to the login page.
        :resheader Location: the canonical location for the created reading.

        """
        body = self.get_request_body()
        new_doc = {'user_id': self.current_user['id'],
                   'title': body['title'],
                   'link': body['url'],
                   'when': datetime.datetime.utcnow()}

        self.logger.debug('adding reading - %r', new_doc)
        doc_id = yield self.mongo.save('readings', new_doc)
        self.set_header('Location', self.reverse_url('reading', doc_id))
        self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
        self.set_header('Access-Control-Allow-Methods', 'GET')
        self.set_status(204)
        self.finish()


class ReadingHandler(UserMixin, helpers.AbsoluteReverseUrlMixin,
                     helpers.AJAXRedirectMixin, content.ContentMixin,
                     mixins.ErrorLogger, mixins.ErrorWriter,
                     web.RequestHandler):

    @web.authenticated
    @gen.coroutine
    def get(self, reading_id):
        """
        Go to a specific reading.

        :param str reading_id: the unique identifier of the reading to
            jump to

        :statuscode 302: redirects to the reading content or the login
            page if you are not logged in
        :resheader Location: the location of the reading content

        """
        db = self.application.mongo.readings
        coll = db.readings
        cursor = coll.find({'user_id': self.current_user['id'],
                            '_id': bson.objectid.ObjectId(reading_id)})
        yield cursor.fetch_next
        reading = cursor.next_object()
        self.redirect(reading['link'])
