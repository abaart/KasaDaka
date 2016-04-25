
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

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
#audio files location
audioURLbase = "http://127.0.0.1/audio/"

#debug mode
debug=True

#python files location
pythonFilesDir = "/home/pi/KasaDaka/FlaskKasadaka/FlaskKasadaka/"

##DO NOT EDIT BELOW THIS line



class LanguageVars(object):
    audioURL = audioURLbase + defaultLanguage + "/"
    audioInterfaceURL = audioURLbase + defaultLanguage + "/interface/"
    language = defaultLanguage

    def replaceVoicelabels(self,inputQuery,
    voicelabelToReplace = "speakle:voicelabel_en",
    voicelabelReplacement = "speakle:voicelabel_"):
        return inputQuery.replace(voicelabelToReplace,voicelabelReplacement+self.language)

    def __init__(self,languageInit):
        if type(languageInit) is not str and 'lang' in languageInit:
             self.audioURL = audioURLbase + languageInit['lang'] + "/"
             self.audioInterfaceURL = audioURLbase + languageInit['lang'] + "/interface/"
             self.language = languageInit['lang']
        elif type(languageInit) is str:
            self.audioURL = audioURLbase + languageInit + "/"
            self.audioInterfaceURL = audioURLbase + languageInit + "/interface/"
            self.language = languageInit

    def __str__(self):
        return language
		
