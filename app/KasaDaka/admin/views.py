from flask import request, session, g, redirect, url_for, abort, render_template, flash, current_app

from . import admin
from ..sparql.sparqlInterface import executeSparqlQuery, executeSparqlUpdate, deleteObject
from ..languageVars import LanguageVars, getVoiceLabels
from ..sparql import sparqlHelper
from ..voice.views import generateReminderMessage
from .. import config
import subprocess
import glob
import re
import urllib
import os.path
import os
from base64 import b16encode , b16decode


@admin.route('/send_reminders')
def sendRemindersPage():
    return ""


@admin.route('/reminders')
def showReminders():
    if 'uri' in request.args: userURI = request.args['uri']
    else: userURI = ""
    users = executeSparqlQuery("""SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   cv:user .
        }""")
    if len(userURI) != 0:
        messages = generateReminderMessage(userURI)
        #TODO concatenateWavs maken
        #reminder = concatenateWavs(messages)
        reminder = ""
        reminderURL = reminder.replace(config.AUDIOPATH,config.AUDIOURLBASE)
        reminderURL = reminderURL.replace("127.0.0.1",request.host)
    else:
        reminderURL = ""
    return render_template('reminder.html',
        reminderURL = reminderURL,
        users = users,
        uri = userURI)

@admin.route('/audio', methods=['GET','POST'])
def adminAudio():
    if 'lang' in request.args and 'uri' in request.args:
        return recordAudio(request.args['lang'],request.args['uri'])
    elif 'lang' in request.args:
        return recordAudio(request.args['lang'])
    elif request.method == 'POST' and request.form['action'] == 'upload':
        return processAudio(request)
    else:
        return adminAudioHome()


def adminAudioHome():
    getLanguagesQuery = """SELECT DISTINCT  ?voicelabel  WHERE {
          ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.}"""
    languages = executeSparqlQuery(getLanguagesQuery)
    for language in languages:
        getNumberMissingVoicelabelsQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER(NOT EXISTS {?subject <"""+language[0]+"""> ?voicelabel_en .})
        }"""
        missingVoicelabels=executeSparqlQuery(getNumberMissingVoicelabelsQuery)
        language.append(len(missingVoicelabels))
    getAllResourcesQuery = """SELECT DISTINCT ?subject  WHERE {
    ?subject rdf:type   ?type .}"""
    sparqlResources = executeSparqlQuery(getAllResourcesQuery)
    sparqlNonExistingWaveFiles = []
    for resource in sparqlResources:
        voiceLabels = getVoiceLabels(resource[0],returnEmptyVoiceLabels=False)
        for audioFile in voiceLabels:
            url = audioFile[1]
            if not urllib.urlopen(url).getcode() == 200:
                sparqlNonExistingWaveFiles.append(audioFile[1])
    sparqlNonExistingWaveFiles = sorted(set(sparqlNonExistingWaveFiles))

    finalResultsInterface = []
    pythonFilesDir =config.PYTHONFILESDIR
    pythonFiles = glob.glob(pythonFilesDir+'*.py')
    pythonFiles.extend(glob.glob(pythonFilesDir+'templates/*.html'))
    pythonFiles.extend(glob.glob(pythonFilesDir+'templates/*.vxml'))
    pythonFiles.extend(glob.glob(pythonFilesDir+'templates/*.html'))
    waveFilesInterface = []
    wavFilePattern = re.compile("""([^\s\\/+"'\*]+\.wav)""",re.I)
    for pythonFile in pythonFiles:
        text = open(pythonFile).read()
        for match in wavFilePattern.findall(text):
            #ignore match on regex above
            if match != "\.wav":
                waveFilesInterface.append(match)
    #remove duplicates
    waveFilesInterface.extend(['1.wav','2.wav','3.wav','4.wav','5.wav','6.wav','7.wav','8.wav','9.wav','0.wav','hash.wav','star.wav'])
    waveFilesInterface = sorted(set(waveFilesInterface))
    nonExistingInterfaceWaveFiles = []
    for language in languages:
        lang = LanguageVars(language[0])
        for waveFile in waveFilesInterface:
            waveFileURL = lang.getInterfaceAudioURL(waveFile)
            if not urllib.urlopen(waveFileURL).getcode() == 200:
                nonExistingInterfaceWaveFiles.append(waveFileURL)
    nonExistingInterfaceWaveFiles = sorted(set(nonExistingInterfaceWaveFiles))


    return render_template('audio.html',
        languages = languages,
        notAvailableWaveFiles = sparqlNonExistingWaveFiles,
        waveFilesInterface=nonExistingInterfaceWaveFiles)

def recordAudio(language,URI = ""):
    getResourcesMissingVoicelabelQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER(NOT EXISTS {?subject <"""+language+"""> ?voicelabel_en .})
        }"""
    getResourcesHavingVoicelabelQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER( EXISTS {?subject <"""+language+"""> ?voicelabel_en .})
        }"""
    resourcesMissingVoicelabels = executeSparqlQuery(getResourcesMissingVoicelabelQuery)
    resourcesHavingVoicelabels = executeSparqlQuery(getResourcesHavingVoicelabelQuery)
    if len(URI) == 0: URI = resourcesMissingVoicelabels[0][0]
    resourceDataQuery = """SELECT DISTINCT  ?1 ?2  WHERE {
          ?uri   ?1 ?2.
         FILTER(?uri=<"""+URI+""">)}"""
    proposedWavURL = config.AUDIOPATH + URI.rsplit('/', 1)[-1] + "_"+language.rsplit('/', 1)[-1] +".wav"

    resourceData = executeSparqlQuery(resourceDataQuery,httpEncode=False)
    languageLabel = sparqlHelper.retrieveLabel(language)
    voiceLabelResults = getVoiceLabels(URI,changeLocalhostIP = request.host)
    return render_template('record.html',uri=URI,data=resourceData,proposedWavURL=proposedWavURL,language=language.rsplit('/', 1)[-1],langURI=language,resourcesMissingVoicelabels=resourcesMissingVoicelabels, resourcesHavingVoicelabels=resourcesHavingVoicelabels,languageLabel=languageLabel,voiceLabelResults=voiceLabelResults)

