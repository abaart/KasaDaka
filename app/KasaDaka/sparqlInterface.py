import re
import urllib2
import urllib
import xml.etree.ElementTree as ET
from xml.dom import minidom
import config

def executeSparqlQuery(query, url = config.sparqlURL, giveColumns = False, httpEncode = True,addGraph=True):
    if addGraph: query = addGraphToQuery(query)
    query = addPrefix(query)
    ET.register_namespace("","http://www.w3.org/2005/sparql-results#")
    requestArgs = { "query":query.encode('utf-8') }
    requestArgs = urllib.urlencode(requestArgs)
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
                toAppend = content.text
                if httpEncode: toAppend = toAppend.replace("-","%2D")
                results[len(results)-1].append(toAppend)
    return results

def executeSparqlUpdate(query, url = config.sparqlURL,addGraph=True):
    if addGraph: query = addGraphToQuery(query)
    query = addPrefix(query)
    requestArgs = { "update":query.encode('utf-8') }
    requestArgs = urllib.urlencode(requestArgs)
    requestURL = url + "update"
    requestReturned = urllib2.urlopen(requestURL,requestArgs).read()
    sucessResult = "<boolean>true</boolean>"
    if sucessResult in requestReturned:
        return True
    else:
        print "ERROR: SPARQL UPDATE FAILED! Check your query!"
        return Falseproperties

def addPrefix(query,prefix = config.sparqlPrefixes):
	#adds a prefix to a query when they are not yet defined
	startsWithPrefix = re.search("^\s*PREFIX\s",query)
	if startsWithPrefix:
		return query
	else:
		return prefix + " " + query

def addGraphToQuery(query,graph = config.sparqlGraph):
    #adds the graph from the config to the query, when not defined 

    #regex that searches for DATA or WHERE without GRAPH defined, adds it in.
    result = re.sub(r"(\s(DATA|WHERE)\s*\{\s*(?!\s*GRAPH\s*\<[^\>]*\>\s*))([^\;]*)(\;?)",
    r"\1GRAPH <"+ graph + r"> {\3}\4",
    query)
    return result

def selectTriples(fields,triples,filter = "",distinct = True,giveColumns = False,httpEncode = False):
    """
    Inserts given matrix of triples into triple store.
    fields = fields to define in the SELECT part of the query, as columns in the result
    triples = triples to define in the WHERE part of the query
    filter = (optional) filter on a URI/value: array with (0):the name of the variable (out of fields) to use for the filter. (1): URI/value to use
    distinct = (optional) enable/disable distinct (non duplicate) results
    """
    if distinct: 
        queryBuilder1 = """ SELECT DISTINCT """
    else:
        queryBuilder1 = """ SELECT """
    queryBuilder2 = """ """
    queryBuilder3 = """  WHERE {"""
    queryBuilder4 = """ """
    queryBuilder5 = """ """
    queryBuilder6 = """}"""
    #if len(triples) == 0: return [[]]
    if len(triples) == 0: raise ValueError('No triples for selection!')
    if len(fields) == 0: raise ValueError("No fields for selection!")
    for field in fields:
        queryBuilder2 = queryBuilder2 + " ?" + field + " " 
    for triple in triples:
        refinedTriple = preProcessTriple(triple)
        queryBuilder4 = queryBuilder4 + " " + refinedTriple[0] + " " + refinedTriple[1] + " " + refinedTriple[2] + " . "
    if len(filter) != 0:
        queryBuilder5 = " FILTER(?" + filter[0] + "=" + preProcessElement(filter[1]) + " ) "
    query = queryBuilder1 + queryBuilder2 + queryBuilder3 + queryBuilder4 + queryBuilder5 + queryBuilder6
    return executeSparqlQuery(query,giveColumns=giveColumns,httpEncode=httpEncode)

def deleteObject(URI):
    """Deletes all triples where the provided URI is the subject."""
    query = """WITH <""" + config.sparqlGraph + """> DELETE { ?del ?p ?v} WHERE {?del ?p ?v FILTER( ?del = <""" + URI + """> )} ;"""
    print query
    return executeSparqlUpdate(query,addGraph=False)

