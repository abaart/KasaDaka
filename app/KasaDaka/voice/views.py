from flask import request, session, g, redirect, url_for, abort, render_template, flash, current_app


from ..voice import voice

from datetime import datetime,date
from .. import languageVars
from ..languageVars import LanguageVars, getVoiceLabels
from ..sparql import sparqlHelper, sparqlInterface
from .. import config
import subprocess
import re
import os.path
import os
from base64 import b16encode , b16decode

@voice.route('/reminder.vxml',methods=['GET'])
def reminderVXML():
    if 'user' not in request.args: return errorVXML(error="No user defined to look up reminders")
    user = b16decode(request.args['user'])
    if 'action' in request.args and request.args['action'] == 'received':
        return markReminderResult(user,True)
    if 'action' in request.args and request.args['action'] == 'failed':
        return markReminderResult(user,False)
    return generateReminderMessage(user)

def markReminderResult(userURI,received):
    lang = LanguageVars(preferredLanguageLookup(userURI))
    receivedURI = "http://example.org/chickenvaccinationsapp/reminder"
    objectType = 'http://example.org/chickenvaccinationsapp/outgoing_reminder'
    tuples = [['http://example.org/chickenvaccinationsapp/user',userURI],['http://example.org/chickenvaccinationsapp/date',str(datetime.now().isoformat())],['http://example.org/chickenvaccinationsapp/received',str(received)]]
    success = sparqlHelper.insertObjectTriples(receivedURI,objectType,tuples)
    messages = [lang.getInterfaceAudioURL('userDidNotConfirm.wav')]
    if received: messages = [lang.getInterfaceAudioURL('reminderMarkedReceived.wav'),lang.getInterfaceAudioURL('thanks.wav')]
    return render_template('message.vxml',
        messages = messages)

def lookupVaccinations():
    """
    Returns array of vaccinations, with properties in order as in second argument of objectList call.
    """
    return sparqlHelper.objectList('http://example.org/chickenvaccinationsapp/vaccination',['http://example.org/chickenvaccinationsapp/days_after_birth','http://example.org/chickenvaccinationsapp/description','http://example.org/chickenvaccinationsapp/treats'])



def lookupChickenBatches(userURI,giveBirthDates = False):
    """
    Returns an array of chicken batches belonging to an user.
    """
    field = ['chicken_batch']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?chicken_batch','http://example.org/chickenvaccinationsapp/owned_by','?userURI']]
    filter = ['userURI',userURI]
    if giveBirthDates:
        field.append('birth_date')
        triples.append(['?chicken_batch','http://example.org/chickenvaccinationsapp/birth_date','?birth_date'])
    return sparqlInterface.selectTriples(field, triples, filter)

def lookupVaccinationReminders(userURI):
    """
    Returns an array of triples (chicken batch URI, vaccination URI,disease URI)
    Of the vaccination needed for an user's chicken batches
    """
    date_format = config.DATEFORMAT
    chickenBatches = lookupChickenBatches(userURI,giveBirthDates = True)
    vaccinations = lookupVaccinations()
    results = []
    for chickenBatch in chickenBatches:
        birthDate = datetime.strptime(chickenBatch[1],date_format)
        currentDate = datetime.now()
        for index, vaccination in enumerate(vaccinations):
            vaccinationDays = vaccination[1]
            if int(vaccinationDays) == int((currentDate - birthDate).days):
                results.append([chickenBatch[0],vaccination[0],vaccination[3]])
    return results


def generateReminderMessage(userURI):
    lang = LanguageVars(preferredLanguageLookup(userURI))
    batchVaccinations = lookupVaccinationReminders(userURI)
    welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
    userVoiceLabel = lang.getVoiceLabel(userURI)
    messages = [welcomeMessage,userVoiceLabel]
    reminders = []
    if len(batchVaccinations) == 0:
        messages.append(lang.getInterfaceAudioURL('currentlyNoVaccinationsNeeded.wav'))
    else:
        messages.append(lang.getInterfaceAudioURL('reminderIntro.wav'))
        for batchVaccination in batchVaccinations:
            batchVoicelabel = lang.getVoiceLabel(batchVaccination[0])
            vaccinationVoicelabel = lang.getVoiceLabel(batchVaccination[1])
            diseaseVoicelabel = lang.getVoiceLabel(batchVaccination[2])
            if len(batchVoicelabel) == 0 or len(vaccinationVoicelabel) == 0 or len(diseaseVoicelabel) == 0:
                return errorVXML(error="Voicelabel does not exist: " + str(batchVaccination))
            reminder = [lang.getInterfaceAudioURL('for.wav'),batchVoicelabel,lang.getInterfaceAudioURL('toPreventDisease.wav'),diseaseVoicelabel,lang.getInterfaceAudioURL('useVaccination.wav'),vaccinationVoicelabel,lang.getInterfaceAudioURL('press1ToConfirm.wav')]
            reminders.append(reminder)
    return render_template('reminder.vxml',
        messages = messages,
        reminders=reminders,
        userURI = b16encode(userURI))
    #return messages



