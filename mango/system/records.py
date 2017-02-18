# -*- coding: utf-8 -*-
'''
    Mango records system logic functions.
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Team Machine'


import logging
import arrow
import datetime
import motor
import uuid
import numpy as np
import pandas as pd
from tornado import gen
from mango.messages import records, BaseResult
from mango.tools import clean_structure, clean_message
from mango.tools import check_times, check_times_get_datetime


class Records(object):
    '''
        Records resources
    '''

    @gen.coroutine
    def get_record(self, account, record_uuid):
        '''
            Get a detail record
        '''
        message = 'where is this account {0} record {1}'.format(account, record_uuid)
        logging.info(message)
        if not account:
            record = yield self.db.records.find_one({'uuid':record_uuid}, {'_id':0})
        else:

            # change accountcode to account, because the accountcode is a uuid
            # and we're expecting an account name.
            message = 'account {0} and record {1} are you for real?'.format(account, record_uuid)
            logging.info(message)

            record = yield self.db.records.find_one({'uuid':record_uuid,
                                                     'account':account},
                                                    {'_id':0})
            logging.info(record)
        try:
            if record:
                record = records.Record(record)
                record.validate()

                record = clean_structure(record)
        except Exception, e:
            logging.exception(e) # catch some daemon here!
            raise e
        finally:
            raise gen.Return(record)

    @gen.coroutine
    def get_record_list(self, account, start, end, status, lapse, page_num):
        '''
            Get detail records 
        '''
        page_num = int(page_num)
        von_count = 0
        page_size = self.settings['page_size']
        record_list = []
        message = None
        query = {'public':False}

        if status != 'all':
            query['status'] = status        

        times = yield check_times_get_datetime(start, end)
        
        if not account:
            query = self.db.records.find({
                'start':{'$gte':times.get('start'), '$lt':times.get('end')},
                'public':False}, {'_id':0}) 
        elif type(account) is list:
            accounts = [{'accountcode':a, 'assigned': True} for a in account]
            query = self.db.records.find({'$or':accounts})
        else:
            query = self.db.records.find({
                'accountcode':account,
                'start':{'$gte':times.get('start'), '$lt':times.get('end')},
                'assigned':True})

        try:
            von_count = yield query.count()
        except Exception, e:
            logging.exception(e)
            raise e
        
        query = query.sort([('uuid', -1)]).skip(page_num * page_size).limit(page_size)
        
        try:
            
            while (yield query.fetch_next):
                result = query.next_object()
                record_list.append(records.Record(result))

        except Exception, e:
            logging.exception(e)
            raise e

        try:
            struct = {'results': record_list, 'page': page_num, 'count': von_count}

            message = BaseResult(struct)

            #message.validate()

            message = message.to_primitive()
        except Exception, e:
            logging.exception(e)
            raise e
        finally:
            raise gen.Return(message)

    @gen.coroutine
    def get_summaries(self, account, start, end, lapse, page_num):
        '''
            Get summaries
        '''
        times = yield check_times(start, end)

        if lapse:
            logging.info('get summaries lapse %s' % (lapse))

    @gen.coroutine
    def get_summary(self, account, start, end, lapse):
        '''
            Get summary
        '''
        # MongoDB Aggregation operators process data and return computed results

        message = []

        times = yield check_times_get_datetime(start, end)

        lapse = (lapse if lapse else None)

        logging.info('Getting summary for account {0} by lapse {1} start {2} end {3} time periods'.format(
            account, lapse, times.get('start'), times.get('end')
        ))
        

        # MongoDB aggregation match operator
        if type(account) is list:
            match = {
                'assigned':True,
                'start':{'$gte':times.get('start'), '$lt':times.get('end')},
                '$or':[{'accountcode':a} for a in account]
            }
        else:
            match = {
                'accountcode':account, 
                'assigned': True,
                'start': {'$gte':times.get('start'), '$lt': times.get('end')}
            }

        if not account:
            logging.info("There is not an account on get_summary aggregation match")
            match = {
                'public': False,
                'start': {'$gte':times.get('start'), '$lt': times.get('end')}
            }

        # MongoDB aggregation project operator
        project = {
            "_id" : 0,
            
            # record timestamps start, answer, end
            "start": 1,
            #"answer":1,
            #"end":1,
            
            # record duration seconds
            "duration": 1,

            # record billing seconds
            "billsec": 1,
            
            # duration of the call in seconds (only billing time)
            "seconds": 1,
            
            "year" : {  
                "$year" : "$start"
            },
            "month" : {  
                "$month" : "$start"
            },
            "week" : {  
                "$week" : "$start"
            },
            "day" : {
                "$dayOfMonth" : "$start"
            },
            "hour" : {
                "$hour" : "$start"
            },
            "minute" : {
                "$minute" : "$start"
            },
            "second" : {
                "$second" : "$start"
            }
        }

        group = {
            '_id': {
                'start': '$start',
                #'answer': '$answer',
                #'end': '$end',
                'year': '$year',
                'month': '$month',
                'week':'$week',
                'day': '$day',
                'hour':'$hour',
                'minute': '$minute',
                'second': '$second',
            },

            'records': {
                '$sum':1    # Is possible that this tell us if we have duplicate records?
            },

            'average': {
                '$avg':'$billsec'
            },

            'duration': {
                '$sum':'$duration'
            },

            'billing': {
                '$sum':'$billsec'
            },

            'seconds': {
                '$sum': '$seconds'
            }
        }

        # MongoDB aggregation pipeline
        pipeline = [
            {'$match':match},
            {'$project':project},
            {'$group':group}
        ]


        # Motor 0.5: no "cursor={}", no "yield".
        #cursor = collection.aggregate(pipeline)
        #while (yield cursor.fetch_next):
        #    doc = cursor.next_object()
        #    print(doc)


        cursor = yield self.db.records.aggregate(pipeline, cursor={})
       
        while (yield cursor.fetch_next):
            doc = cursor.next_object()
            message.append(doc)

        raise gen.Return(message)        

    @gen.coroutine
    def new_detail_record(self, struct, db=None):
        '''
            Create a new record entry
        '''
        if not db:
            db = self.db
        try:
            # if not type str convert to str...
            # same note different day... WTF I'm talking about...

            if isinstance(struct, dict):

                struct['strdate'] = '"{0}"'.format(struct.get('strdate', ''))
            
            record = records.Record(struct)
            record.validate()
        except Exception, e:
            logging.exception(e)
            raise e

        record2 = clean_structure(record)

        record = clean_message(record)

        result = yield db.records.insert(record)

        message = {
            'uniqueid':struct.get('uniqueid'),
            'uuid':record.get('uuid')
        }

        raise gen.Return(message)

    @gen.coroutine
    def set_assigned_flag(self, account, record_uuid):
        '''
            Set the record assigned flag
        '''
        logging.info('set_assigned_flag account: %s, record: %s' % (account, record_uuid))

        result = yield self.db.records.update(
                                {'uuid':record_uuid, 
                                 'accountcode':account}, 
                                {'$set': {'assigned': True}})
        
        raise gen.Return(result)

    @gen.coroutine
    def get_cost_summary(self, account, routes, lapse, start, end):
        '''
            get_cost_summary
        '''

        if not start:
            start = arrow.utcnow()
        if not end:
            end = start.replace(days=+1)

        start = start.timestamp

        # TODO: multiple routes, getting there..
        single_route = routes

        # MongoDB aggregation match operator
        if type(account) is list:
            match = {
                'assigned': True,
                'start': {'$gte':start, '$lt':end},
                'channel': {'$regex': single_route['channel']},
                'dstchannel': {'$regex': single_route['dstchannel']},
                '$or': [{'accountcode':a} for a in account]
            }
        else:
            match = {
                'accountcode': account, 
                'assigned': True,
                'start': {'$gte':start, '$lt': end},
                'channel': {'$regex': single_route['channel']},
                'dstchannel': {'$regex': single_route['dstchannel']},
            }
    
        # MongoDB aggregation project operator
        project = {
               "_id" : 0,
               # record duration seconds
               "duration" : 1,
               # record billing seconds
               "billsec" : 1,
               # record times
               "start" : 1,
               'answer': 1,
               'end': 1,
        
               "year" : {
                         "$year" : "$start"
               },
               "month" : {
                          "$month" : "$start"
               },
               "week" : {
                         "$week" : "$start"
               },
               "day" : {  
                        "$dayOfMonth" : "$start"
               },
               "hour" : {  
                         "$hour" : "$start"
               },
               "minute" : {  
                           "$minute" : "$start"
               },
               "second" : {
                           "$second" : "$start"
               }
        }
        
        # MongoDB aggregation group operator
        group = {
            '_id': {
                'start': '$start',
                'answer': '$answer',
                'end': '$end',
                
                'year': '$year',
                'month': '$month',
                'week':'$week',        
                'day': '$day',
                'hour':'$hour',
                'minute': '$minute',
                'second': '$second',
            },
            'records': {
                '$sum': 1
            },
            'average': {
                '$avg':'$seconds'
            },
            'duration': {
                '$sum':'$duration'
            },
            'seconds': {
                '$sum':'$seconds'
            }
        }
        
        # MongoDB aggregation pipeline
        pipeline = [
            {'$match':match},
            {'$project':project},
            {'$group':group}
        ]
        

        result = yield self.db.records.aggregate(pipeline)

        raise gen.Return(result.get('result'))

    @gen.coroutine
    def remove_record(self, record_uuid):
        '''
            Remove a record entry
        '''
        result = yield self.db.records.remove({'uuid':record_uuid})
        raise gen.Return(result)

    @gen.coroutine
    def replace_record(self, struct):
        '''
            Replace a existent record entry
        '''
        # put implementation
        pass

    @gen.coroutine
    def resource_options(self):
        '''
            Return resource options
        '''
        # options implementation
        pass

    @gen.coroutine
    def modify_record(self, struct):
        '''
            Modify a existent record entry
        '''
        # patch implementation
        pass