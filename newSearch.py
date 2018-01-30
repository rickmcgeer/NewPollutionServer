
#
# middleware to search the DB.  The functions here are called by the server.
# written separately to permit easy on-host testing
#
#
from os import listdir
from os.path import isfile, join
from config import dataDirectory
from loadManager import DataManager
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
    res, dataset = getBestAvailableData(dataManager, year, month, res)
    return getData(north, south, west, east, res, dataset)


#
# get the row number for a latitude, given res points per degree.
# aLatInTenths is in the range -900, 899, so we 
# 1. Add 900 to get it into the range (0, 1799)
# 2. multiply by res/10 -- for res 1, row 1 is at -890 which maps to 10, for res 2, -895, which maps to 5
# 3. Take the integer floor -- res 4 is not an even divisor of 10
#

def getRow(aLatInTenths, res):
	return int(math.floor((aLatInTenths + 900) * res/10))

#
# getCol.  Same as getRow but aLngInTenths is in the range -1800, 1799,  so
# add 1800 to get it in the range (0, 3599)
#

def getCol(aLngInTenths, res):
	return int(math.floor((aLngInTenths + 1800) * res/10))

def getData(north, south, west, east, res, dataset):
	result = getDataAsSequences(north, south, west, east, res, dataset)
	result['base64String'] = ''.join(result['sequences'])
	return result

def getCoordinate(row, col, res):
	return {"lat": row * 10/res - 900, "lon": col * 10/res - 1800}

def getDataAsSequences(north, south, west, east, res, dataset):
	pointsPerRow = 360 * res
	firstRow = getRow(south, res)
	lastRow = getRow(north, res)
	firstCol = getCol(west, res)
	lastCol = getCol(east, res) - 1
	sequences = [(firstCol + x * pointsPerRow, lastCol + x * pointsPerRow) for x in range(firstRow, lastRow)]
	data = [dataset[s[0]:s[1] + 1] for s in sequences]
	return  {'swCorner': getCoordinate(firstRow, firstCol, res), 'pointsPerRow': lastCol + 1 - firstCol, 'pointsPerDegree': res, 'sequences': data}

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



