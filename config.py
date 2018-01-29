#!/usr/bin/python
# configuration data for the new server and searchBase64DB

#
# the directory where the data lives.  This should be in a configuration file
#
dataDirectory = './pyData'
#
# server port
#
port = 8888
#
# Whether to use ssl (https)
# has two fields: a boolean, use_ssl, and if use_ssl is true a pair
# (certfile, keyfile)
#
ssl_directive = {
	'use_ssl': False,
	'ssl_context': ('myFile.crt', 'myFile.key')
}