def processAudio(request):
    fileExists = os.path.isfile(request.form['filename'])
    file = request.files['file']
    #if file and allowed_file(file.filename):
        #filename = secure_filename(file.filename)
        #file.save(os.path.join(admin.config['UPLOAD_FOLDER'], filename))
    tempFileLocation = "/tmp/"+request.form['filename'].rsplit('/', 1)[-1]
    file.save(tempFileLocation)
    size = os.stat(tempFileLocation).st_size
    subprocess.call(['/usr/bin/sox',tempFileLocation,'-r','8k','-c','1','-e','signed-integer',request.form['filename']])
    if size > 0: flash('File saved successfully! bytes:'+str(size))
    else:
        flash("Error: file "+str(size)+" bytes.")
        return recordAudio(request.form['lang'])

    URL = config.AUDIOURLBASE + request.form['filename'].rsplit('/', 1)[-1]
    insertVoicelabelQuery = """INSERT DATA {
    <"""+ request.form['uri'] + """> <"""+ request.form['lang'] +"""> <""" + URL + """>.
    }"""
    insertSuccess = executeSparqlUpdate(insertVoicelabelQuery)
    if insertSuccess: return 'Upload Succesful!'+str(size)+" bytes."
    else: return "upload failed :("
    #if insertSuccess: flash("Voicelabel sucessfully inserted in to triple store!")
    #else: flash("Error in inserting triples")
    #return recordAudio(request.form['lang'],request.form['uri'])


@admin.route('/')
def adminIndex():
    return render_template('index.html')

@admin.route('/object')
def objectInfo():
    """
    Presents a page with all information about an object from the HTTP GET (base16 encoded).
    """
    if 'uri' not in request.args: return "Error, no uri specified"
    URI = b16decode(request.args['uri'])
    voiceLabels = getVoiceLabels(URI,changeLocalhostIP = request.host)
    objectType = sparqlHelper.determineObjectType(URI)
    fieldNames = sparqlHelper.propertyLabels(objectType)
    result = sparqlHelper.objectInfo(URI)
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    return render_template(
        'object.html',
        data = result,
        fieldNames = fieldNames,
        uri = URI,
        voiceLabelResults = voiceLabels,
        objectTypeLabel=objectTypeLabel)

