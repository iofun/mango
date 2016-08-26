# -*- coding: utf-8 -*-
'''
    Mango HTTP base handlers.
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Jean Chassoul'


import time
import motor
import queries
from tornado import gen
from tornado import web
from zmq.eventloop import ioloop
from mango.system import basic_authentication
from mango.messages import tasks as _tasks
from mango.tools import clean_structure
from mango.tools import check_account_authorization
from mango import errors
from mango.tools.quotes import PeopleQuotes
import logging


class BaseHandler(web.RequestHandler):
    '''
        System application request handler

        gente d'armi e ganti
    '''

    @property
    def sql(self):
        '''
            SQL database
        '''
        return self.settings['sql']

    @property
    def document(self):
        '''
            Document database
        '''
        return self.application.document

    @property
    def kvalue(self):
        '''
            Key-value database
        '''
        return self.application.kvalue

    @property
    def cache(self):
        '''
            Cache backend
        '''
        return self.settings['cache']

    def initialize(self, **kwargs):
        '''
            Initialize the Base Handler
        '''
        super(BaseHandler, self).initialize(**kwargs)
        self.etag = None
        # System database
        self.db = self.settings['db']
        # Page settings
        self.page_size = self.settings['page_size']

    def set_default_headers(self):
        '''
            Mango default headers
        '''
        # if debug set allow all if not set settings domain
        # all means fucking all the multiverse and stuff 
        # this shit is for CORS support, thanks!.
        self.set_header("Access-Control-Allow-Origin", '*')
        # self.set_header("Access-Control-Allow-Origin", self.settings['domain'])

    def get_current_username(self):
        '''
            Return the username from a secure cookie
        '''
        return self.get_secure_cookie('username')

    def get_current_account(self):
        '''
            Return the account from a secure cookie
        '''
        return self.get_secure_cookie('account')

    @gen.coroutine
    def let_it_crash(self, struct, scheme, error, reason):
        '''
            Let it crash
        '''
        # missing zmq sub topic
        # if something fucking happens we need to report the error
        # to the fucking overlord supervisor
        # yep the name is inspired directly on erlang
        # but sure this is not the beam and we're not saying that
        # the entire system is made to work toguether with erlang.

        # of course we're not totally there yet. )=
        str_error = str(error)
        error_handler = errors.Error(error)
        messages = []
        if error and 'Model' in str_error:
            message = error_handler.model(scheme)
        elif error and 'duplicate' in str_error:
            for name, value in reason.get('duplicates'):
                if value in str_error:
                    message = error_handler.duplicate(
                        name.title(),
                        value,
                        struct.get(value)
                    )
                    messages.append(message)
            message = ({'messages':messages} if messages else False)
        elif error and 'value' in str_error:
            message = error_handler.value()
        elif error is not None:
            logging.warning(str_error)
            logging.error(struct, scheme, error, reason)
            message = {
                'error': u'https://nonsense.ws/help',
                'message': u"there is no error, stuff don't make sense... but that's life right?"
            }
        else:
            quotes = PeopleQuotes()
            message = {
                'status': 200,
                'message': quotes.get()
            }
        raise gen.Return(message)

    @gen.coroutine
    def new_sip_account(self, struct):
        '''
            New sip account
        '''
        try:
            # Get SQL database from system settings
            sql = self.settings.get('sql')
            # PostgreSQL insert new sip account query
            query = '''
                insert into sip (
                    name,
                    defaultuser,
                    fromuser,
                    fromdomain,
                    host,
                    sippasswd,
                    directmedia,
                    videosupport,
                    transport,
                    allow,
                    context,
                    nat,
                    qualify,
                    avpf,
                    encryption,
                    force_avp,
                    dtlsenable,
                    dtlsverify,
                    dtlscertfile,
                    dtlsprivatekey,
                    dtlssetup,
                    directrtpsetup,
                    icesupport
                ) values (
                    '{0}',
                    '{1}',
                    '{2}',
                    '{3}',
                    'dynamic',
                    '{4}',
                    'no',
                    'no',
                    'udp,wss',
                    'opus,ulaw,alaw,g729,vp8',
                    'fun-accounts',
                    'force_rport,comedia',
                    'yes',
                    'yes',
                    'yes',
                    'yes',
                    'no',
                    '/etc/asterisk/keys/asterisk.pem',
                    '/etc/asterisk/keys/asterisk.pem',
                    'actpass',
                    'no',
                    'yes'
                );
            '''.format(
                struct.get('account'),
                struct.get('account'),
                struct.get('account'),
                struct.get('domain', self.settings.get('domain')),
                struct.get('password')
            )
            result = yield sql.query(query)
            if result:
                message = {'ack': True}
            else:
                message = {'ack': False}
            result.free()
            logging.warning('new sip account spawned on PostgreSQL {0}'.format(message))

        # TODO: Still need to check the follings exceptions with the new queries module.
        #except (psycopg2.Warning, psycopg2.Error) as e:
        #    logging.exception(e)
        #    raise e
        
        except Exception, e:
            logging.exception(e)
            raise e

        raise gen.Return(message)

    @gen.coroutine
    def new_coturn_account(self, struct):
        '''
            New coturn account task
        '''
        try:
            task = _tasks.Task(struct)
            task.validate()
        except Exception, e:
            logging.exception(e)
            raise e

        task = clean_structure(task)
        result = yield self.db.tasks.insert(task)

        raise gen.Return(task.get('uuid'))


@basic_authentication
class LoginHandler(BaseHandler):
    '''
        BasicAuth login
    '''

    @gen.coroutine
    def get(self):
        # redirect next url
        next_url = '/'
        args = self.get_arguments('next')
        if args:
            next_url = args[0]

        account = yield check_account_authorization(self.db,
                            self.username,
                            self.password)

        if not account:
            # 401 status code?
            self.set_status(403)
            # mae! get realm from options.
            # why you fucker? are you fucking sure and stuff ???
            # well probably to be more customizable and shit right?
            self.set_header('WWW-Authenticate', 'Basic realm=mango')
            self.finish()
        else:
            self.set_header('Access-Control-Allow-Origin','*')
            # self.set_header('Access-Control-Allow-Methods','POST, GET, OPTIONS, DELETE, PATCH, PUT, HEAD')
            self.set_header('Access-Control-Allow-Methods','GET, OPTIONS')
            self.set_header('Access-Control-Allow-Headers','Content-Type, authorization')
            self.set_secure_cookie('username', self.username)
            self.username, self.password = (None, None)
            # self.redirect(next_url)
            self.set_status(200)
            self.finish()

    @gen.coroutine
    def options(self):
        self.set_header('Access-Control-Allow-Origin','*')
        # self.set_header('Access-Control-Allow-Methods','POST, GET, OPTIONS, DELETE, PATCH, PUT, HEAD')
        self.set_header('Access-Control-Allow-Methods','GET')
        self.set_header('Access-Control-Allow-Headers','Content-Type, Authorization')
        self.set_header('Access-Control-Allow-Credentials', 'true')
        self.data = ''
        self.set_status(200)
        self.finish()


class LogoutHandler(BaseHandler):
    '''
        BasicAuth logout
    '''

    @gen.coroutine
    def get(self):
        '''
            Clear secure cookie
        '''
        self.clear_cookie('username')
        self.set_status(200)
        self.finish()


class MangoHandler(BaseHandler):
    '''
        Mango Handler Quote experiment
    '''

    @gen.coroutine
    def get(self):
        '''
            Get some quotes
        '''
        quotes = PeopleQuotes()
        self.finish(
            {'quote': quotes.get()}
        )