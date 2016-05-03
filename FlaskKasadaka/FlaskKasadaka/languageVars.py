import config
from sparqlInterface import executeSparqlQuery

class LanguageVars(object):
    audioURL = config.audioURLbase + config.defaultLanguage + "/"
    audioInterfaceURL = config.audioURLbase + config.defaultLanguage + "/interface/"
    language = config.defaultLanguage

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

def getVoiceLabels(uri,giveColumns = True,returnEmptyVoiceLabels = True):
    languagesQuery =""" SELECT DISTINCT  ?voicelabel  WHERE {
        ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.    }"""
    outputLanguagesQuery = executeSparqlQuery(languagesQuery)
    queryBuilder1 = """ SELECT DISTINCT """
    queryBuilder2 = """ """
    queryBuilder3 = """  WHERE {"""
    queryBuilder4 = """ """
    queryBuilder5 = """ FILTER(?uri=<""" + uri +""">) }"""
    voiceLabels = []
    for language in outputLanguagesQuery:
        queryBuilder2 =  " ?" + language[0].rsplit('/', 1)[-1]
        queryBuilder4 = " " + "OPTIONAL{?uri <"+language[0]+"> ?" + language[0].rsplit('/', 1)[-1] + " } "
        voiceLabelQuery = queryBuilder1 + queryBuilder2 + queryBuilder3 + queryBuilder4 + queryBuilder5
        voiceLabelResult = executeSparqlQuery(voiceLabelQuery,giveColumns=giveColumns,httpEncode=False)
        if len(voiceLabelResult[1]) is not 0:
            audio = voiceLabelResult[1][0]
            voiceLabels.append([voiceLabelResult[0][0],audio])
        elif returnEmptyVoiceLabels == True:
            audio = ""
            voiceLabels.append([voiceLabelResult[0][0],audio])
    return voiceLabels