@admin.route('/list')
def objectList(objectType = ""):
    """
    Presents a page with a list of all objects of a given type from the HTTP GET (base16 encoded)
    """
    if 'uri' not in request.args and len(objectType) == 0: return "Error, no uri specified"
    if len(objectType) == 0:
        objectTypeBaseEncoded = request.args['uri']
        objectType = b16decode(objectTypeBaseEncoded)
    else:
        objectTypeBaseEncoded = b16encode(objectType)
    output = sparqlHelper.objectList(objectType)
    fieldNames = sparqlHelper.propertyLabels(objectType,firstColumnIsURI=True)
    recordURIs = sparqlHelper.createURIarray(output)
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    return render_template('list.html',
        data=output,
        fieldNames = fieldNames,
        objectTypeLabel = objectTypeLabel,
        objectTypeBaseEncoded = objectTypeBaseEncoded,
        recordURIs = recordURIs
        )

@admin.route('/new')
def showNewObjectPage():
    if 'uri' not in request.args: return "Error, no uri specified"
    objectTypeBaseEncoded = request.args['uri']
    objectType = b16decode(objectTypeBaseEncoded)
    fieldNames = sparqlHelper.propertyLabels(objectType)
    properties = [[]]
    for prop in sparqlHelper.getDataStructure(objectType):
        properties[0].append(b16encode(prop))
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    return render_template(
                    'object.html',
                    data = properties,
                    fieldNames = fieldNames,
                    uri = 'NEW ' + objectTypeLabel,
                    new=True,
                    objectTypeLabel = objectTypeLabel,
                    objectType = objectType)

@admin.route('/insert', methods=['POST'])
def insertNewObject():
    if 'objectType' not in request.form: return "Error, no objectType specified"
    if 'uri' not in request.form: return "Error, no uri for new object specified"
    URI = request.form['uri']
    objectType = request.form['objectType']
    properties = sparqlHelper.getDataStructure(objectType)
    dataTuples = createDataTuples(properties,request)
    success = len(sparqlHelper.insertObjectTriples(URI,objectType,dataTuples))
    if success:
        flash(objectType+" successfully inserted! Please record audio for new "+objectType+" on audio page!")
    else:
        flash("Error inserting "+objectType)
    return objectList(objectType)

@admin.route('/delete', methods=['POST'])
def adminDeleteObject():
    if 'uri' not in request.form: return "Error, no uri specified"
    URI = request.form['uri']
    objectType = sparqlHelper.determineObjectType(URI)
    success = deleteObject(URI)
    if success:
        flash("URI:" + URI +' deleted!')
    else:
        flash('Error in deleting '+URI)
    return objectList(objectType)

@admin.route('/update', methods=['POST'])
def updateObject():
    if 'uri' not in request.form: return "Error, no uri specified"
    URI = request.form['uri']
    objectType = sparqlHelper.determineObjectType(URI)
    properties = sparqlHelper.getDataStructure(objectType)
    insertTuples = createDataTuples(properties,request)
    deleteProperties = properties
    objectInfo = sparqlHelper.objectInfo(URI,deleteProperties)[1]
    deleteTuples = []
    for index, prop in enumerate(deleteProperties):
        deleteTuples.append([prop,objectInfo[index]])
    if len(deleteProperties) != len(deleteTuples): raise ValueError('update error in retreiving triples to delete')
    success = sparqlHelper.objectUpdate(URI,deleteTuples,insertTuples)
    if success:
        flash(objectType+' data successfully updated!')
    else:
        flash('Error in updating '+objectType)
    return objectList(objectType)

def createDataTuples(properties, request):
    dataTuples = []
    for prop in properties:
        encodedProp = b16encode(prop)
        if encodedProp not in request.form: raise ValueError("Not all nessecary properties given! Missing: " + prop)
        if len(prop) == 0 or len(request.form[encodedProp]) == 0: raise ValueError('Empty tuple!')
        dataTuples.append([prop,request.form[encodedProp]])
    return dataTuples
