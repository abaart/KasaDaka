


import urllib2
import urllib
import xml.etree.ElementTree as ET
from xml.dom import minidom
import config

def executeSparqlQuery(query, url = config.sparqlURL, giveColumns = False):
    ET.register_namespace("","http://www.w3.org/2005/sparql-results#")

    queryHtmlFormat = urllib.quote(query)
    requestURL = url + "?query=" + queryHtmlFormat
    #print "requesting: "+requestURL
    resultXML = urllib2.urlopen(requestURL).read()
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
                toAppend = toAppend.replace("-","%2D")
                results[len(results)-1].append(toAppend)

    return results

def executeSparqlUpdate(query, url = config.sparqlURL):

    queryHtmlFormat = urllib.quote(query)
    requestURL = url + "update?update=" + queryHtmlFormat
    requestReturned = urllib2.urlopen(requestURL).read()
    sucessResult = "<boolean>true</boolean>"
    if sucessResult in requestReturned:
        return True
    else:
        print "ERROR: SPARQL UPDATE FAILED! Check your query!"
        return False

		
