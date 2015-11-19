import sys
import math

base64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

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
    def __init__(self, nw, se, offsetComputers):
        self.nwIndex = DatasetIndex(nw, offsetComputers)
        self.seIndex = DatasetIndex(se, offsetComputers)
        if (self.seIndex.colIndex < self.nwIndex.colIndex):
            # then we cross the dateline.  There is no problem
            # having a negative column index -- we just use columnIndex
            # as an offset anyway (the data is indexed in row-major order)
            self.nwIndex.complementColIndex()

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
        indexesPerRow = 1 + self.seIndex.colIndex - self.nwIndex.colIndex
        #
        # Handle the special case of a single rectangle (the bounding box spans
        # longitude -180 to 180)
        #
        if (indexesPerRow >=  self.nwIndex.pointsPerRow()):
            firstIndex = self.nwIndex.indexIntoDataSet()
            lastIndex = self.seIndex.indexIntoDataSet()
            return [{'firstIndex':firstIndex, 'lastIndex':lastIndex}]
        #
        # Get the first index of every row in the range.  This is just the row number * pointsPerRow
        # plus the offset from the first point in the row, which is the colIndex
        #
        rowIndices = range(self.seIndex.rowIndex, self.nwIndex.rowIndex + 1)
        firstIndices = [row * self.nwIndex.pointsPerRow() + self.nwIndex.colIndex for row in rowIndices]
        #
        # Unlikely to happen corner case.  If the bounding box includes row 0 (the North Pole) and
        # crosses the dateline, then the nw rowIndex = 0, nw colIndex < 0, and so its dataset index
        # will be < 0.  The fix here is simply to set it to be 0; for all the remaining rows, the
        # rowIndex * pointsPerRow > |the maximum negative column index|, so the data index is positive
        #
        if firstIndices[0] < 0:
            firstIndices[0] = 0
        return [{'firstIndex': firstIndex, 'lastIndex': firstIndex + indexesPerRow} for firstIndex in firstIndices]
    #
    # for debugging
    #
    def __repr__(self):
        return '(nw: %s, se:%s)' % (self.nwIndex.__repr__(), self.seIndex.__repr__())

#
# Get the data from dataset for the bounding box given by
# (nw, se) where each is given by a pair (lat, long).  In fact
# these are four scalar variables.  Latitude is given in the
# conventional range, (-89.9 to 89.9), where -89.9 is the South Pole and
# 89.9 is the north pole.  Similarly, -179.9 is just east of the dateline,
# 179.9 is just west of the dateline.  This routine returns a list of
# strings, one per row.  The subsequent method returns as a single string
#

def getDataAsSequences(nw, se, offsetComputer, dataSet):
    bbox = BoundingBox(nw, se, offsetComputer)
    indexSet = bbox.getIndexSequences()
    sequences = [dataSet[sn['firstIndex']:sn['lastIndex']] for sn in indexSet]
    return sequences
#
# Get the data from dataset for the bounding box given by
# (nw, se) where each is given by a pair (lat, long).  This returns the result
# from getData as a single string, which is what will generally be used; a routine
# which calls getDataAsSequences directly does it to support human-readability for debugging.
#

def getData(nw, se, offsetComputer, dataSet):
    sequences = getDataAsSequences(nw, se, offsetComputer, dataSet)
    return ''.join(sequences)
