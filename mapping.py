import sys
import math

base64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

def fullSetSize(pointsPerDegree):
    return 360 * 180 * pointsPerDegree * pointsPerDegree

#
# A Coordinate, just a lat/lon pair
#
class Coordinate:
    def __init__(self, lat, lon):
        lat = min(90, max(-90, lat))
        lon = min(180, max(-180, lon))
        self.lat = lat
        self.lon = lon

    def __repr__(self):
        return '(lat: %f, lon: %f)' % (self.lat, self.lon)

#
# The maximum indices for row and column given pointsPerDegree
#
def maximumIndices(pointsPerDegree):
    return {'column': 360 * pointsPerDegree - 1, 'row': 180 * pointsPerDegree - 1}

class DatasetIndex:
    #
    # convert a lat/lon pair to be an (i, j) index into the dataset,
    # given a number of points per degree.  In general, we have
    # {lat: aLat, lon:aLon}, and we want to
    # {rowIndex:aLatIndex, colIndex:aColIndex}, where
    # the northpole, just east of dateline (90-eps, -180+ eps)
    # maps to rowIndex:0, colIndex:0,
    # and where the southpole, just west of dateline (-90 + eps, 180-eps)
    # maps to the maxIndex (pointsPerDegree^2 * 180 * 3600 - 1)
    #
    def __init__(self, aCoordinate, pointsPerDegree):
        aLatAsInteger = int(math.ceil(pointsPerDegree * aCoordinate.lat))
        # now in range (pointsPerDegree * 90, pointsPerDegree * 90 - 1)
        aLatAsInteger = aLatAsInteger - (pointsPerDegree * 90)
        # now 0 at the north pole, -(pointsPerDegree * 90) at the equator,
        # 1-(pointsPerDegree * 180) at the South Pole.  All we need to do
        # is negate
        self.rowIndex = -1 * aLatAsInteger
        # Do it for the longitude.
        aLonAsInteger = int(math.floor(pointsPerDegree * aCoordinate.lon))
        # now -pointsPerDegree * 180 at the dateline, 0 at the prime meridian,
        # 180 - pointsPerDegree just east of the dateline.  all we need to do
        # is shift the range
        self.colIndex = aLonAsInteger + 180 * pointsPerDegree
        maxima = maximumIndices(pointsPerDegree)
        self.colIndex = max(min(self.colIndex, maxima['column']), 0)
        self.rowIndex = max(min(self.rowIndex, maxima['row']), 0)
        self.pointsPerDegree  = pointsPerDegree



    #
    # return the index into the data set, which is just the rowIndex * the number
    # of points in a row + the column index, which is the offset into a row.  Since
    # this can be negative (see the comments in BoundingBox), when row is 0 this
    # can result in a negative index.  The fix is just to return 0 in that case.
    #
    def indexIntoDataSet(self):
        return max(self.rowIndex * self.pointsPerRow() + self.colIndex, 0)

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
    def __init__(self, nw, se, pointsPerDegree):
        self.nwIndex = DatasetIndex(nw, pointsPerDegree)
        self.seIndex = DatasetIndex(se, pointsPerDegree)
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
        rowIndices = range(self.nwIndex.rowIndex, self.seIndex.rowIndex + 1)
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

# Get the data from dataset for the bounding box given by
# (nw, se) where each is given by a pair (lat, long).  In fact
# these are four scalar variables.  Latitude is given in the
# conventional range, (-89.9 to 89.9), where -89.9 is the South Pole and
# 89.9 is the north pole.  Similarly, -179.9 is just east of the dateline,
# 179.9 is just west of the dateline.
#

def getData(nw, se, pointsPerDegree, dataSet):
    bbox = BoundingBox(nw, se, pointsPerDegree)
    indexSet = bbox.getIndexSequences()
    sequences = [dataSet[sn['firstIndex']:sn['lastIndex']] for sn in indexSet]
    return ''.join(sequences)

#
# set up some test data
#
nw = Coordinate(50, 1)
se = Coordinate(49, 2)
bbox = BoundingBox(nw, se, 1)
