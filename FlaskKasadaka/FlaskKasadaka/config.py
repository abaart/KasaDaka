
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

#URI of graph to use
sparqlGraph = "http://localhost/chickenvaccination"

#TODO implement automatic insertion of prefixes
sparqlPrefixes = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
PREFIX lexvo: <http://lexvo.org/ontology#>
PREFIX cv: <http://example.org/chickenvaccinationsapp/>
"""

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

##DO NOT EDIT BELOW THIS line




		
