from config import dataDirectory
import json
from mapping import fullSetSize
#
# The data manager for the visualizer.  This loads data sets on demand and unloads them
# to keep memory usage in checkFunction
#
class DataManager:
    def __init__(self):
        self.data = {}
        manifestFile = open(dataDirectory + '/manifest.json')
        self.rawManifest = json.loads(manifestFile.read())
        self.manifest = {}
        for record in self.rawManifest:
            self.manifest[(record['year'], record['month'], record['res'])] = dataDirectory + '/' + record['file']
            if record['res'] != 10:
                self.loadDataSet(record['year'], record['month'], record['res'])

    def hasDataSet(self, year, month, res):
        return year in self.data and month in self.data[year] and res in self.data[year][month]

    def bestResolution(self, year, month):
        if (not year in self.data) or (not month in self.data[year]):
            return None
        resolutions = self.data[years][months].keys()
        return resolutions.sort()[-1]

    def checkLoadable(self, year, month, res):
        return (year, month, res) in self.manifest


    #
    # Utilities to query the data
    #
    def getMonths(self, year):
        return [month for (aYear, month, res) in self.manifest.keys() if aYear == year]


    def getResolutions(self, year, month):
        return [res for (aYear, aMonth, res) in self.manifest.keys() if aYear == year and aMonth == month]


    #
    # Sanity check on data: is everything the right length?
    #
    def sanityCheck(self, year, month, res):
        if self.checkLoadable(year, month, res):
            if (self.hasDataSet(year, month, res)):
                return fullSetSize(res) == len(self.data[year][month][res])
            else: return True
        else: return False

    #
    # Sanity check and report
    #
    def sanityCheckAndReport(self, year, month, res):
        setReportStr = "year = %d, month = %d, res = %d" % (year, month, res)
        sanityCheckReportString = 'Data set sanity check failed for %s, expected %d entries got %d'
        if (not self.checkLoadable(year, month, res)):
            print 'Data set %s does not exist' % setReportStr
            return
        if (not self.hasDataSet(year, month, res)):
            print 'Have not yet loaded data for %s' %setReportStr
        if (not self.sanityCheck(year, month, res)):
            print sanityCheckReportString % (setReportStr, fullSetSize(res), len(self.data[year][month][res]))
    #
    # Get the loaded (year, month, res) tuples
    #
    def getAllLoadedKeys(self):
        return [(year, month, res) for year in self.data for month in self.data[year] for res in self.data[year][month]]

    #
    # Get the loadable (year, month, res) tuples
    #
    def getLoadableKeys(self):
        return self.manifest.keys()

    #
    # Do A sanity check over the whole data set
    #
    def fullSanityCheck(self):
        keys = self.getAllLoadedKeys()
        for (year, month, res) in keys: self.sanityCheckAndReport(year, month, res)

    #
    # print a year, month, res
    #
    def printReport(self, year, month, res):
        print "year = %d, month = %d, res = %d" % (year, month, res)

    #
    # checkExistenceSanityCheckReport: designed to be called
    # from checkExistenceSanityCheck -- just makes sure that
    # checkDatasetExists returns True for all loaded data sets
    #
    def checkExistenceSanityCheckReport(self, year, month, res):
        if not self.checkLoadable(year, month, res):
            print 'Error: checkDatasetExists failed for year = %d, month = %d, res = %d' % (year, month, res)
    #
    # Ensure checkDatasetExists returns True for all loaded data sets
    #
    def checkExistenceSanityCheck(self):
        keys = self.getAllLoadedKeys()
        for (year, month, res) in keys: self.checkExistenceSanityCheckReport(year, month, res)

    #
    # print an inventory of what we have
    #
    def printInventory(self):
        print 'Printing Inventory of loaded data.  '
        keys = self.getAllLoadedKeys()
        for (year, month, res) in keys:
            print "year = %d, month = %d, res = %d" % (year, month, res)
        print 'Loadable Datasets are:'
        for (year, month, res) in self.manifest.keys():
            print "year = %d, month = %d, res = %d" % (year, month, res)



    def loadDataSet(self, year, month, res):
        if not (year, month, res) in self.manifest: return
        f = open(self.manifest[(year, month, res)])
        dataset = f.read()
        f.close()
        if not year in self.data: self.data[year] = {}
        if not month in self.data[year]: self.data[year][month] = {}
        self.data[year][month][res] = dataset

    def getData(self, year, month, res):
        if self.hasDataSet(year, month, res): return self.data[year][month][res]
        if (year, month, res) in self.manifest:
            self.loadDataSet(year, month, res)
            return self.data[year][month][res]

    def getSize(self):
        return sum([len(self.data[year][month][res]) for year in self.data for month in self.data[year] for res in self.data[year][month]])
