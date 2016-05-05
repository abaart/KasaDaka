
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

#URI of graph to use
sparqlGraph = "http://localhost/seedmarket"

#key is rdf:type, values is array of properties to use
dataStructure = {
    'http://example.org/seedmarketapp/user' : ['http://example.org/seedmarketapp/contact_fname','http://example.org/seedmarketapp/contact_lname','http://example.org/seedmarketapp/contact_tel','http://example.org/seedmarketapp/preferred_language'],
    'http://example.org/seedmarketapp/location' : ['http://example.org/seedmarketapp/country'],
    'http://example.org/seedmarketapp/seed' : ['http://example.org/seedmarketapp/country'],
    'http://example.org/seedmarketapp/seed_quality' : ['http://example.org/seedmarketapp/description'],
    'http://example.org/seedmarketapp/offering' : ['http://example.org/seedmarketapp/user','http://example.org/seedmarketapp/location','http://example.org/seedmarketapp/seed','http://example.org/seedmarketapp/seed_quality','http://example.org/seedmarketapp/quantity','http://example.org/seedmarketapp/currency','http://example.org/seedmarketapp/price'],
    'http://example.org/seedmarketapp/quantity' : ['http://example.org/seedmarketapp/description'],
    'http://example.org/seedmarketapp/currency' : ['http://example.org/seedmarketapp/description'],
    'http://example.org/seedmarketapp/price' : ['http://example.org/seedmarketapp/description']
}

#TODO implement automatic insertion of prefixes
sparqlPrefixes = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
PREFIX lexvo: <http://lexvo.org/ontology#>
PREFIX cv: <http://example.org/chickenvaccinationsapp/>
PREFIX      sm: <http://example.org/seedmarketapp/> 
"""
sparqlPrefixDict = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#' : 'rdf',
    'http://www.w3.org/2000/01/rdf-schema#' : 'rdfs',
    'http://purl.org/collections/w4ra/speakle/' : 'speakle',
    'http://purl.org/collections/w4ra/radiomarche/' : 'radiomarche',
    'http://lexvo.org/ontology#' : 'lexvo',
    'http://example.org/chickenvaccinationsapp/' : 'cv',
    'http://example.org/seedmarketapp/' : 'sm'
}
#default language
defaultLanguage = "en"
defaultLanguageURI = "http://purl.org/collections/w4ra/speakle/voicelabel_en"
#audio files locations: THESE PATHS MUST POINT TO THE SAME LOCATION
# IMPORTANT: MAKE SURE TO CHMOD 777 THIS DIR
audioURLbase = "http://127.0.0.1/audio/"
audioPath = "/home/pi/KasaDaka/html/audio/"

#path to place user recordings
recordingsPath = audioPath + "user_recordings/"

allowedUploadExtensions = set(['wav'])


#debug mode
debug=True

#python files location
pythonFilesDir = "/home/pi/KasaDaka/FlaskKasadaka/FlaskKasadaka/"

