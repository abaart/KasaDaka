import re
import urllib2
import urllib
import xml.etree.ElementTree as ET
from xml.dom import minidom
import config

def executeSparqlQuery(query, url = config.sparqlURL, giveColumns = False, httpEncode = True):
    query = addGraph(query)
    query = addPrefix(query)
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
    query = addGraph(query)
    query = addPrefix(query)
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

def addPrefix(query,prefix = config.sparqlPrefixes):
	#adds a prefix to a query when they are not yet defined
	startsWithPrefix = re.search("^\s*PREFIX\s",query)
	if startsWithPrefix:
		return query
	else:
		return prefix + " " + query

def addGraph(query,graph = config.sparqlGraph):
    #adds the graph from the config to the query, when not defined 

    #regex that searches for DATA or WHERE without GRAPH defined, adds it in.
    result = re.sub(r"(\s(DATA|WHERE)\s*\{\s*(?!\s*GRAPH\s*\<[^\>]*\>\s*))([^\;]*)(\;?)",
    r"\1GRAPH <"+ graph + r"> {\3}\4",
    query)
    return result

def updateQueryReplace(URI,updateQuery,replacables,insertables):
    """
    Replaces pieces in an update query.
    Input: 
        URI = The URI to be inserted over "<INSERTURI>"
        updateQuery = the query to replace things in
        replacables = matrix of 2 arrays, first array contains the labels (columns) to be replaced in the query. This array is best generated from a SPARQL query (with headers turned on).
        insertables = request dictionary a.k.a. 'request.form', with the 'keys' the same as the labels in replacables, the values will be inserted in to the query
    Output:
        Query with all stuff replaced

    Example query to be processed:
    DELETE DATA{ 
    <INSERTURI> cv:contact_fname ?fname.
    <INSERTURI> cv:contact_lname ?lname.
    <INSERTURI> cv:contact_tel ?tel.
    <INSERTURI> cv:preferred_language ?pl.
    };
    INSERT DATA {
    <INSERTURI> cv:contact_fname <fname>.
    <INSERTURI> cv:contact_lname <lname>.
    <INSERTURI> cv:contact_tel <tel>.
    <INSERTURI> cv:preferred_language <pl>.
    };
    """
    updateQuery = updateQuery.replace("<INSERTURI>","<"+URI+">")
    for replacable in replacables:
        #insert URI's and strings in their own way
        if validURI(insertables[replacable]):
            updateQuery = updateQuery.replace("<"+replacable+">","<"+insertables[replacable]+">")
        else:
            updateQuery = updateQuery.replace("<"+replacable+">","'"+insertables[replacable]+"'")
    return updateQuery

def selectTriples(fields,triples,filter = "",distinct = True):
    """
    Inserts given matrix of triples into triple store.
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
    print query
    return executeSparqlQuery(query)


def deleteTriples(tuples):
    """
    Deletes triples that match the two first elements given in the tuples.
    """
    queryBuilder1 = """DELETE DATA {"""
    queryBuilder2 = """ """
    queryBuilder3 = """};"""
    if len(triples) == 0: raise ValueError('No tuples to delete!')
    for index, triple in enumerate(triples):
        refinedTriple = preProcessTriple(triple)
        queryBuilder2 = queryBuilder2 + " " + refinedTriple[0] + " " + refinedTriple[1] + " ?" + index + " . "
    return executeSparqlUpdate(queryBuilder1+queryBuilder2+queryBuilder3)

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
    result = ""
    if validURI(element):
       result = ("<"+element+">")
    #check whether element could be a prefix thingy
    elif re.search("^\w{2,}:\w{2,100}$",element):
        result = element
    else:
        result = '"'+ element +'"'
    return result



def findFreshURI(preferredURI):
    """
    Returns a URI that does not exist, taking in to account the preferred URI.
    """
    addition = 1
    URI = preferredURI + "_" + str(addition)
    while existsURI(URI):
        addition = addition + 1
        URI = preferredURI + "_" + str(addition)
    return URI

		
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