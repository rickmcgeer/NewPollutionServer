#!/usr/bin/python
from mapping import *


def zeroVector(n):
    return [base64[0] for i in range(0, n)]


def exponentialEncode(aValue):
    if (aValue < 0):
        return 0
    if (aValue < 256):
        return int(math.floor(aValue * 60.0/256))
    if (aValue < 512): return 60
    if (aValue < 1024): return 61
    if (aValue < 2048): return 62
    return 63

def base64Encode(aValue):
    return base64[exponentialEncode(aValue)]

def monthStr(aMonth):
    if aMonth < 10:
        return '0%d' % aMonth
    else:
        return '%d' % aMonth

def getDataFromFile(year, month, pointsPerDegree):
    monthString = monthStr(month)
    f1 = open('%d/%s/PM25_%d_%s_average_%d.csv' % (year, monthString, year, monthString, pointsPerDegree))
    dataAsStrings = f1.read().split('\n')[1:]
    f1.close()
    dataAsStrings = filter(lambda x: len(x) == 5, [d.split(',') for d in dataAsStrings])
    return [[Coordinate(float(data[2])/10, float(data[3])/10), float(data[4])] for data in dataAsStrings]

def convertToBase64(year, month, pointsPerDegree):
    dataSet = getDataFromFile(year, month, pointsPerDegree)
    result = [base64Encode(data[1]) for data in dataSet]
    return ''.join(result)


def makeBase64(year, month, pointsPerDegree):
    resultVector = zeroVector(fullSetSize(pointsPerDegree))
    dataSet = getDataFromFile(year, month, pointsPerDegree)
    for data in dataSet:
        datasetIndex = DatasetIndex(data[0], pointsPerDegree)
        base64Index = exponentialEncode(data[1])
        resultIndex = datasetIndex.indexIntoDataSet()

        try:
            resultVector[resultIndex] = base64[base64Index]
        except IndexError:
            reportStr = 'Index Error: year %d. month %d, data set index %s, data set values %s, base64Index %d'
            values = (year, month, resultIndex, repr(datasetIndex), base64Index)
            print  reportStr % values
    return ''.join(resultVector)

years = range(1998, 2015)
fullMonths = range(1, 13)
partYears = [{'year': 1997, 'months': range(9, 13)}, {'year':2015, 'months': [1]}]
resolutions = [1, 2, 4, 10]

def getYear(aYear, months):
    return [{'month': month, 'res':res, 'data': makeBase64(aYear, month, res)} for month in months for res in resolutions]


def getFile(aYear):
    return open('pyData/data_%d.py' % aYear, 'w')

def getHeader(year, months):
    headerStrings = ['#!/usr/bin/python',
        '# base64 encoding of the data for the year %d' % year,
        '# see RFC 4648 for the encoding, Table 1, page 5.  The result is in',
        '# data[%d][month][res] for each month and resolution' % year,
        '# the data is a string, encoded in base64, the world in',
        '# row-major order, starting from the international date line and going east',
        '# and from the north pole and going south.  We use the same mapping.py',
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

def genYear(aYear, months):
    file = getFile(aYear)
    printHeader(file, aYear, months)
    result = getYear(aYear, months)
    for value in result:
        file.write('data[%d][%d][%d] = "%s"\n' % (aYear, value['month'], value['res'], value['data']))
    file.close()

def fullDB():
    for year in years:
        genYear(year, fullMonths)
    for partYear in partYears:
        genYear(partYear['year'], partYear['months'])
