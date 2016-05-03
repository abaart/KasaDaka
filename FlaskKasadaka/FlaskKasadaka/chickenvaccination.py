from flask import flash
import config
import sparqlInterface

prefixCode = "cv"
PrefixURI = "http://example.org/chickenvaccinationsapp/"

#key is rdf:type, values is array of properties to use
dataStructure = {
	'user' : ['cv:contact_fname','cv:contact_lname','cv:contact_tel','cv:preferred_language']
}

def objectList(objectType):
	#geeft resultaten van alle objecten van type
	properties = dataStructure[objectType]
	triples = []
	fields = []
	for prop in dataStructure[objectType]:
		triples.append(['?' + objectType , prop , '?' + prop.replace(":","_")])
		fields.append(prop.replace(":","_"))
	return sparqlInterface.selectTriples(fields,triples)




def objectInsert(request,objectType):
    success = insertObjectTriples(objectType,request.form,dataStructure[objectType])
    if success:
        flash(objectType+" successfully inserted! Please record audio for new "+objectType+" on audio page!")
    else:
        flash("Error inserting "+objectType)
    return

#TODO DIT REWRITEN
def objectUpdate(request,objectInfoQuery,updateObjectInfoQuery,objectType):
    #check whether all nessecary fields are sent with the request
    #fetch the columns to check
    objectInfoQuery = objectInfoQuery.replace("<INSERTURI>","<"+request.form[objectType]+">")
    objectInfo = sparqlInterface.executeSparqlQuery(objectInfoQuery,giveColumns=True)
    
    #TODO update to not use replace function

    updateObjectInfoQuery = sparqlInterface.updateQueryReplace(request.form[objectType],updateObjectInfoQuery,objectInfo[0],request.form)
    success = sparqlInterface.executeSparqlUpdate(updateObjectInfoQuery)
    if success:
        flash(objectType+' data successfully updated!')
    else:
        flash('Error in updating '+objectType)
    return


def insertObjectTriples(objectType,fields,fieldIDs):
    URI =  PrefixURI + objectType
    URI = sparqlInterface.findFreshURI(URI)
    triples = [[URI,'rdf:type', prefixCode + ':' + objectType]]
    for field in fieldIDs:
        triples.append([URI,field,fields[field]])
    return sparqlInterface.insertTriples(triples) 