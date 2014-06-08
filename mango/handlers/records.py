# -*- coding: utf-8 -*-
'''
    Mango HTTP records handlers.
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Jean Chassoul'


import time
import arrow
import motor

# import numpy as np
import pandas as pd

from bson import json_util

from tornado import gen
from tornado import web

from mango.system import accounts
from mango.system import records

from mango.tools import content_type_validation
from mango.tools import check_json
from mango.tools import check_times
from mango.tools import errors

from mango.handlers import BaseHandler


@content_type_validation
class Handler(records.Records, accounts.Accounts, BaseHandler):
    '''       
        Records resource handler
    '''

    @web.asynchronous
    @gen.engine
    def get(self, record_uuid=None, start=None, end=None, page_num=0, lapse='hours'):
        '''
            Mango records get handler

            Get record objects
        '''
        if record_uuid:
            record_uuid = record_uuid.rstrip('/')

            if self.current_user:
                user = self.current_user
                record = yield motor.Op(self.get_record, user, record_uuid)
            else:
                record = yield motor.Op(self.get_record, None, record_uuid)

            if not record:
                self.set_status(400)
                system_error = errors.Error('missing')
                error = system_error.missing('record', record_uuid)
                self.finish(error)
                return

            self.finish(record)
            return

        if self.current_user:
            user = self.current_user
            orgs = yield motor.Op(self.get_orgs_list, user)

            accounts = (orgs['orgs'] if orgs else False)

            print('WARNING:', user, orgs, ' on GET records.')

            if not accounts:
                result = yield motor.Op(self.get_record_list,
                                        account=user, 
                                        lapse=lapse,
                                        start=start,
                                        end=end,
                                        page_num=page_num)
            else:
                accounts.append(user)
                result = yield motor.Op(self.get_record_list,
                                        account=accounts,
                                        lapse=lapse,
                                        start=start,
                                        end=end,
                                        page_num=page_num)
        else:
            result = yield motor.Op(self.get_record_list,
                                    account=None,
                                    lapse=lapse,
                                    start=start,
                                    end=end,
                                    page_num=page_num)
        
            result = json_util.dumps(result)

        self.finish(result)

    @web.asynchronous
    @gen.engine
    def post(self):
        '''
            Mango records post handler

            Register a record detail record
        '''

        result = yield gen.Task(check_json, self.request.body)
        struct, error = result.args
        
        if error:
            self.set_status(400)
            self.finish(error)
            return

        result = yield motor.Op(self.new_detail_record, struct)
 
        # Warning missing crash_and_die errors handlers.

        if error:
            print('error 2')
            error = str(error)
            system_error = errors.Error(error)

            # Error handling 409?
            
            self.set_status(400)
        
        if error and 'Model' in error:
            error = system_error.model('Records')
            self.finish(error)
            return
        elif error and 'duplicate' in error:
            error = system_error.duplicate('Record', 'uniqueid', struct['uniqueid'])
            self.finish(error)
            return
        elif error:
            print('error 3')
            self.finish(error)
            return
        
        if 'accountcode' in struct:
            account = struct['accountcode']

            resource = {'account': account, 'resource':'records', 'uuid':result}

            exist = yield motor.Op(self.check_exist, account)

            if exist:
                
                update = yield motor.Op(self.new_resource, resource)

                flag = yield motor.Op(self.set_assigned_flag,
                                      account,
                                      result)

                print('after flag')


        self.set_status(201)
        self.finish({'id':result})

    @web.authenticated
    @web.asynchronous
    @gen.engine
    def put(self):
        '''
            Mango records put handler
        '''
        pass

    @web.authenticated
    @web.asynchronous
    @gen.engine
    def delete(self, record_uuid):
        '''
            Mango records delete handler

            Remove a record register
        '''
        record_uuid = record_uuid.rstrip('/')
        result = yield motor.Op(self.remove_cdr, record_uuid)

        if not result['n']:
            self.set_status(400)
            system_error = errors.Error('missing')
            error = system_error.missing('record', record_uuid)
            self.finish(error)
            return

        self.set_status(204)
        self.finish()

    @web.authenticated
    @web.asynchronous
    @gen.engine
    def patch(self):
        '''
            Mango records patch handler
        '''
        pass


@content_type_validation
class PublicHandler(records.Records, BaseHandler):
    '''
        Mango public records handler
        
        Public records handler
    '''
    
    @web.asynchronous
    @gen.engine
    def get(self, page_num=0):
        '''
            Mango public records get handler

            Get public record details
        '''
        # get public details: record get_record_list without an account
        account = None
        result = yield motor.Op(self.get_record_list,
                                       account=account,
                                       lapse=None,
                                       start=None,
                                       end=None,
                                       page_num=page_num)
        
        self.finish({'results': result})

@content_type_validation
class UnassignedHandler(records.Records, BaseHandler):
    '''
        Mango records unassigned handler

        Records unassigned requests handler
    '''
    
    @web.asynchronous
    @gen.engine
    def get(self, page_num=0):
        '''
            Mango unassigned records get handler

            Get unassigned record details
        '''
        result = yield motor.Op(self.get_unassigned_records, 
                                        lapse=None,
                                        start=None,
                                        end=None,
                                        page_num=page_num)
        self.finish(result)


@content_type_validation
class SummaryHandler(records.Records, accounts.Accounts, BaseHandler):
    '''
        Summary handler 
    '''

    #@web.authenticated
    @web.asynchronous
    @gen.engine
    def get(self, account=None, start=None, end=None, lapse='hours', page_num=0):
        '''
            Get record summary

            arguments: account, start, end, lapse, page.

            - account or list of accounts
            - start timestamp
            - end timestamp
            - lapse of time
            - page number
        '''
        result = 0
        minutes = 0
        record_avg = 0

        if not account:
            account = self.current_user

        orgs = yield motor.Op(self.get_orgs_list, account)
        accounts = (orgs['orgs'] if orgs else False)

        if accounts:
            accounts.append(account)
            summary = yield motor.Op(self.get_summary,
                                     account=accounts,
                                     start=start,
                                     end=end,
                                     lapse=lapse
                                     )
        else:
            summary = yield motor.Op(self.get_summary,
                                     account=account,
                                     start=start,
                                     end=end,
                                     lapse=lapse
                                     )

        if summary:
            
            dates = [record['_id'] for record in summary]
            
            for _x in summary:
                del _x['_id']
            
            frame = pd.DataFrame(summary)
            frame = frame.join(pd.DataFrame(dates))
        
            if lapse:
                lapse = lapse.rstrip('/')

                if 'hours' in lapse:
                    # pandas data-frames
                    frame['minutes'] = frame['billsecs'] / 60
                    
                    # research pandas dataframe set_index
                    hours = frame[['records', 'minutes', 'start']].groupby('start').sum()
                    
                    # get a dict of results from the data-frame
                    result =  dict(hours['records'])
                    minutes = dict(hours['minutes'])
                    
                    result = {         
                        time.mktime(key.timetuple()): int(result[key]) 
                        for key in result
                    }            
                    
                    minutes = {
                        time.mktime(key.timetuple()): int(minutes[key])
                        for key in minutes
                    } 
                                        
                    # return the clean version of the data
                    self.finish({
                        'records': result, 
                        'minutes': minutes
                    })

                    return
            
            result = frame['records'].sum()
            seconds = frame['billsecs'].sum()
            average = frame['average'].sum()
        
            minutes = seconds / 60
            min_avg = average / 60
            
            record_avg = round(min_avg / result)
        
        self.finish({'records': int(result),
                     'minutes': int(minutes),
                     'record_avg': int(record_avg)})


@content_type_validation
class SummariesHandler(records.Records, accounts.Accounts, BaseHandler):
    '''
       Summaries requests handler.
    '''
    
    #@web.authenticated
    @web.asynchronous
    @gen.engine
    def get(self, account=None, start=None, end=None, lapse=None, page_num=0):
        '''
            Get summaries

            arguments: account, start, end, lapse, page_num.

            - account or list of accounts
            - start timestamp
            - end timestamp
            - time lapse
            - page number
        '''
        result = 0
        minutes = 0
        record_avg = 0

        times = yield motor.Op(check_times, start, end)

        if not account:
            account = self.current_user

        orgs = yield motor.Op(self.get_orgs_list, account)
        accounts = (orgs['orgs'] if orgs else False)

        if accounts:
            accounts.append(account)
            summary = yield motor.Op(self.get_summary, 
                                     account=accounts,
                                     lapse=lapse,
                                     start=times['start'],
                                     end=times['end'])
        else:
            summary = yield motor.Op(self.get_summary,
                                     account=account,
                                     lapse=lapse,
                                     start=times['start'],
                                     end=times['end'])
        if summary:

            print("WARNING: remove record['_id']: %s from query." % (record['_id'],))
            
            dates = [record['_id'] for record in summary]
            
            for x in summary:
                del x['_id']
            
            frame = pd.DataFrame(summary)
            frame = frame.join(pd.DataFrame(dates))
        
            if lapse:
                lapse = lapse.rstrip('/')

                print('lapse on handler:', lapse)
            
                if 'hours' in lapse:
                    # pandas data-frames
                    frame['minutes'] = frame['billsecs'] / 60
                    
                    # research pandas dataframe set_index
                    hours = frame[['records', 'minutes', 'start']].groupby('start').sum()
                    
                    # get a dict of results from the data-frame
                    result =  dict(hours['records'])
                    minutes = dict(hours['minutes'])
                    
                    result = {         
                        time.mktime(key.timetuple()): int(result[key]) 
                        for key in result
                    }            
                    
                    minutes = {
                        time.mktime(key.timetuple()): int(minutes[key])
                        for key in minutes
                    } 
                                        
                    # return the clean version of the data
                    self.finish({
                        'records': result, 
                        'minutes': minutes
                    })
                    return
            
            result = frame['result'].sum()
            seconds = frame['billsecs'].sum()
            average = frame['average'].sum()
        
            minutes = seconds / 60
            min_avg = average / 60
            
            record_avg = round(min_avg / result)
        
        self.finish({'records': int(result),
                     'minutes': int(minutes),
                     'record_avg': int(record_avg)})