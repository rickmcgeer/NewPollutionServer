from mapping import *
#
# middleware to search the DB.  The functions here are called by the server.
# written separately to permit easy on-host testing
#
#
from os import listdir
from os.path import isfile, join
from config import dataDirectory

datafiles = filter(lambda x: x.startswith('data_'), listdir(dataDirectory))
datafiles = filter(isfile, [join(dataDirectory, fileName) for fileName in datafiles])

data = {}
#
# initialize and read the data
#
def loadDataSet():
    global data
    data = {}
    for fileName in datafiles: execfile(fileName)

#
# Minimal initialize and read the data for debugging
#
def loadDataSetMin():
    global data
    data = {}
    execfile(join(dataDirectory, 'data_2006.py'))

offsetComputers = {
    4: OffsetComputer(4, [0, 2, 4, 7, 9]),
    2: OffsetComputer(2, [0, 5]),
    1: OffsetComputer(1, [9]),
    10: OffsetComputer(10, range(0, 10))
}


#
# Utilities to query the data
#
def getMonths(year):
    if year in data:
        return data[year].keys()
    else:
        return []

def getResolutions(year, month):
    if (year in data):
        if (month in data[year]):
            return data[year][month].keys()
    return 0

#
# Does a data set exist for year/month/res?
#
def checkDatasetExists(year, month, res):
    if (not year in data): return False
    if (not month in data[year]): return False
    if (not res in data[year][month]): return False
    return True

#
# Sanity check on data: is everything the right length?
#
def sanityCheck(year, month, res):
    if (checkDatasetExists(year, month, res)):
        return fullSetSize(res) == len(data[year][month][res])
    return False

def convertToString(year, month, res):
    return "year = %d, month = %d, res = %d" % (year, month, res)

#
# Sanity check and report
#
def sanityCheckAndReport(year, month, res):
    setReportStr = convertToString(year, month, res)
    sanityCheckReportString = 'Data set sanity check failed for %s, expected %d entries got %d'
    if (not checkDatasetExists(year, month, res)):
        print 'Data set %s does not exist' % setReportStr
        return
    if (not sanityCheck(year, month, res)):
        print sanityCheckReportString % (setReportStr, fullSetSize(res), len(data[year][month][res]))
#
# Iterate over  the entire data set, calling fun on each item
# fun should be a function that takes year, month, res
#
def iterateOverDataSetAndDo(fun):
    for year in data:
        for month in data[year]:
            for res in data[year][month]:
                fun(year, month, res)

#
# Do A sanity check over the whole data set
#
def fullSanityCheck():
    iterateOverDataSetAndDo(sanityCheckAndReport)

#
# print a year, month, res
#
def printReport(year, month, res):
    print convertToString(year, month, res)

#
# checkExistenceSanityCheckReport: designed to be called
# from checkExistenceSanityCheck -- just makes sure that
# checkDatasetExists returns True for all loaded data sets
#
def checkExistenceSanityCheckReport(year, month, res):
    if not checkDatasetExists(year, month, res):
        print 'Error: checkDatasetExists failed for ' + convertToString(year, month, res)
#
# Ensure checkDatasetExists returns True for all loaded data sets
#
def checkExistenceSanityCheck():
    iterateOverDataSetAndDo(checkExistenceSanityCheckReport)

#
# print an inventory of what we have
#
def printInventory():
    print 'Printing Inventory of loaded data.  '
    print 'Data Files are: ' + ', '.join(datafiles)
    iterateOverDataSetAndDo(printReport)

#
# getInventory: return everything we have loaded.  Should use the
# iterate meta but I need to figure out how to make that return a List
# returns a list of human-readable strings rather than tuples
#
def getInventory():
    result = []
    for year in data:
        for month in data[year]:
            for res in data[year][month]:
                result.append(convertToString(year, month, res))
    return result


#
# Now we get to it...actually searching the data
#

#
# Utility to check that a query is OK.  This should be called
# only when we haven't checked previously.  This checks to make sure
# we have the data and that the bounds are OK.  Returns a pair
# (T/F, message), where the message explains the problem if one was detected
#
def checkQuery(year, month, res, nwLat, seLat, nwLon, seLon):
    if not checkDatasetExists(year, month, res):
        return (False, "No Dataset for %s" % convertToString(year, month, res))
    for lat in [nwLat, seLat]:
        if (lat < -90 or lat > 90):
            return (False, "Latitude must be in [-90, 90], not %f" % lat)
    for lon in [nwLon, seLon]:
        if (lon < -180 or lon > 180):
            return (False, "Longitude must be in [-180, 180], not %f" % lon)
    return (True, "OK")
#
# Actually Search the DB for a matching string.  No checking: call first if
# you want this checked.  Result is a String, row-major order
#
def searchDB(year, month, res, north, south, west, east):
    return getData(north, south, west, east, offsetComputers[res], data[year][month][res])


#
# Actually Search the DB for a matching string.  No checking: call first if
# you want this checked.  Result is a list of sequences, one per row
#
def searchDBReturnRows(year, month, res, north, south, west, east):
    return getDataAsSequences(north, south, west, east, offsetComputers[res], data[year][month][res])
import time

#
# get the statistics for a search as a dictionary with two entries, pts and ms
#
def getStats(year, month, res, north, south, west, east):
    start = time.time()
    result = searchDB(year, month, res, north, south, west, east)
    end = time.time()
    return ({'pts': len(result), 'ms': (end - start) * 1000})
