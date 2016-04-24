
#Change these variables according to your installation

#Sparql endpoint
sparqlURL = "http://127.0.0.1:3020/sparql/"

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
		
