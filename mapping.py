import sys
import math

base64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

#
# A Hybrid encoder.  This encodes according to the formula
# y = (maxY/maxX) * x for 0 <= x <= maxX
# y = maxY + ceil(log2(x)) - ceil(log2(maxX)) for
# x > maxX
#
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

    def getXRange(self, aYVal):
        if (aYVal < 0):
            return {'min': 0, 'max':0}
        #
        # If it's in the linear range, we have
        # y = slope * x, so
        # x = y/slope.  Since we're rounding,
        # the minimum x is (y - 0.5)/slope, the
        # maximum is (y + 0.5)/slope
        if (aYVal < self.maxY):
            return {'min': (aYVal - 0.5)/self.slope, 'max': (aYVal + 0.5)/self.slope}
        #
        # If we're in the exponential range, then
        # y = maxY + ceil(log2(x)) - ceil(log2(maxX)) for
        # so ceil(log2(maxX)) + y - maxY = ceil(log2(x))
        # so x < 1 << ceil(log2(maxX)) + y - maxY and
        # the min is half that...note ceil(log2(maxX)) is self.bitOffset
        #
        ceilX = 1 << (self.bitOffset + aYVal - self.maxY)
        minX = ceilX >> 1
        if (aYVal == self.maxY or minX < self.maxX):
            minX = self.maxX - 0.5
        if (aYVal == 63):
            ceilX = 1 << 30 # infinity...
        return {'min': minX, 'max': ceilX}



def fullSetSize(pointsPerDegree):
    return 360 * 180 * pointsPerDegree * pointsPerDegree

#
# Initialize the parameters
#
class OffsetComputer:
    def __init__(self, pointsPerDegree, offsetData):
        self.offsets = offsetData
        self.pointsPerDegree = pointsPerDegree

    #
    # get the index of the offset corresponding to aDegreeOffset (a tenth
    # of a degree).  This is the amount to add to the index we get from a
    # degree
    #

    def getIndexOffset(self, aDegreeOffset):
        if aDegreeOffset in self.offsets:
            return self.offsets.index(aDegreeOffset)
        for index, elem in enumerate(self.offsets):
            if (elem > aDegreeOffset): return index - 1
        return self.pointsPerDegree - 1

    #
    # given a row or column index, return the latitude/longitude
    # in tenths of degrees
    #
    def computeLatOrLonFromIndex(self, aRowOrColIndex, minValue):
        numDegrees = int(math.floor(aRowOrColIndex/self.pointsPerDegree))
        offsetIndex = aRowOrColIndex % self.pointsPerDegree
        return minValue + 10 * numDegrees + self.offsets[offsetIndex]

    #
    # Return the lat/lon for a given index into the dataset.  This is the
    # inverse of the computation that DatasetIndex does.  As always, we will
    # return in tenths of degrees
    #

    def getCoordinateForIndex(self, anIndexIntoDataSet):
        # There are 360 * pointsPerDegree points in a row
        # so taking the floor of anIndexIntoDataset/(360 * pointsPerDegree)
        # gives us the row
        rowIndex = int(math.floor(anIndexIntoDataSet/(360 * self.pointsPerDegree)))
        # The column index is just what's left over
        colIndex = anIndexIntoDataSet - 360 * self.pointsPerDegree * rowIndex
        latitude = self.computeLatOrLonFromIndex(rowIndex, -900)
        longitude = self.computeLatOrLonFromIndex(colIndex, -1800)
        return {'lat': latitude, 'lon': longitude}

#
# A Coordinate, just a lat/lon pair.  Here and everywhere these are integers
# in tenths of degrees
#
class Coordinate:
    def __init__(self, lon, lat):
        lat = min(900, max(-900, lat))
        lon = min(1800, max(-1800, lon))
        latFromSouthPole = lat + 900
        lonFromDateline = lon + 1800
        self.latDegree = int(math.floor(latFromSouthPole/10))
        self.lonDegree = int(math.floor(lonFromDateline/10))
        self.lonOffset = lon % 10
        self.latOffset = lat % 10
        self.lat = lat
        self.lon = lon

    def __repr__(self):
        vals = (self.lat, self.latDegree, self.latOffset, self.lon, self.lonDegree, self.lonOffset)
        return 'lat: %d (%d from south pole, offset %d), lon: %d (%d from date line, offset %d)' % vals

#
# The maximum indices for row and column given pointsPerDegree
#
def maximumIndices(pointsPerDegree):
    return {'column': 360 * pointsPerDegree - 1, 'row': 180 * pointsPerDegree - 1}

class DatasetIndex:
    #
    # convert a lat/lon pair to be an (i, j) index into the dataset,
    # given a number of points per degree. The dataset
    #
    def __init__(self, aCoordinate, offsetComputer):
        self.rowIndex =  aCoordinate.latDegree * offsetComputer.pointsPerDegree
        self.rowIndex += offsetComputer.getIndexOffset(aCoordinate.latOffset)
        self.colIndex = aCoordinate.lonDegree * offsetComputer.pointsPerDegree
        self.colIndex += offsetComputer.getIndexOffset(aCoordinate.lonOffset)
        self.pointsPerDegree  = offsetComputer.pointsPerDegree



    #
    # return the index into the data set, which is just the rowIndex * the number
    # of points in a row + the column index, which is the offset into a row.  Since
    # this can be negative (see the comments in BoundingBox), when row is 0 this
    # can result in a negative index.  The fix is just to return 0 in that case.
    #
    def indexIntoDataSet(self):
        return int(max(self.rowIndex * self.pointsPerRow() + self.colIndex, 0))

    #
    # complement the column index for when we want an index west of the dateline
    # to be a negative number.  Since the data set is in row-major order, this
    # is not a problem, unless rowIndex = 0.  Should check for that.
    # The dateline is at self.pointsPerDegree * 360, so if we are one tick
    # west of the dateline (our colIndex is then self.pointsPerDegree * 360 - 1)
    # we want it to become -1.  Conversely, if we are one tick east of the dateline,
    # our current colIndex is 1, and we want it to become -(self.pointsPerDegree * 360 - 1),
    # or 1 - self.pointsPerDegree * 360.  A little algebra in both cases shows that
    # we want to set colIndex = colIndex - self.pointsPerDegree * 360
    #

    def complementColIndex(self):
        self.colIndex = self.colIndex - self.pointsPerDegree * 360

    #
    # points in a row (one way all around the earth)
    #
    def pointsPerRow(self):
        return 360 * self.pointsPerDegree

    #
    # for debugging
    #
    def __repr__(self):
        return '(row: %d, col:%d, pointsPerDegree: %d)' % (self.rowIndex, self.colIndex, self.pointsPerDegree)

