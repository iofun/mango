# -*- coding: utf-8 -*-
'''
    Mango tasks system logic functions.
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.

__author__ = 'Jean Chassoul'


import logging

import arrow
import motor

import uuid

# import numpy as np
import pandas as pd

from tornado import gen

from mango.messages import tasks
from mango.messages import reports

from mango.tools import clean_structure
from mango.tools import clean_results
from mango.tools import check_times


class Tasks(object):
    '''
        Tasks resources
    '''

    @gen.coroutine
    def get_task(self, account, task_uuid):
        '''
            Get a detail task
        '''
        if not account:
            task = yield self.db.tasks.find_one({'uuid':task_uuid},{'_id':0})
        else:

            # change accountcode to account, because the accountcode is a uuid
            # and we're expecting an account name.

            task = yield self.db.tasks.find_one({'uuid':task_uuid,
                                                     'account':account},
                                                    {'_id':0})
        try:
            if task:
                task = tasks.Task(task)
                task.validate()
        except Exception, e:
            logging.exception(e) # catch some daemon here!
            raise e
        finally:
            raise gen.Return(task)

    @gen.coroutine
    def get_task_list(self, account, start, end, lapse, status, page_num):
        '''
            Get detail tasks 
        '''
        page_num = int(page_num)
        page_size = self.settings['page_size']
        task_list = []
        message = None
        query = {'public':False}

        if status != 'all':
            query['status'] = status
        
        if not account:
            query = self.db.tasks.find(query,
                                       {'_id':0, 'comments':0})
        elif type(account) is list:
            accounts = [{'accountcode':a, 'assigned': True} for a in account]
            query = self.db.tasks.find({'$or':accounts},
                                       {'_id':0, 'comments':0})
        else:
            query = self.db.tasks.find({'accountcode':account,
                                        'assigned':True},
                                       {'_id':0, 'comments':0})
        
        query = query.sort([('uuid', -1)]).skip(page_num * page_size).limit(page_size)
        
        try:
            
            while (yield query.fetch_next):
                result = query.next_object()
                task_list.append(tasks.Task(result))

        except Exception, e:
            logging.exception(e)
            raise e

        try:
            struct = {'results': task_list}

            # reports BaseGoal? da faq??
            
            message = reports.BaseGoal(struct)
            message.validate()
            message = clean_results(message)

        except Exception, e:
            logging.exception(e)
            raise e
        finally:
            raise gen.Return(message)
    
    @gen.coroutine
    def get_unassigned_tasks(self, start, end, lapse, page_num):
        '''
            Get unassigned tasks
        '''
        page_num = int(page_num)
        page_size = self.settings['page_size']
        result = []
        
        # or $exist = false ?

        query = self.db.tasks.find({'assigned':False})
        query = query.sort([('uuid', -1)]).skip(page_num * page_size).limit(page_size)
        
        try:
            for task in (yield query.to_list()):
                result.append(tasks.Task(task))
            
            struct = {'results':result}

            results = reports.BaseResult(struct)
            results.validate()
        except Exception, e:
            logging.exception(e)
            raise e

        results = clean_results(results)        
        raise gen.Return(results)


    @gen.coroutine
    def new_task(self, struct):
        '''
            Create a new task entry
        '''
        try:
            task = tasks.Task(struct)
            task.validate()
        except Exception, e:
            logging.exception(e)
            raise e

        task = clean_structure(task)

        result = yield self.db.tasks.insert(task)

        raise gen.Return(task.get('uuid'))

    @gen.coroutine
    def set_assigned_flag(self, account, task_uuid):
        '''
            Set the task assigned flag
        '''
        logging.info('set_assigned_flag account: %s, task: %s' % (account, task_uuid))

        result = yield self.db.tasks.update(
                                {'uuid':task_uuid, 
                                 'accountcode':account}, 
                                {'$set': {'assigned': True}})
        
        raise gen.Return(result)

    @gen.coroutine
    def remove_task(self, task_uuid):
        '''
            Remove a task entry
        '''
        result = yield self.db.tasks.remove({'uuid':task_uuid})
        raise gen.Return(result)

    @gen.coroutine
    def modify_task(self, account, task_uuid, struct):
        '''
            Modify task
        '''
        try:
            logging.info(struct)
            task = tasks.ModifyTask(struct)
            task.validate()
            task = clean_structure(task)
        except Exception, e:
            logging.error(e)
            raise e

        try:
            result = yield self.db.tasks.update(
                {'account':account,
                 'uuid':task_uuid},
                {'$set':task}
            )
            logging.info(result)            
        except Exception, e:
            logging.error(e)
            message = str(e)

        raise gen.Return(bool(result.get('n')))

    @gen.coroutine
    def replace_task(self, struct):
        '''
            Replace a existent task entry
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