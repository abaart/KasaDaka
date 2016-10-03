
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

#URI of graph to use
sparqlGraph = "http://localhost/foroba-blon"

#key is rdf:type, values is array of properties to use
dataStructure = {
    'http://example.org/foroba-blon/message' : ['http://example.org/foroba-blon/contact_tel','http://example.org/foroba-blon/date']
}

#TODO implement automatic insertion of prefixes
sparqlPrefixes = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
PREFIX lexvo: <http://lexvo.org/ontology#>
PREFIX fb: <http://example.org/foroba-blon/>
"""
sparqlPrefixDict = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#' : 'rdf',
    'http://www.w3.org/2000/01/rdf-schema#' : 'rdfs',
    'http://purl.org/collections/w4ra/speakle/' : 'speakle',
    'http://purl.org/collections/w4ra/radiomarche/' : 'radiomarche',
    'http://lexvo.org/ontology#' : 'lexvo',
    'http://example.org/foroba-blon/' : 'fb'
}
#default language
defaultLanguage = "en"
defaultLanguageURI = "http://purl.org/collections/w4ra/speakle/voicelabel_en"
#audio files locations: THESE PATHS MUST POINT TO THE SAME LOCATION
# IMPORTANT: MAKE SURE TO CHMOD 777 THIS DIR
audioURLbase = "http://127.0.0.1/static/audio/"
audioPath = "/home/pi/KasaDaka/FlaskKasadaka/FlaskKasadaka/static/audio/"

#path to place user recordings
recordingsPath = audioPath + "user_recordings/"

allowedUploadExtensions = set(['wav'])

#date format in triple store
dateFormat = "%Y-%m-%d %H:%M:%S"

#debug mode
debug=True

#python files location
pythonFilesDir = "/home/pi/KasaDaka/FlaskKasadaka/FlaskKasadaka/"

