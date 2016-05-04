
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

#URI of graph to use
sparqlGraph = "http://localhost/chickenvaccination"

#key is rdf:type, values is array of properties to use
dataStructure = {
    'http://example.org/chickenvaccinationsapp/user' : ['http://example.org/chickenvaccinationsapp/contact_fname','http://example.org/chickenvaccinationsapp/contact_lname','http://example.org/chickenvaccinationsapp/contact_tel','http://example.org/chickenvaccinationsapp/preferred_language'],
    'http://example.org/chickenvaccinationsapp/chicken_batch' : ['http://example.org/chickenvaccinationsapp/birth_date','http://example.org/chickenvaccinationsapp/owned_by'],
    'http://example.org/chickenvaccinationsapp/disease' : ['http://example.org/chickenvaccinationsapp/occurs_in'],
    'http://example.org/chickenvaccinationsapp/vaccination' : ['http://example.org/chickenvaccinationsapp/days_after_birth','http://example.org/chickenvaccinationsapp/description','http://example.org/chickenvaccinationsapp/treats']
}

#TODO implement automatic insertion of prefixes
sparqlPrefixes = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
PREFIX lexvo: <http://lexvo.org/ontology#>
PREFIX cv: <http://example.org/chickenvaccinationsapp/>
"""
sparqlPrefixDict = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#' : 'rdf',
    'http://www.w3.org/2000/01/rdf-schema#' : 'rdfs',
    'http://purl.org/collections/w4ra/speakle/' : 'speakle',
    'http://purl.org/collections/w4ra/radiomarche/' : 'radiomarche',
    'http://lexvo.org/ontology#' : 'lexvo',
    'http://example.org/chickenvaccinationsapp/' : 'cv'
}
#default language
defaultLanguage = "en"
#audio files locations: THESE PATHS MUST POINT TO THE SAME LOCATION
audioURLbase = "http://heidrunn.nl/audio/"
audioPath = "/tmp/"
allowedUploadExtensions = set(['wav'])


#debug mode
debug=True

#python files location
pythonFilesDir = "/home/pi/KasaDaka/FlaskKasadaka/FlaskKasadaka/"

