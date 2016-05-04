from flask import flash
from config import dataStructure
import sparqlInterface
from base64 import b16encode , b16decode

def getDataStructure(URI):
	return dataStructure[URI]

def retrieveLabel(URI):
	triples = []
	fields = []
	triples.append([URI , "rdfs:label" , '?' + b16encode(URI)])
	fields.append(b16encode(URI))
	return sparqlInterface.selectTriples(fields,triples,giveColumns=False)[0][0]

def propertyLabels(objectType,firstColumnIsURI=False):
	properties = dataStructure[objectType]
	triples = []
	fields = []
	for prop in properties:
		triples.append([prop , "rdfs:label" , '?' + b16encode(prop)])
		fields.append(b16encode(prop))
	result = []
	if firstColumnIsURI: result.append('URI')
	result.extend(sparqlInterface.selectTriples(fields,triples,giveColumns=False)[0])
	return result

def objectInfo(URI):
	objectType = determineObjectType(URI)
	properties = dataStructure[objectType]
	triples = []
	fields = []
	for prop in dataStructure[objectType]:
		triples.append(["?uri" , prop , '?' + b16encode(prop)])
		fields.append(b16encode(prop))
	filter = ["uri",URI]
	return sparqlInterface.selectTriples(fields,triples,filter,giveColumns=True)

def objectList(objectType):
	#gives a list of all objects of a certain type
	properties = dataStructure[objectType]
	triples = []
	fields = []
	triples.append(['?' + b16encode(objectType) , 'rdf:type' , objectType])
	fields.append(b16encode(objectType))
	for prop in dataStructure[objectType]:
		triples.append(['?' + b16encode(objectType) , prop , '?' + b16encode(prop)])
		fields.append(b16encode(prop))
	return sparqlInterface.selectTriples(fields,triples)

#TODO DIT REWRITEN
def objectUpdatepodl(request,objectInfoQuery,updateObjectInfoQuery,objectType):
    #check whether all nessecary fields are sent with the request
    #fetch the columns to check
    objectInfoQuery = objectInfoQuery.replace("<INSERTURI>","<"+request.form[objectType]+">")
    objectInfo = sparqlInterface.executeSparqlQuery(objectInfoQuery,giveColumns=True)
    
    #TODO update to not use replace function

    updateObjectInfoQuery = sparqlInterface.updateQueryReplace(request.form[objectType],updateObjectInfoQuery,objectInfo[0],request.form)
    success = sparqlInterface.executeSparqlUpdate(updateObjectInfoQuery)
    if success:
    	#FLASH UIT DEZE CLASS
        flash(objectType+' data successfully updated!')
    else:
        flash('Error in updating '+objectType)
    return success

def objectUpdate(URI,deleteProperties,insertTuples):
	if len(deleteProperties) == 0 or len(insertTuples) == 0: raise ValueError("Nothing to delete/update!")
	if len(deleteProperties) != len(insertTuples): raise ValueError('Number of fields in deleting not equal to inserting!')
	if len(URI) == 0: raise ValueError("URI not defined!")
	triplesToBeDeleted = []
	triplesToBeInserted = []
	for field in deleteProperties:
		triplesToBeDeleted.append([URI,field])
	for insertTuple in insertTuples:
		if insertTuple[0] not in deleteProperties: raise ValueError("Properties to be deleted not equal to properties to be inserted!")
		triplesToBeInserted.append([URI,insertTuple[0],insertTuple[1]])
	success = sparqlInterface.deleteTriples(triplesToBeDeleted) and sparqlInterface.insertTriples(triplesToBeInserted)
	return success


def insertObjectTriples(URI,objectType,tuples):
    URI = findFreshURI(URI)
    triples = [[URI,'rdf:type',objectType]]
    for tupl in tuples:
        triples.append([URI,tupl[0],tupl[1]])
    return sparqlInterface.insertTriples(triples) 

def determineObjectType(URI):
	triples = [[URI,'rdf:type','?type']]
	fields = ['type']
	return sparqlInterface.selectTriples(fields,triples)[0][0]

def createURIarray(queryResult):
    """
    creates an array of tuples with:
    pos 0: the base16 encoded URI
    pos 1: the URI (original)
    Input:
    result from SPARQL query with in the first (0) column the URI of the result
    """
    output = []
    for result in queryResult:
        output.append([b16encode(result[0]),result[0]])
    return output

def findFreshURI(preferredURI):
    """
    Returns a URI that does not exist, taking in to account the preferred URI.
    """
    addition = 1
    URI = preferredURI + "_" + str(addition)
    while sparqlInterface.existsURI(URI):
        addition = addition + 1
        URI = preferredURI + "_" + str(addition)
    return URI