@voice.route('/declareBornChickenBatch.vxml',methods=['GET'])
def cvNewChickenBatchVXML():
    if 'user' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    preMessages = [lang.getInterfaceAudioURL('speakChickenBatchName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['user',request.args['user']]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'insertBornChickenBatch.vxml')

@voice.route('/insertBornChickenBatch.vxml',methods=['GET'])
def cvInsertNewChickenBatchVXML():
    if 'user' not in request.args or 'recording' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    recordingLocation = request.args['recording']
    recordingLocation = saveRecording(recordingLocation)
    success = insertNewChickenBatch(recordingLocation,user)
    if success:
        messages = [lang.getInterfaceAudioURL('insertChickenBatchSuccess.wav')]
        return render_template('message.vxml',
            messages = messages,
            redirect = "chickenvaccination_main.vxml?user="+request.args['user'])
    else: return errorVXML()

def insertNewChickenBatch(recordingLocation,user):
    voicelabelLanguage = preferredLanguageLookup(user)
    objectType =  "http://example.org/chickenvaccinationsapp/chicken_batch"
    preferredURI = objectType
    currentDate = date.today().strftime(config.DATEFORMAT)
    recordingLocation = recordingLocation.replace(config.AUDIOPATH,config.AUDIOURLBASE)
    tuples = [["http://example.org/chickenvaccinationsapp/birth_date",currentDate],
        ["http://example.org/chickenvaccinationsapp/owned_by",user],
        [voicelabelLanguage,recordingLocation]]
    return len(sparqlHelper.insertObjectTriples(preferredURI,objectType,tuples)) != 0


def saveRecording(path):
    #remove file:// if present
    #a lot of %00 stuff to remove
    path =  path.replace("\00","")
    path = re.sub(r"(file:\/\/)?(.*)",r"\2",path)
    dest = findFreshFilePath(config.RECORDINGSPATH+ "recording.wav")
    #convert to format that is good for vxml as well as web interface
    subprocess.call(['/usr/bin/sox',path,'-r','8k','-c','1','-e','signed-integer',dest])
    #shutil.copy(path,dest)
    return dest

def findFreshFilePath(preferredPath):
    addition = 1
    path = re.sub(r"(.*\/)(\w*)(\.\w{3})",r"\1\2" + "_" + str(addition) + r"\3",preferredPath)
    while os.path.isfile(path):
        addition = addition + 1
        path = re.sub(r"(.*\/)(\w*)(\.\w{3})",r"\1\2" + "_" + str(addition) + r"\3",preferredPath)
    return path



@voice.route('/chickenvaccination_main.vxml',methods=['GET'])
def cvMainMenuVXML():
    if 'user' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    #list of options in initial menu: link to file, and audio description of the choice
    options = [
            ['declareBornChickenBatch.vxml?user='+request.args['user'],lang.getInterfaceAudioURL('declareBornChickenBatch.wav')]
            ]
    return render_template(
        'main.vxml',
        interfaceAudioDir = lang.audioInterfaceURL,
        welcomeAudio = 'welcomeMainMenu.wav',
        questionAudio = "mainMenuQuestion.wav",
        options = options)


@voice.route('/chickenvaccination.vxml',methods=['GET'])
def callerID():
    if 'callerid' in request.args:
        callerID = preProcessCallerID(request.args['callerid'])
        user = callerIDLookup(callerID)
        if len(user) != 0:
            preferredLanguage = preferredLanguageLookup(user)
            lang = LanguageVars(preferredLanguage.rsplit('_', 1)[-1])
            userVoiceLabel = lang.getVoiceLabel(user)
            welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
            return render_template('message.vxml',
                messages = [welcomeMessage,userVoiceLabel],
                redirect = "chickenvaccination_main.vxml?user=" + b16encode(user))
        else:
            return newUserVXML(callerID)
    else:
        return errorVXML()

def preProcessCallerID(callerID):
    """
    remove any spaces or plus signs from the callerID
    """
    processed = re.sub(r"(\s*\+*)(\d+)",r"\2",callerID)
    return processed

#TODO tidying
def askLanguageVXML(redirect,passOnVariables):
    audioURLbase = config.AUDIOURLBASE
    languages = languageVars.getVoiceLabelPossibilities()
    for language in languages:
        language.append(audioURLbase + language[0].rsplit('_', 1)[-1] + "/interface/" + language[0].rsplit('/', 1)[-1] + ".wav")
        language.append(language[0].rsplit('_', 1)[-1])
        language[0] = b16encode(language[0])
    return render_template(
    'language.vxml',
    options = languages,
    audioDir = audioURLbase,
    questionAudio = audioURLbase+config.defaultLanguage+"/interface/chooseLanguage.wav",
    passOnVariables = passOnVariables,
    redirect = redirect
    )

def newUserVXML(callerID,lang=""):
    if len(callerID) == 0 : return errorVXML()
    if len(lang) == 0: return askLanguageVXML('recordUserName.vxml',[['callerid',b16encode(callerID)]])
    lang = LanguageVars(lang)
    preMessages = [lang.getInterfaceAudioURL('speakUserName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['callerid',callerID],['lang', lang]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'recordUserName.vxml')

@voice.route('/recordUserName.vxml',methods=['GET'])
def recordUserName():
    if 'callerid' not in request.args or 'lang' not in request.args: return errorVXML()
    lang = LanguageVars(b16decode(request.args['lang']))
    preMessages = [lang.getInterfaceAudioURL('speakUserName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['callerid',request.args['callerid']],
        ['lang',request.args['lang']]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'insertNewUser.vxml')

@voice.route('/insertNewUser.vxml',methods=['GET'])
def insertNewUserVXML():
    if 'callerid' not in request.args or 'lang' not in request.args or 'recording' not in request.args: return errorVXML()
    lang = LanguageVars(b16decode(request.args['lang']))
    callerID = b16decode(request.args['callerid'])
    recordingLocation = request.args['recording']
    recordingLocation = saveRecording(recordingLocation)
    newUserURI = insertNewUser(recordingLocation,callerID,str(lang))
    if len(newUserURI) != 0:
        messages = [lang.getInterfaceAudioURL('registerUserSuccess.wav')]
        return render_template('message.vxml',
            messages = messages,
            redirect = "chickenvaccination_main.vxml?user="+b16encode(newUserURI))
    else: return errorVXML()

def insertNewUser(recordingLocation,callerID,lang):
    objectType = "http://example.org/chickenvaccinationsapp/user"
    preferredURI = objectType
    audioPath = config.AUDIOPATH
    audioURLbase = config.AUDIOURLBASE
    recordingLocation = recordingLocation.replace(audioPath,audioURLbase)
    tuples = [["http://example.org/chickenvaccinationsapp/contact_fname","unknown"],
        ["http://example.org/chickenvaccinationsapp/contact_lname","unknown"],
        ["http://example.org/chickenvaccinationsapp/contact_tel",callerID],
        ["http://example.org/chickenvaccinationsapp/preferred_language",lang],
        [lang,recordingLocation]]
    return sparqlHelper.insertObjectTriples(preferredURI,objectType,tuples)

def preferredLanguageLookup(userURI):
    """
    Returns the URI of the preferred voicelabel (language) for an user.
    """
    field = ['preferred_language']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?userURI','http://example.org/chickenvaccinationsapp/preferred_language','?preferred_language']]
    filter = ['userURI',userURI]
    result = sparqlInterface.selectTriples(field,triples,filter)
    if len(result) == 0: return config.DEFAULTLANGUAGEURI
    else: return result[0][0]

def callerIDLookup(callerID):
    """
    Returns the URI of the user associated with the caller ID. Returns an empty string if no match.
    """
    callerID = callerID.replace(" ","+")
    field = ['userURI']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?userURI','http://example.org/chickenvaccinationsapp/contact_tel',callerID]]
    result = sparqlInterface.selectTriples(field,triples)
    if len(result) == 0: return ""
    else: return result[0][0]


@voice.route('/error.vxml')
def errorVXML(error="undefined error",language="en"):
    lang = LanguageVars(language)
    return render_template('message.vxml',
        messages = [lang.audioInterfaceURL + 'error.wav'],
            redirect = '',
            error=error)