def deleteTriples(triples):
    """
    Deletes triples, or triples that match the two first elements given in the tuples.
    """

    ###### PROBABLY BROKEN, incorrect use of SPARQL~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    queryBuilder1 = """DELETE DATA {"""
    queryBuilder2 = """ """
    queryBuilder3 = """};"""
    if len(triples) == 0: raise ValueError('No triples to delete!')
    for index, triple in enumerate(triples):
        refinedTriple = preProcessTriple(triple)
        if len(refinedTriple) == 3 and len(refinedTriple[2]) != 0:
            queryBuilder2 = queryBuilder2 + " " + refinedTriple[0] + " " + refinedTriple[1] + " " + refinedTriple[2] + " . "
        elif len(refinedTriple) == 2:
            queryBuilder2 = queryBuilder2 + " " + refinedTriple[0] + " " + refinedTriple[1] + " ?" + str(index) + " . "
        else: raise ValueError('Triple to delete is no triple or tuple!')
    return executeSparqlUpdate(queryBuilder1+queryBuilder2+queryBuilder3)

def updateTriples(triplesToBeDeleted,triplesToBeInserted):
    """Updates the content of the provided triples.
    Input: triples of: [subject, property, NEW-VALUE]
    The old value does not matter, it will be overwritten by the new value.
    """
    queryBuilder1 = """WITH <""" + config.sparqlGraph +"""> DELETE {"""
    queryBuilder2 = """ """
    queryBuilder3 = """} INSERT {"""
    queryBuilder4 = """ """
    queryBuilder5 = """ } WHERE { """
    queryBuilder6 = """ """
    queryBuilder7 = """ } """

    for deleteTriple in triplesToBeDeleted:
        refinedTriple = preProcessTriple(deleteTriple)
        queryBuilder2 = queryBuilder2 + " " + refinedTriple[0] + " " + refinedTriple[1] + " " + refinedTriple[2] + " . "
    for insertTriple in triplesToBeInserted:
        refinedTriple = preProcessTriple(insertTriple)
        queryBuilder4 = queryBuilder4 + " " + refinedTriple[0] + " " + refinedTriple[1] + " " + refinedTriple[2] + " . "
    query = queryBuilder1 + queryBuilder2 + queryBuilder3 + queryBuilder4 + queryBuilder5 + queryBuilder6 + queryBuilder7
    return executeSparqlUpdate(query,addGraph=False)

def insertTriples(triples):
    """
    Inserts given matrix of triples into triple store.
    """
    queryBuilder1 = """INSERT DATA {"""
    queryBuilder2 = """ """
    queryBuilder3 = """};"""
    if len(triples) == 0: raise ValueError('No triples to insert!')
    for triple in triples:
        refinedTriple = preProcessTriple(triple)
        queryBuilder2 = queryBuilder2 + " " + refinedTriple[0] + " " + refinedTriple[1] + " " + refinedTriple[2] + " . "
    return executeSparqlUpdate(queryBuilder1+queryBuilder2+queryBuilder3)


def preProcessTriple(triple):
    """
    Preprocesses a triple for use in a SPARQL query.
    DOES NOT check for valid use of prefixes.
    """
    result=[]
    for element in triple:
        result.append(preProcessElement(element))
    return result

def preProcessElement(element):
    """
    Adds < > when element is a URI.
    Adds " " when element is likely a string.
    Does not add anything when element is likely a short URI. (uses prefix)
    """
    if len(element) == 0: raise ValueError("Error: empty element!")
    result = ""
    if validURI(element):
       result = ("<"+element+">")
    #check whether element could be a prefix thingy or variable
    elif re.search("^\w{2,}:\w{2,100}$",element) or re.search("^\?\w+$",element):
        result = element
    else:
        result = '"'+ element +'"'
    return result

def existsURI(URI):
    """
    Checks whether a URI exists.
    """
    if not validURI: raise ValueError('URI to check for existance not valid!')
    existenceQuery = """
    SELECT * WHERE {
    ?sub ?pred ?obj .
    FILTER(?sub = <"""+ URI + """>)} """
    result = executeSparqlQuery(existenceQuery)
    if len(result) == 0: return False
    else: return True

def validURI(URI):
    """
    Checks whether a given URI is valid.
    """
    return re.search("(https?:\/\/(?:www\.|(?!www))[^\s\.]+\.[^\s]{2,}|www\.[^\s]+\.[^\s]{2,})",URI)