#
# Create the bounding box in a pair (nwDataSetIndex, seDataSetIndex
# where the indexes are DatasetIndex for the coordinates
# (nw, se) where each is given by a pair (lat, long).  This involves
# computing the indices for the lat, long pair, and adjusting the
# column index for the nw column index in the case where the BoundingBox
# crosses the dateline
#

class BoundingBox:
    def __init__(self, northLat, southLat, westLon, eastLon, offsetComputers):
        self.sw = Coordinate(westLon, southLat)
        self.ne = Coordinate(eastLon, northLat)
        self.swIndex = DatasetIndex(self.sw, offsetComputers)
        self.neIndex = DatasetIndex(self.ne, offsetComputers)
        if (self.neIndex.colIndex < self.swIndex.colIndex):
            # then we cross the dateline.  There is no problem
            # having a negative column index -- we just use columnIndex
            # as an offset anyway (the data is indexed in row-major order)
            self.swIndex.complementColIndex()

    #
    # Number of indexes in a row
    #
    def indexesPerRow(self):
        return 1 + self.neIndex.colIndex - self.swIndex.colIndex

    #
    # Find the actual sequences of indices in the data set. In
    # general, this will be a list of the form [{'firstIndex':n, 'lastIndex':m}]
    # where n < m and both are on the same row.  the second form is where the
    # entire globe (E-W) is spanned, in which case the list has a single entry
    # We are throwing lots of data structures at this problem, primarily for
    # testing and debugging
    #
    def getIndexSequences(self):
        # Find out how many indexes per row we want from the bounding box
        # east - west
        indexesPerRow = 1 + self.neIndex.colIndex - self.swIndex.colIndex
        #
        # Handle the special case of a single rectangle (the bounding box spans
        # longitude -180 to 180)
        #
        if (indexesPerRow >=  self.swIndex.pointsPerRow()):
            firstIndex = self.swIndex.indexIntoDataSet()
            lastIndex = self.neIndex.indexIntoDataSet()
            return [{'firstIndex':firstIndex, 'lastIndex':lastIndex}]
        #
        # Get the first index of every row in the range.  This is just the row number * pointsPerRow
        # plus the offset from the first point in the row, which is the colIndex
        #
        rowIndices = range(self.swIndex.rowIndex, self.neIndex.rowIndex + 1)
        firstIndices = [row * self.swIndex.pointsPerRow() + self.swIndex.colIndex for row in rowIndices]
        #
        # Unlikely to happen corner case.  If the bounding box includes row 0 (the South Pole) and
        # crosses the dateline, then the sw rowIndex = 0, sw colIndex < 0, and so its dataset index
        # will be < 0.  The fix here is simply to set the first row to be the first row above the
        # south pole (which is empty in any case).  This just means dropping the first element
        #
        if firstIndices[0] < 0:
            firstIndices = firstIndices[1:]
        return [{'firstIndex': firstIndex, 'lastIndex': firstIndex + indexesPerRow} for firstIndex in firstIndices]
    #
    # for debugging
    #
    def __repr__(self):
        return '(sw: %s, ne:%s)' % (self.swIndex.__repr__(), self.neIndex.__repr__())

#
# Get the data from dataset for the bounding box given by
# (nw, se) where each is given by a pair (lat, long).  In fact
# these are four scalar variables.  Latitude is given in the
# conventional range, (-89.9 to 89.9), where -89.9 is the South Pole and
# 89.9 is the north pole.  Similarly, -179.9 is just east of the dateline,
# 179.9 is just west of the dateline.  This routine returns a list of
# strings, one per row.  The subsequent method returns as a single string
#

def getDataAsSequences(north, south, west, east, offsetComputer, dataSet):
    bbox = BoundingBox(north, south, west, east, offsetComputer)
    indexSet = bbox.getIndexSequences()
    sequences = [dataSet[sn['firstIndex']:sn['lastIndex']] for sn in indexSet]
    firstCoordinate = offsetComputer.getCoordinateForIndex(indexSet[0]['firstIndex'])
    pointsPerRow = bbox.indexesPerRow()
    return {'swCorner': firstCoordinate, 'pointsPerRow': pointsPerRow, 'pointsPerDegree': offsetComputer.pointsPerDegree, 'sequences': sequences}
#
# Get the data from dataset for the bounding box given by
# (nw, se) where each is given by a pair (lat, long).  This returns the result
# from getData as a single string, which is what will generally be used; a routine
# which calls getDataAsSequences directly does it to support human-readability for debugging.
#

def getData(north, south, west, east, offsetComputer, dataSet):
    result = getDataAsSequences(north, south, west, east, offsetComputer, dataSet)
    result['base64String'] = ''.join(result['sequences'])
    return result
