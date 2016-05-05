import config
from sparqlInterface import executeSparqlQuery, validURI

class LanguageVars(object):
    audioURL = config.audioURLbase + config.defaultLanguage + "/"
    audioInterfaceURL = config.audioURLbase + config.defaultLanguage + "/interface/"
    language = config.defaultLanguage
    languageURI = ""

    #TODO remove unused?
    def replaceVoicelabels(self,inputQuery,
    voicelabelToReplace = "speakle:voicelabel_en",
    voicelabelReplacement = "speakle:voicelabel_"):
        return inputQuery.replace(voicelabelToReplace,voicelabelReplacement+self.language)

    #TODO base encoding
    def getVoiceLabel(self,URI):
        allVoiceLabels = getVoiceLabels(URI)
        result = ""
        for voicelabel in allVoiceLabels:
            if voicelabel[0] == "voicelabel_" + self.language:
                result = voicelabel[1]
        return result

    def getInterfaceAudioURL(self,audioFile):
        return self.audioInterfaceURL + audioFile

    def __init__(self,languageInit):
        if type(languageInit) is not str and 'lang' in languageInit:
            self.languageURI = languageInit
            self.audioURL = config.audioURLbase + languageInit['lang'] + "/"
            self.audioInterfaceURL = config.audioURLbase + languageInit['lang'] + "/interface/"
            self.language = languageInit['lang']
        elif type(languageInit) is str and not validURI(languageInit):
            self.languageURI = languageInit
            self.audioURL = config.audioURLbase + languageInit + "/"
            self.audioInterfaceURL = config.audioURLbase + languageInit + "/interface/"
            self.language = languageInit
        elif type(languageInit) is str and validURI(languageInit):
            self.languageURI = languageInit
            self.language = languageInit.rsplit('_', 1)[-1]
            self.audioURL = config.audioURLbase + self.language + "/"
            self.audioInterfaceURL = self.audioURL + "interface/"


    def __str__(self):
        return languageURI

def getVoiceLabelPossibilities():
    languagesQuery =""" SELECT DISTINCT  ?voicelabel  WHERE {
        ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.    }"""
    outputLanguagesQuery = executeSparqlQuery(languagesQuery)
    return outputLanguagesQuery

#TODO base encoding
def getVoiceLabels(uri,giveColumns = True,returnEmptyVoiceLabels = True,changeLocalhostIP = "127.0.0.1"):
    VoiceLabelPossibility = getVoiceLabelPossibilities()
    queryBuilder1 = """ SELECT DISTINCT """
    queryBuilder2 = """ """
    queryBuilder3 = """  WHERE {"""
    queryBuilder4 = """ """
    queryBuilder5 = """ FILTER(?uri=<""" + uri +""">) }"""
    voiceLabels = []
    for language in VoiceLabelPossibility:
        queryBuilder2 =  " ?" + language[0].rsplit('/', 1)[-1]
        queryBuilder4 = " " + "OPTIONAL{?uri <"+language[0]+"> ?" + language[0].rsplit('/', 1)[-1] + " } "
        voiceLabelQuery = queryBuilder1 + queryBuilder2 + queryBuilder3 + queryBuilder4 + queryBuilder5
        voiceLabelResult = executeSparqlQuery(voiceLabelQuery,giveColumns=giveColumns,httpEncode=False)
        if len(voiceLabelResult[1]) is not 0:
            audio = voiceLabelResult[1][0]
            if changeLocalhostIP: audio = audio.replace("127.0.0.1",changeLocalhostIP)
            voiceLabels.append([voiceLabelResult[0][0],audio])
        elif returnEmptyVoiceLabels == True:
            audio = ""
            voiceLabels.append([voiceLabelResult[0][0],audio])
    return voiceLabels