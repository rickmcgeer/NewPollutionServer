#!/usr/bin/python
import datetime
import sys
import os
import json
execfile('searchBase64DB.py')
from config import port

from flask import Flask
from flask import request
from flask.ext.cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

#
# Dig out a  field, convert it using convertFunction, and check the result
# using checkFunction.  convertFunction should be something which takes a string
# and returns the right type, throwing a ValueError if there is a problem.  checkFunction
# takes a single parameter and returns True if it's valid, False otherwise.  Annotates
# requestResult either with the  value or with the error message if there is one.  This
# is designed to be called multiple times with the same requestResult, so error, once
# set to True, should never be set to False.
#


def getField(request, requestResult, fieldName, convertFunction, checkFunction):
    value = request.args.get(fieldName)
    if (not value):
        requestResult['error'] = True
        requestResult['message'] += 'fieldName %s missing.  ' % fieldName
    try:
        val = convertFunction(value)
        if (checkFunction(val)):
            requestResult[fieldName] = val
        else:
            requestResult['error'] = True
            requestResult['message'] += 'validity check failed for field %s, value %s' % (fieldName, value)
    except ValueError:
        requestResult['error'] = True
        requestResult['message'] += 'conversion function failed for fieldName %s, not %s.  ' % (fieldName, value)

#
# Parse a request and return the result.  The specifications
# are the fields, so all this does is iterate over the fields
# provided as arguments
#
def parseRequest(request, fields):
    result = {'error': False, 'message': ''}
    for (fieldName, conversion, checkFunction) in fields:
        getField(request, result, fieldName, conversion, checkFunction)
    return result

basicParseFields = [('year', int, lambda x: x in range(1997, 2016)),
          ('month', int, lambda x: x in range(1, 13)),
          ('res', int, lambda x: x in [1, 2, 4, 10])
          ]

fullParseFields = basicParseFields + [
        ('nwLat', float, lambda x: x < 90.0 and x > -90.0),
        ('seLat', float, lambda x: x < 90.0 and x > -90.0),
        ('nwLon', float, lambda x: x < 180.0 and x > -180.0),
        ('seLon', float, lambda x: x < 180.0 and x > -180.0),
    ]

#
#  Turn a structure into a string
#

@app.route('/test')
def test_basic():
    result = parseRequest(request, basicParseFields)
    if result['error']:
        return 'Error in request ' + result['message']
    else:
        return json.dumps(result)

@app.route('/test_full')
def test_full():
    result = parseRequest(request, fullParseFields)
    if result['error']:
        return 'Error in request ' + result['message']
    else:
        return json.dumps(result)

def parseAndCheck(request):
    query = parseRequest(request, fullParseFields)
    if query['error']:
        query['message'] = 'Error in request ' + query['message']
        return query
    if (not checkDatasetExists(query['year'], query['month'], query['res'])):
        query['error'] = True
        query['message'] = "Dataset %s is not loaded" % convertToString(query['year'], query['month'], query['res'])
    else:
        query['error'] = False
    return query

@app.route('/get_time')
def get_times():
    query = parseAndCheck(request)
    if (query['error']):
        return query['message']
    stats = getStats(query['year'], query['month'], query['res'],
               query['nwLat'], query['seLat'], query['nwLon'], query['seLon'])
    return 'Found %d points in %f milliseconds' % (stats['pts'], stats['ms'])

@app.route('/show_inventory')
def get_inventory():
    datafileList = 'Datafiles: %s' + ', '.join(datafiles)
    inventory = '\n'.join(getInventory())
    return datafileList + '\nData sets loaded\n' + inventory

@app.route('/get_data')
def get_data():
    query = parseAndCheck(request)
    if (query['error']):
        return query['message']
    return searchDB(query['year'], query['month'], query['res'],
               query['nwLat'], query['seLat'], query['nwLon'], query['seLon'])

@app.route('/get_data_readable')
def get_data():
    query = parseAndCheck(request)
    if (query['error']):
        return query['message']
    sequences = searchDBReturnRows(query['year'], query['month'], query['res'],
               query['nwLat'], query['seLat'], query['nwLon'], query['seLon'])
    return '\n'.join(sequences)

if __name__ == '__main__':
    # for fileName in yearFiles:
    #     execfile(fileName)
    # print memory()
    app.debug = True
    loadDataSet()
    printInventory()
    checkExistenceSanityCheck()
    app.run(host='0.0.0.0', port=port)
