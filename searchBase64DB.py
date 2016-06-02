from mapping import *
#
# middleware to search the DB.  The functions here are called by the server.
# written separately to permit easy on-host testing
#
#
from os import listdir
from os.path import isfile, join
from config import dataDirectory
from loadManager import DataManager


offsetComputers = {
    4: OffsetComputer(4, [0, 2, 4, 7, 9]),
    2: OffsetComputer(2, [0, 5]),
    1: OffsetComputer(1, [9]),
    10: OffsetComputer(10, range(0, 10))
}


#
# Utility to check that a query is OK.  This should be called
# only when we haven't checked previously.  This checks to make sure
# we have the data and that the bounds are OK.  Returns a pair
# (T/F, message), where the message explains the problem if one was detected
#
def checkQuery(dataManager, year, month, res, nwLat, seLat, nwLon, seLon):
    if not dataManager.checkLoadable(year, month, res):
        return (False, "No Dataset for %s" % convertToString(year, month, res))
    for lat in [nwLat, seLat]:
        if (lat < -90 or lat > 90):
            return (False, "Latitude must be in [-90, 90], not %f" % lat)
    for lon in [nwLon, seLon]:
        if (lon < -180 or lon > 180):
            return (False, "Longitude must be in [-180, 180], not %f" % lon)
    return (True, "OK")

#
# Pull the dataset from the data manager, returning either the data set with the
# requested resolution, or, if that is not available but loadable, the best loaded
# resolution and kick off the load request so the next request for this data will hit
#
def getBestAvailableData(dataManager, year, month, res):
    if dataManager.hasDataSet(year, month, res):
        return res, dataManager.getData(year, month, res)
    bestRes = dataManager.bestResolution(year, month)
    result = dataManager.getData(year, month, bestRes)
    if dataManager.checkLoadable(year, month, res):
        dataManager.asynchLoad(year, month, res)
    return bestRes, result
#
# Actually Search the DB for a matching string.  No checking: call first if
# you want this checked.  Result is a String, row-major order
#
def searchDB(dataManager, year, month, res, north, south, west, east):
    res, dataSet = getBestAvailableData(dataManager, year, month, res)
    return getData(north, south, west, east, offsetComputers[res], dataSet)


#
# Actually Search the DB for a matching string.  No checking: call first if
# you want this checked.  Result is a list of sequences, one per row
#
def searchDBReturnRows(dataManager, year, month, res, north, south, west, east, optimizeSingleRectangleCase):
    res, dataSet = getBestAvailableData(dataManager, year, month, res)
    return getDataAsSequences(north, south, west, east, offsetComputers[res], dataSet, optimizeSingleRectangleCase)

#
# count the number of zeros in a string
#
def countNonZero(aBase64String):
    return len([x for x in aBase64String if x != 'A'])

import time

#
# get the statistics for a search as a dictionary with two entries, pts and ms
#
def getStats(dataManager, year, month, res, north, south, west, east):
    start = time.time()
    result = searchDB(dataManager, year, month, res, north, south, west, east)
    end = time.time()
    nonzero = countNonZero(result['base64String'])
    rectResult = searchDBReturnRows(dataManager, year, month, res, north, south, west, east, False)
    s1 = time.time()
    rectangles = convertToRectangles(rectResult, False)
    res1 = '[' + '.'.join(rectangles) + ']'
    e1 = time.time()
    s2 = time.time()
    rectangles = convertToRectangles(rectResult, True)
    res2 = '[' + '.'.join(rectangles) + ']'
    e2 = time.time()
    numRects = len(rectangles)
    result = {'pts': len(result['base64String']), 'nonzero': nonzero, 'search(ms)': (end - start) * 1000}
    result.update({'rectangles': numRects, 'convertTime(lat/lon)(ms)': (e1 - s1) * 1000})
    result.update({'rectangle bytes(lat/lon)': len(res1), 'converTime(indices)(ms)': (e2 - s2) * 1000})
    result.update({'rectangle bytes(indices)': len(res2)})
    return result

#
# Convert a sequence with a latitude, an increment, and a longitude into a list of
# Rectangles
#
def convertSequenceToRectangles(latitude, firstLon, increment, sequence):
    result = []
    currentValue = sequence[0]
    startLon  = firstLon
    lon = firstLon
    for index in range(1, len(sequence)):
        if sequence[index] == currentValue:
            lon += increment
            continue
        value = base64.index(currentValue)
        if value != 0:
            result.append('(%d,%d,%d,%d)' %  (value, latitude, startLon, lon))
        currentValue = sequence[index]
        lon += increment
        startLon = lon
    value = base64.index(sequence[-1])
    if value != 0:
        result.append('(%d,%d,%d,%d)' % (value, latitude, startLon, lon))
    return result

#
# Convert a sequence with a latitude, an increment, and a longitude into a list of
# Rectangles
#
def convertSequenceToSimpleRectangles(rowNum, sequence):
    result = []
    currentValue = sequence[0]
    firstIndex = 0
    for index in range(1, len(sequence)):
        if sequence[index] == currentValue:
            continue
        value = base64.index(currentValue)
        if value != 0:
            result.append('(%d,%d,%d,%d)' % (value, rowNum, firstIndex, index))
        currentValue = sequence[index]
        firstIndex = index + 1
    value = base64.index(sequence[-1])
    if value != 0:
        result.append('(%d,%d,%d,%d)' % (value, rowNum, firstIndex, len(sequence) - 1))
    return result

#
# convert a search result into a set of rectangles
#
def convertToRectangles(aSearchResult, doIndicesOnly):
    increment = 10/aSearchResult['pointsPerDegree']
    firstLon = aSearchResult['swCorner']['lon']
    lat = aSearchResult['swCorner']['lat']
    rectangles = []
    index = 0
    for sequence in aSearchResult['sequences']:
        if (doIndicesOnly):
            rectangles.extend(convertSequenceToSimpleRectangles(index, sequence))
        else:
            rectangles.extend(convertSequenceToRectangles(lat, firstLon, increment, sequence))
        lat += increment
        ++index
    return rectangles
