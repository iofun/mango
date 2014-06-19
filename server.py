# -*- coding: utf-8 -*-
'''
    Manage Asynchronous Number of Granular/Going ORGs

    Organizations of restricted generality (ORGs)
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Jean Chassoul'


import os
import logging
import arrow
import motor

import itertools
#import psycopg2
#import momoko

from tornado import ioloop
from tornado import gen
from tornado import web

# from tornado import websocket

from mango.handlers import accounts
from mango.handlers import billings
from mango.handlers import records

from mango.tools import options
from mango.tools import indexes
from mango.tools import periodic

# new resource function
from mango.tools import new_resource

from mango.handlers import MangoHandler, LoginHandler, LogoutHandler


# iofun testing box
iofun = []

# e_tag
e_tag = False


class IndexHandler(web.RequestHandler):
    '''
        HTML5 Index
    '''

    def get(self):
        self.render('index.html', test="Hello, world!")


@gen.engine
def periodic_records_callbacks(stuff='bananas'):
    '''
        Mango periodic records
    '''  
    results = yield [
        motor.Op(periodic.process_assigned_false, db),
        motor.Op(periodic.process_asterisk_cdr, db)
    ]

    # incomprehensible list comprehensions.
    # result = [item for sublist in results for item in sublist]

    # itertools.chain
    result = list(itertools.chain.from_iterable(results))

    # print('periodic records: ', result)

    for record in result:
        flag = yield motor.Op(
            periodic.assign_call,
            db,
            record['account'],
            record['id'] # uuid?
        )

        # check new resource
        resource = yield motor.Op(new_resource, db, record)


if __name__ == '__main__':
    '''
        Manage Asynchronous Number Granular/Going ORGs

        Organizations of Restricted Generality.
    '''
    opts = options.options()

    # Mango periodic functions
    periodic_records = opts.periodic_records

    # Set document database
    document = motor.MotorClient().open_sync().mango

    # Set default database
    db = document

    if opts.ensure_indexes:
        logging.info('Ensuring indexes...')
        indexes.ensure_indexes(db)
        logging.info('DONE.')

    # base url
    base_url = opts.base_url

    # mango web application daemon
    application = web.Application(

        [
            (r'/', IndexHandler),

            # Mango system knowledge (quotes).
            (r'/system/?', MangoHandler),

            # Tornado static file handler 
            (r'/static/(.*)', web.StaticFileHandler, {'path': './static'},),

            # Basic-Auth session
            (r'/login/?', LoginHandler),
            (r'/logout/?', LogoutHandler),

            # ORGs records
            (r'/orgs/(?P<account>.+)/records/?', accounts.RecordsHandler),
            (r'/orgs/(?P<account>.+)/records/page/(?P<page_num>\d+)/?', accounts.RecordsHandler),

            (r'/orgs/(?P<account>.+)/records/?', accounts.RecordsHandler),
            (r'/orgs/(?P<account>.+)/records/page/(?P<page_num>\d+)/?', accounts.RecordsHandler),

            # ORGs teams
            (r'/orgs/(?P<account>.+)/teams/page/(?P<page_num>\d+)/?', accounts.TeamsHandler),
            (r'/orgs/(?P<account>.+)/teams/(?P<team_uuid>.+)/?', accounts.TeamsHandler),
            (r'/orgs/(?P<account>.+)/teams/?', accounts.TeamsHandler),

            # ORGs members
            (r'/orgs/(?P<account>.+)/members/page/(?P<page_num>\d+)/?', accounts.MembersHandler),
            (r'/orgs/(?P<account>.+)/members/(?P<user>.+)/?', accounts.MembersHandler),
            (r'/orgs/(?P<account>.+)/members/?', accounts.MembersHandler),

            # Organizations of Restricted Generality
            (r'/orgs/?', accounts.OrgsHandler),
            (r'/orgs/(?P<account>.+)/?', accounts.OrgsHandler),

            # Users records 
            (r'/users/(?P<account>.+)/records/?', accounts.RecordsHandler),
            (r'/users/(?P<account>.+)/records/page/(?P<page_num>\d+)/?', accounts.RecordsHandler),

            # Users billing routes
            (r'/users/(?P<account>.+)/routes/?', accounts.RoutesHandler),

            # Users
            (r'/users/?', accounts.UsersHandler),
            (r'/users/(?P<account>.+)/?', accounts.UsersHandler),

            # Records
            (r'/records/start/(?P<start>.*)/end/(?P<end>.*)/?', records.Handler),
            (r'/records/start/(?P<start>.*)/?', records.Handler),
            (r'/records/end/(?P<end>.*)/?', records.Handler),
            (r'/records/page/(?P<page_num>\d+)/?', records.Handler),

            # Public records 
            (r'/records/public/?', records.PublicHandler),
            (r'/records/public/page/(?P<page_num>\d+)/?', records.PublicHandler),

            # Unassigned records
            (r'/records/unassigned/?', records.UnassignedHandler),
            (r'/records/unassigned/page/(?P<page_num>\d+)/?', records.UnassignedHandler),

            # Records summary
            # (r'/records/summary/<lapse>/<value>/?', records.SummaryHandler),

            # Return last (n) of lapse
            # (r'/records/summary/<lapse>/lasts/(?P<int>\d+)/?', records.SummaryHandler),

            # Statistical projection based on the previous data.
            # (r'/records/summary/<lapse>/nexts/(?P<int>\d+)/?', records.SummaryHandler),

            # Records summary
            (r'/records/summary/start/(?P<start>.*)/end/(?P<end>.*)/?', records.SummaryHandler),
            
            (r'/records/summary/start/(?P<start>.*)/?', records.SummaryHandler),
            
            (r'/records/summary/end/(?P<end>.*)/?', records.SummaryHandler),

            (r'/records/summary/(?P<lapse>.*)/start/(?P<start>.*)/end/(?P<end>.*)/?', records.SummaryHandler),
            (r'/records/summary/(?P<lapse>.*)/start/(?P<start>.*)/?', records.SummaryHandler),
            (r'/records/summary/(?P<lapse>.*)/end/(?P<end>.*)/?', records.SummaryHandler),

            # Return last (n) of lapse
            # (r'/records/summary/(?P<lapse>.*)/lasts/(?P<int>\d+)/?', records.SummaryHandler),

            (r'/records/summary/(?P<lapse>.*)/?', records.SummaryHandler),
            (r'/records/summary/?', records.SummaryHandler),

            # Records summaries
            (r'/records/summaries/start/(?P<start>.*)/end/(?P<end>.*)/?', records.SummariesHandler),
            (r'/records/summaries/start/(?P<start>.*)/?', records.SummariesHandler),
            (r'/records/summaries/end/(?P<end>.*)/?', records.SummariesHandler),

            (r'/records/summaries/(?P<lapse>.*)/start/(?P<start>.*)/end/(?P<end>.*)/?', records.SummariesHandler),
            (r'/records/summaries/(?P<lapse>.*)/start/(?P<start>.*)/?', records.SummariesHandler),
            (r'/records/summaries/(?P<lapse>.*)/end/(?P<end>.*)/?', records.SummariesHandler),

            (r'/records/summaries/(?P<lapse>.*)/?', records.SummariesHandler),
            (r'/records/summaries/?', records.SummariesHandler),

            # Records
            (r'/records/(?P<record_uuid>.+)/?', records.Handler),
            (r'/records/?', records.Handler),


            # Reports
            

            # Billings
            (r'/billings/(?P<billing_uuid>.+)/?', billings.RecordsHandler),
            (r'/billings/?', billings.RecordsHandler),

            # Billings records
            (r'/billings/records/start/(?P<start>.*)/end/(?P<end>.*)/?', billings.RecordsHandler),
            (r'/billings/records/start/(?P<start>.*)/?', billings.RecordsHandler),
            (r'/billings/records/end/(?P<end>.*)/?', billings.RecordsHandler),
            (r'/billings/records/?', billings.RecordsHandler)

        ],

        # system database
        db=db,

        # periodic records
        periodic_records=periodic_records,

        # application domain
        domain=opts.domain,

        # application timezone
        tz=arrow.now(opts.timezone),

        # pagination page size
        page_size=opts.page_size,

        # cookie settings
        cookie_secret=opts.cookie_secret,

        # static files (this is all the html, css, js and stuff)
        # on production environment the static stuff is served with nginx.

        static_path=os.path.join(os.path.dirname(__file__), "static"),

        template_path=os.path.join(os.path.dirname(__file__), "templates"),

        # login url
        login_url='/login'
    )

    # Set relational database
    #application.sql = momoko.Pool(
    #    dsn='dbname=asterisk user=postgres',
    #    size=1
    #)

    # Tornado periodic callbacks
    periodic_records = ioloop.PeriodicCallback(periodic_records_callbacks, 10000)
    periodic_records.start()

    # Setting up mango server processor
    application.listen(opts.port)
    logging.info('Listening on http://%s:%s' % (opts.host, opts.port))
    ioloop.IOLoop.instance().start()