# -*- coding: utf-8 -*-

# This file is part of mango.

# Distributed under the terms of the last AGPL License.
# The full license is in the file LICENCE, distributed as part of this software.


__author__ = 'Space Beam'


import time
import arrow
import csv
import ujson as json
import logging
import uuid
from tornado import gen


def validate_uuid4(uuid_string):
    '''
        Validate that a UUID string is in
        fact a valid uuid4.

        Happily, the uuid module does the actual
        checking for us.
    '''
    try:
        val = uuid.UUID(uuid_string, version=4)
    except ValueError:
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        return False
    return str(val) == uuid_string

def clean_response(response, ignore):
    '''
        clean response
    '''
    return dict(
        (key.split('_register')[0], value)
        for (key, value) in response.items()
        if key not in ignore
    )

def get_search_item(solr, search_index, query, filter_query):
    '''
        Build and return the item query url
    '''
    return "https://{0}/search/query/{1}?wt=json&q={2}&fq={3}".format(
        solr, search_index, query, filter_query
    )

def get_search_list(solr, search_index, query, filter_query, start_num, page_size):
    '''
        Build and return the list query url
    '''
    # LOL WTF CLEAN THIS, PUT STUFF ON TUPLES OR SOMETHING ...
    return "https://{0}/search/query/{1}?wt=json&q={2}&fq={3}&start={4}&rows={5}&sort=created_at_register+desc, uuid_register+desc".format(solr, search_index, query, filter_query, start_num, page_size).replace(' ', '')
    
def get_average(total, marks):
    '''
        Get average from signals
    '''
    return float(total) / len(marks)

def get_percentage(part, whole):
    '''
        Get percentage of part and whole.

    '''
    return "{0:.0f}%".format(float(part)/whole * 100)

@gen.coroutine
def check_json(struct):
    '''
        Check for malformed JSON
    '''
    try:
        message = json.loads(struct)
    except Exception as error:
        message = json.dumps({'error':400})
        raise error
    return message

@gen.coroutine
def check_times(start, end):
    '''
        Check times
    '''
    try:
        start = (arrow.get(start) if start else arrow.get(arrow.utcnow().date()))
        end = (arrow.get(end) if end else start.replace(days=+1))
        message = {'start':start.timestamp, 'end':end.timestamp}
    except Exception as error:
        logging.exception(error)
        raise error
    return message

@gen.coroutine
def check_times_get_timestamp(start, end):
    '''
        Check times get timestamp
    '''
    try:
        start = (arrow.get(start) if start else arrow.get(arrow.utcnow().date()))
        end = (arrow.get(end) if end else start.replace(days=+1))
        message = {'start':start.timestamp, 'end':end.timestamp}
    except Exception as error:
        logging.exception(error)
        raise error    
    return message

@gen.coroutine
def check_times_get_datetime(start, end):
    '''
        Check times get datetime
    '''
    try:
        start = (arrow.get(start) if start else arrow.get(arrow.utcnow().date()))
        end = (arrow.get(end) if end else start.replace(days=+1))
        message = {'start':start.naive, 'end':end.naive}
    except Exception as error:
        logging.exception(error)
        raise error
    return message

def clean_message(struct):
    '''
        clean message
    '''
    struct = struct.to_native()
    struct = {
        key: struct[key]
            for key in struct
                if struct[key] is not None
    }
    return struct

def clean_structure(struct):
    '''
        clean structure
    '''
    struct = struct.to_primitive()
    struct = {
        key: struct[key]
            for key in struct
                if struct[key] is not None
    }
    return struct

def clean_results(results):
    '''
        clean results
    '''
    results = results.to_primitive()
    results = results.get('results')
    results = [
        {
            key: dic[key]
                for key in dic
                    if dic[key] is not None
        } for dic in results
    ]
    return {'results': results}

def str2bool(boo):
    '''
        String to boolean
    '''
    return boo.lower() in ('yes', 'true', 't', '1')

def export_to_csv(csv_file_path, dict_data):
    '''
        Tony's first attemp on general export_to_csv function
        TODO: Clean/finish it?
    '''
    csv_file = open(csv_file_path, 'w')
    writer = csv.writer(csv_file, dialect='excel')
    headers = dict_data[0].keys()
    writer.writerow(headers)
    for dat in dict_data:
        line = []
        for field in headers:
            line.append(dat[field])
        writer.writerow(line)
    csv_file.close()
