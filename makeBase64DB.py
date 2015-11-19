#!/usr/bin/python
from mapping import *

def zeroVector(n):
    return [base64[0] for i in range(0, n)]

class Base64Encoder:
    def __init__(self, maxX, maxY):
        self.maxY = min(maxY, 63)
        self.maxX = maxX
        self.slope = self.maxY/self.maxX
        self.bitOffset = maxX.bit_length()

    def encode(self, aValue):
        if aValue < 0: return 0
        if (aValue <= self.maxX):
            return int(round(self.slope * aValue))
        logAValue = int(aValue).bit_length()
        return min((logAValue - self.bitOffset) + self.maxY, 63)



def makeBase64(year, month, pointsPerDegree, base64Encoder):
    resultVector = zeroVector(fullSetSize(pointsPerDegree))
    for data in pm25[year][month][pointsPerDegree]:
        datasetIndex = DatasetIndex(Coordinate(data[0], data[1]), offsetComputers[pointsPerDegree])
        base64Index = base64Encoder.encode(data[2])
        resultIndex = datasetIndex.indexIntoDataSet()
        try:
            resultVector[resultIndex] = base64[base64Index]
        except IndexError:
            reportStr = 'Index Error: year %d. month %d, data set index %s, data set values %s, base64Index %d'
            values = (year, month, resultIndex, repr(datasetIndex), base64Index)
            print reportStr % values
    return ''.join(resultVector)

def parseAndCheck(aPointAsList, datasetSpecifier):
    if (not aPointAsList ):
        print 'Error: bad point in ' + datasetSpecifier
        return (True, None)
    if (len(aPointAsList) != 3):
        print 'Error: bad point %s read in %s' % (repr(aPointAsList), datasetSpecifier)
        return (True, None)
    try:
        result = [int(aPointAsList[0]), int(aPointAsList[1]), float(aPointAsList[2])]
    except ValueError:
        print 'Error: failed to convert one or more elements of %s in %s' % (repr(aPointAsList), datasetSpecifier)
        return (True, None)
    if (result[0] > 1800 or result[0] < -1800):
        print 'Bad Longitude value %d in %s in %s' % (result[0], repr(aPointAsList), datasetSpecifier)
        return (True, None)
    if (result[1] > 900 or result[1] < -900):
        print 'Bad Latitude value %d in %s in %s' % (result[1], repr(aPointAsList), datasetSpecifier)
        return (True, None)
    if (result[2] < 0):
        print 'Bad Data value %f in %s in %s' % (result[2], repr(aPointAsList), datasetSpecifier)
        return (True, None)
    return (False, result)



#
# Do a year/month/res triple
#
def base64EncodeYearMonthRes(year, month, res, base64Encoder, outfile):
    csvfile = open('newPM25/%d_%d_%d.csv' % (year, month, res), 'r')
    resultVector = zeroVector(fullSetSize(res))
    line = csvfile.readline()
    datasetSpecifier = 'year = %d, month=%s, res=%d' % (year, month, res)
    offsetComputer = offsetComputers[res]
    while (len(line) > 0):
        dataAsList = line.split(',')
        (error, aPointAsList) = parseAndCheck(dataAsList, datasetSpecifier)
        if (error): continue
        datasetIndex = DatasetIndex(Coordinate(aPointAsList[0], aPointAsList[1]), offsetComputer)
        base64Index = base64Encoder.encode(aPointAsList[2])
        resultIndex = datasetIndex.indexIntoDataSet()
        resultVector[resultIndex] = base64[base64Index]
    outfile.write('data[%d][%d][%d] = "%s"\n' % (year, month, res, ''.join(resultVector)))
    csvfile.close()

#
# Do a Month
#
def base64EncodeYearMonth(year, month, base64Encoder, outfile):
    for res in [1, 2, 4, 10]:
        base64EncodeYearMonthRes(year, month, res, base64Encoder, outfile)

#
# Do a Year
#
def base64EncodeYear(year, months, base64Encoder):
    outfile = open('pyData/data_%d.py' % year, 'w')
    printHeader(outfile, year, months)
    for month in months:
        base64EncodeYearMonth(year, month, base64Encoder, outfile)
    outfile.close()




years = range(1998, 2015)
fullMonths = range(1, 13)
partYears = [{'year': 1997, 'months': range(9, 13)}, {'year':2015, 'months': [1]}]
resolutions = [1, 2, 4, 10]

offsetComputers = {
    4: OffsetComputer(4, [0, 2, 4, 7, 9]),
    2: OffsetComputer(2, [0, 5]),
    1: OffsetComputer(1, [9]),
    10: OffsetComputer(10, range(0, 10))
}



def getYear(aYear, months, base64Encoder):
    return [{'month': month, 'res':res, 'data': makeBase64(aYear, month, res, base64Encoder)} for month in months for res in resolutions]


def getFile(aYear):
    return open('pyData/data_%d.py' % aYear, 'w')

def getHeader(year, months):
    headerStrings = ['#!/usr/bin/python',
        '# base64 encoding of the data for the year %d' % year,
        '# see RFC 4648 for the encoding, Table 1, page 5.  The result is in',
        '# data[%d][month][res] for each month and resolution' % year,
        '# the data is a string, encoded in base64, the world in',
        '# row-major order, starting from the international date line and going east',
        '# and from the south pole and going north.  We use the same mapping.py',
        '# file to both generate this data file and to use it in the server',
        'data[%d] = {}' % year]
    for month in months:
        headerStrings.append('data[%d][%d] = {}' % (year, month) )
    return headerStrings

def printHeader(file, year, months):
    headerStrings = getHeader(year, months)
    result = '\n'.join(headerStrings)
    file.write(result)
    file.write('\n')

def genYear(aYear, months, base64Encoder):
    file = getFile(aYear)
    global pm25
    pm25[aYear] = {}
    for month in months:
        execfile('newPM25/%d_%d.py' % (aYear, month))
    printHeader(file, aYear, months)
    result = getYear(aYear, months, base64Encoder)
    for value in result:
        file.write('data[%d][%d][%d] = "%s"\n' % (aYear, value['month'], value['res'], value['data']))
    file.close()

def doRes(aYear, aMonth, res, base64Encoder, file):
    file.write('data[%d][%d][%d] = "%s"\n' % (aYear, aMonth, res, makeBase64(aYear, aMonth, res, base64Encoder)))

def doMonth(aYear, aMonth, base64Encoder, file):
    for res in [1, 2, 4, 10]:
        doRes(aYear, aMonth, res, base64Encoder, file)
    pm25[aYear][aMonth] = {}


def doYear(aYear, months, base64Encoder):
    file = getFile(aYear)
    global pm25
    pm25[aYear] = {}
    printHeader(file, aYear, months)
    for month in months:
        execfile('newPM25/%d_%d.py' % (aYear, month))
        doMonth(aYear, month, base64Encoder, file)
    pm25[aYear] = {}
    file.close()

def doYears(yearList):
    base64Encoder = Base64Encoder(60, 60)
    global pm25
    pm25 = {}
    for year in yearList:
        doYear(year, fullMonths, base64Encoder)


def fullDB():
    base64Encoder = Base64Encoder(60, 60)
    global pm25
    pm25 = {}
    for year in years:
        doYear(year, fullMonths, base64Encoder)
    for partYear in partYears:
        doYear(partYear['year'], partYear['months'], base64Encoder)
