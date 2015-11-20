#!/usr/bin/python
from searchBase64DB import *

# A search rectangle is a tuple (north, west, south, east)
# where each unit is measured in tenths of degrees
searchRectangles = [
   (899, 1799, -899, -1799),   # Whole world
   (51, -1799, 49, 1799),      # cross the dateline
   (50, -1300, 30, -1800)     # continental US
]

def doTest(north, west, south, east, year, month, res):
    result = getStats(year, month, res, north, west, south, east)
    print ("Results for Bounding Box (%d, %d) (%d, %d), year = %d, month=%d, res=%d" % (west, north, east, south, year, month, res))
    print ("%d points found in %f milliseconds" % (result['pts'], result['ms']))
    print ("Total bytes %d", result['pts'] * 8)

# fullYears = range(1998, 2015)
# months1997 = range(9, 13)
fullYears = [2006]
resolutions = [1, 2, 4, 10]

# loadDataSet()
loadDataSetMin()
cases = [(year, month) for year in fullYears for month in range(1, 13)]
# cases.extend([(2015, 1)])
# cases.extend([(1997, month) for month in months1997])
fullCases = [(year, month, res) for (year, month) in cases for res in resolutions]
tests = [(north, west, south, east, year, month, res) for (north, west, south, east) in searchRectangles for (year, month, res) in fullCases]
for (north, west, south, east, year, month, res) in tests:
    doTest(north, west, south, east, year, month, res)
