

import re
import urllib2
import urllib
import xml.etree.ElementTree as ET
from xml.dom import minidom
import config

def executeSparqlQuery(query, url = config.sparqlURL, giveColumns = False, httpEncode = True):
    query = prefix(query)
    ET.register_namespace("","http://www.w3.org/2005/sparql-results#")

    #queryHtmlFormat = urllib.quote(query)
    requestArgs = { "query":query }
    requestArgs = urllib.urlencode(requestArgs)
    #requestURL = url + "?query="
    #print "requesting: "+requestURL
    #print requestArgs
    resultXML = urllib2.urlopen(url,requestArgs).read()
    root = ET.fromstring(resultXML)

    head = root.find("{http://www.w3.org/2005/sparql-results#}head")
    columns = []

    for result in head:
        columns.append(result.get("name"))

    iteratorResults = root.iter(tag="{http://www.w3.org/2005/sparql-results#}result")

    results = []
    if giveColumns:
        results.append(columns)
    for result in iteratorResults:
        results.append([])
        for item in result:
            for content in item:
                #toAppend = urllib.quote(content.text)
                toAppend = content.text
                if httpEncode: toAppend = toAppend.replace("-","%2D")
                results[len(results)-1].append(toAppend)

    return results

def executeSparqlUpdate(query, url = config.sparqlURL):
    query = prefix(query)
    #queryHtmlFormat = urllib.quote(query)
    requestArgs = { "update":query }
    requestArgs = urllib.urlencode(requestArgs)
    #requestURL = url + "update?update=" + queryHtmlFormat
    requestURL = url + "update"
    requestReturned = urllib2.urlopen(requestURL,requestArgs).read()
    sucessResult = "<boolean>true</boolean>"
    if sucessResult in requestReturned:
        return True
    else:
        print "ERROR: SPARQL UPDATE FAILED! Check your query!"
        return False

def prefix(query,prefix = config.sparqlPrefixes):
	#adds a prefix to a query when they are not yet defined
	startsWithPrefix = re.search("^\s*PREFIX\s",query)
	if startsWithPrefix:
		return query
	else:
		return prefix + " " + query


		
