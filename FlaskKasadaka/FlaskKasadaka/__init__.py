from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
import sparqlInterface
from datetime import datetime,date
from werkzeug import secure_filename
import config
from languageVars import LanguageVars, getVoiceLabels
import sparqlHelper
import languageVars

import subprocess
import shutil
import glob
import re
import urllib
import copy
import os.path
import os
from base64 import b16encode , b16decode

app = Flask(__name__)
app.secret_key = 'asdfbjarbja;kfbejkfbasjkfbslhjvbhcxgxui328'
app.config['UPLOAD_FOLDER'] = config.audioPath



@app.route('/')
def index():
    """ Index page
	Only used to confirm hosting is working correctly
	"""
    return 'This is the Kasadaka Vxml generator'

@app.route('/admin/audio', methods=['GET','POST'])
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
    resources = executeSparqlQuery(getAllResourcesQuery)
    sparqlNonExistingWaveFiles = []
    for resource in resources:
        voiceLabels = getVoiceLabels(resource[0],returnEmptyVoiceLabels=False)
        for audioFile in voiceLabels:
            url = audioFile[1]
            if not urllib.urlopen(url).getcode() == 200:
                sparqlNonExistingWaveFiles.append(audioFile[1])
                sparqlNonExistingWaveFiles = sorted(sparqlNonExistingWaveFiles)

    return render_template('admin/audio.html',
        languages = languages,
        notAvailableWaveFiles = sparqlNonExistingWaveFiles)

def recordAudio(language,URI = ""):
    getResourcesMissingVoicelabelQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER(NOT EXISTS {?subject <"""+language+"""> ?voicelabel_en .})
        }"""
    resourcesMissingVoicelabels = executeSparqlQuery(getResourcesMissingVoicelabelQuery)
    if len(URI) == 0: URI = resourcesMissingVoicelabels[0][0]
    resourceDataQuery = """SELECT DISTINCT  ?1 ?2  WHERE {
          ?uri   ?1 ?2.
         FILTER(?uri=<"""+URI+""">)}"""
    proposedWavURL = config.audioPath + URI.rsplit('/', 1)[-1] + "_"+language.rsplit('/', 1)[-1] +".wav"

    resourceData = executeSparqlQuery(resourceDataQuery,httpEncode=False)


    return render_template('admin/record.html',uri=URI,data=resourceData,proposedWavURL=proposedWavURL,language=language.rsplit('/', 1)[-1],langURI=language)

def processAudio(request):
    fileExists = os.path.isfile(request.form['filename'])
    file = request.files['file']
    #if file and allowed_file(file.filename):
        #filename = secure_filename(file.filename)
        #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    file.save(request.form['filename'])
    size = os.stat(request.form['filename']).st_size
    if size > 0: flash('File saved successfully! bytes:'+str(size))
    else:
        flash("Error: file "+str(size)+" bytes.")
        return recordAudio(request.form['lang'])

    URL = config.audioURLbase + request.form['filename'].rsplit('/', 1)[-1]
    insertVoicelabelQuery = """INSERT DATA {
    <"""+ request.form['uri'] + """> <"""+ request.form['lang'] +"""> <""" + URL + """>.
    }"""
    insertSuccess = executeSparqlUpdate(insertVoicelabelQuery)
    if insertSuccess: flash("Voicelabel sucessfully inserted in to triple store!")
    else: flash("Error in inserting triples")
    return recordAudio(request.form['lang'],request.form['uri'])


@app.route('/admin')
def adminIndex():
    return render_template('admin/index.html')

@app.route('/admin/object')
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
        'admin/object.html',
        data = result, 
        fieldNames = fieldNames, 
        uri = URI,
        voiceLabelResults = voiceLabels,
        objectTypeLabel=objectTypeLabel)

@app.route('/admin/list')
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
    return render_template('admin/list.html',
        data=output,
        fieldNames = fieldNames,
        objectTypeLabel = objectTypeLabel,
        objectTypeBaseEncoded = objectTypeBaseEncoded,
        recordURIs = recordURIs
        )

@app.route('/admin/new')
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
                    'admin/object.html',
                    data = properties, 
                    fieldNames = fieldNames, 
                    uri = 'NEW ' + objectTypeLabel,
                    new=True,
                    objectTypeLabel = objectTypeLabel,
                    objectType = objectType)

@app.route('/admin/insert', methods=['POST'])
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


@app.route('/admin/update', methods=['POST'])
def updateObject():
    if 'uri' not in request.form: return "Error, no uri specified"    
    URI = request.form['uri']
    objectType = sparqlHelper.determineObjectType(URI)
    properties = sparqlHelper.getDataStructure(objectType)
    insertTuples = createDataTuples(properties,request)
    deleteProperties = properties
    success = sparqlHelper.objectUpdate(URI,deleteProperties,insertTuples)
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

@app.route('/declareBornChickenBatch.vxml',methods=['GET'])
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

@app.route('/insertBornChickenBatch.vxml',methods=['GET'])
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
    currentDate = date.today().strftime("%Y-%m-%d")
    recordingLocation = recordingLocation.replace(config.audioPath,config.audioURLbase)
    tuples = [["http://example.org/chickenvaccinationsapp/birth_date",currentDate],
        ["http://example.org/chickenvaccinationsapp/owned_by",user],
        [voicelabelLanguage,recordingLocation]]
    return len(sparqlHelper.insertObjectTriples(preferredURI,objectType,tuples)) != 0


def saveRecording(path):
    #remove file:// if present
    #a lot of %00 stuff to remove
    path =  path.replace("\00","")
    path = re.sub(r"(file:\/\/)?(.*)",r"\2",path)
    dest = findFreshFilePath(config.recordingsPath+ "recording.wav")
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



@app.route('/chickenvaccination_main.vxml',methods=['GET'])
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


@app.route('/chickenvaccination.vxml',methods=['GET'])
def callerID():
    if 'callerid' in request.args:
        user = callerIDLookup(request.args['callerid'])
        if len(user) != 0:
            preferredLanguage = preferredLanguageLookup(user)
            lang = LanguageVars(preferredLanguage.rsplit('_', 1)[-1])
            userVoiceLabel = lang.getVoiceLabel(user) 
            welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
            return render_template('message.vxml',
                messages = [welcomeMessage,userVoiceLabel],
                redirect = "chickenvaccination_main.vxml?user=" + b16encode(user))
        else:
            return newUserVXML(request.args['callerid'])
    else:
        return errorVXML()

#TODO tidying
def askLanguageVXML(redirect,passOnVariables):
    languages = languageVars.getVoiceLabelPossibilities()
    for language in languages:
        language.append(config.audioURLbase + language[0].rsplit('_', 1)[-1] + "/interface/" + language[0].rsplit('/', 1)[-1] + ".wav")
        language.append(language[0].rsplit('_', 1)[-1])
        language[0] = b16encode(language[0])
    return render_template(
    'language.vxml',
    options = languages,
    audioDir = config.audioURLbase,
    questionAudio = config.audioURLbase+config.defaultLanguage+"/interface/chooseLanguage.wav",
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

@app.route('/recordUserName.vxml',methods=['GET'])
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

@app.route('/insertNewUser.vxml',methods=['GET'])
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
    recordingLocation = recordingLocation.replace(config.audioPath,config.audioURLbase)
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
    result = sparqlInterface.selectTriples(field,triples)
    if len(result) == 0: return config.defaultLanguageURI
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
    
@app.route('/error.vxml')
def errorVXML(language="en"):
    lang = LanguageVars(language)
    return render_template('message.vxml',
        messages = [lang.audioInterfaceURL + 'error.wav'],
            redirect = 'error.vxml')


@app.route('/main.vxml')
def main():
    if 'lang' in request.args:
        lang = LanguageVars(request.args)
        #list of options in initial menu: link to file, and audio description of the choice
        options = [
                ['requestProductOfferings.vxml?lang='+lang.language,    lang.audioInterfaceURL+'requestProductOfferings.wav'],
                ['placeProductOffer.vxml?lang='+lang.language,   lang.audioInterfaceURL+'placeProductOffer.wav']
                ]


        return render_template(
        'main.vxml',
        interfaceAudioDir = lang.audioInterfaceURL,
        welcomeAudio = 'welcome.wav',
        questionAudio = "mainMenuQuestion.wav",
        options = options)
    else:
        #give your language
        languagesQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        PREFIX lexvo: <http://lexvo.org/ontology#>

        SELECT DISTINCT  ?voicelabel  WHERE {
              ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.

        }"""
        languages = executeSparqlQuery(languagesQuery)
        for language in languages:
            language.append(config.audioURLbase + language[0].rsplit('_', 1)[-1] + "/interface/" + language[0].rsplit('/', 1)[-1] + ".wav")
            language.append(language[0].rsplit('_', 1)[-1])
            language[0] = "main.vxml?lang=" + language[0].rsplit('_', 1)[-1]


        return render_template(
        'language.vxml',
        options = languages,
        audioDir = config.audioURLbase,
        questionAudio = config.audioURLbase+config.defaultLanguage+"/interface/chooseLanguage.wav"
        )



@app.route('/requestProductOfferings.vxml')
def requestProductOfferings():
    #process the language
    lang = LanguageVars(request.args)

    #if the chosen product has been entered, show results
    if 'product' in request.args:
        choice = request.args['product']

        query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT  ?quantity_voicelabel ?contact_voicelabel ?price_voicelabel ?currency_voicelabel WHERE {
        #get offers of selected product
        ?offering rdf:type	radiomarche:Offering.
        ?offering radiomarche:prod_name <"""+choice+ """>.

        #get contact
        ?offering radiomarche:has_contact ?contact.
        ?contact speakle:voicelabel_en ?contact_voicelabel.
        #get quantity
        ?offering radiomarche:quantity ?quantity.
        ?quantity speakle:voicelabel_en ?quantity_voicelabel.

        #get price
        ?offering radiomarche:price ?price.
        ?price speakle:voicelabel_en ?price_voicelabel.

        #get currency
        ?offering radiomarche:currency ?currency.
        ?currency speakle:voicelabel_en ?currency_voicelabel
        }"""
        query = lang.replaceVoicelabels(query)

        results = executeSparqlQuery(query)

        return render_template(
            'result.vxml',
            interfaceAudioDir = lang.audioInterfaceURL,
            messageAudio = 'presentProductOfferings.wav',
            redirect = 'main.vxml?lang='+lang.language,
            results = results)


    #if no choice was made, offer choices of products to get offerings from
    query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?product ?voicelabel_en  WHERE {
    ?product rdf:type	radiomarche:Product.
    ?product speakle:voicelabel_en ?voicelabel_en
    }"""
    query = lang.replaceVoicelabels(query)
    choices = executeSparqlQuery(query)
    #add the url of this page to the links, so the user gets the results
    #also keep the language
    for choice in choices:
        choice[0] = 'requestProductOfferings.vxml?lang='+lang.language+'&amp;product=' + choice[0]

    return render_template(
    'menu.vxml',
    options = choices,
    interfaceAudioDir = lang.audioInterfaceURL,
    questionAudio = "chooseYourProduct.wav"
    )

@app.route('/placeProductOffer.vxml')
def placeProductOffer():
#for this function, a lot of things are defined in the template 'placeProductOffer.vxml'. You will need to edit this file as well.
    #process the language

    lang = LanguageVars(request.args)

    #if all the nessecary variables are set, update data in store
    if 'user' in request.args and 'product' in request.args and 'location' in request.args and 'price' in request.args and 'currency' in request.args and 'quantity' in request.args:
        user = request.args['user']
        product = request.args['product']
        location = request.args['location']
        price = request.args['price']
        currency = request.args['currency']
        quantity = request.args['quantity']


        #determine next number for offering (add to the already existing offerings)
        allOfferings = executeSparqlQuery("""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT ?offering   WHERE {
        ?offering rdf:type	radiomarche:Offering.
        }""")
        highestCurrentOfferingNumber = 0
        for offering in allOfferings:
            #check the highest current offering in database
            if int(offering[0].rsplit('_', 1)[-1]) > highestCurrentOfferingNumber:
                highestCurrentOfferingNumber = int(offering[0].rsplit('_', 1)[-1])
        dateTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        #TODO confirm eerst doen
        offeringNumber = str(highestCurrentOfferingNumber + 1)
        insertQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        	INSERT  DATA
        { radiomarche:offering_xxxxx rdf:type  <http://purl.org/collections/w4ra/radiomarche/Offering> .
        radiomarche:offering_xxxxx radiomarche:currency  <"""+ currency +"""> .
        radiomarche:offering_xxxxx radiomarche:has_contact  <"""+ user +"""> .
        radiomarche:offering_xxxxx radiomarche:price  <http://purl.org/collections/w4ra/radiomarche/price-"""+ price +"""> .
        radiomarche:offering_xxxxx radiomarche:prod_name  <"""+ product +"""> .
        radiomarche:offering_xxxxx radiomarche:quantity  <http://purl.org/collections/w4ra/radiomarche/quantity-"""+ quantity +"""> .
        radiomarche:offering_xxxxx radiomarche:ts_date_entered  '"""+ dateTime +"""' .
        radiomarche:offering_xxxxx radiomarche:zone <"""+ location +"""> .
        }"""
        insertQuery = insertQuery.replace("offering_xxxxx","offering_"+offeringNumber)
        result = executeSparqlUpdate(insertQuery)
        #TODO doe een message dat alles gelukt is en terug naar main menu
        if result:
            return render_template(
                'message.vxml',
                redirect ="main.vxml?lang=" + lang.language,
                messageAudio = 'placeProductOffer_success.wav',
                interfaceAudioDir = lang.audioInterfaceURL)
        else:
            return render_template(
                'message.vxml',
                redirect ="main.vxml?lang=" + lang.language,
                messageAudio = 'error.wav',
                interfaceAudioDir = lang.audioInterfaceURL)


    #if no choice was made, present choice menu
    userChoices = executeSparqlQuery(
        """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                 ?person  rdf:type radiomarche:Person  .
                 ?person radiomarche:contact_fname ?fname .
                 ?person radiomarche:contact_lname ?lname.
                 ?person speakle:voicelabel_en ?voicelabel_en
        }""")

    productChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?product ?voicelabel_en  WHERE {
            ?product rdf:type	radiomarche:Product.
            ?product speakle:voicelabel_en ?voicelabel_en
            }""")
    locationChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?zone ?voicelabel  WHERE {
    ?zone rdf:type	radiomarche:Zone.
	?zone speakle:voicelabel_en ?voicelabel
    }""")
    currencyChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?currency ?voicelabel  WHERE {
    ?currency rdf:type	radiomarche:Currency.
	?currency speakle:voicelabel_en ?voicelabel
    }""")

    return render_template(
    'placeProductOffer.vxml',
    personOptions = userChoices,
    personQuestionAudio = "placeProductOffer_person.wav",
    productOptions = productChoices,
    productQuestionAudio = "placeProductOffer_product.wav",
    locationOptions = locationChoices,
    locationQuestionAudio = "placeProductOffer_location.wav",
    currencyOptions = currencyChoices,
    currencyQuestionAudio = "placeProductOffer_currency.wav",
    quantityQuestionAudio = "placeProductOffer_quantity.wav",
    priceQuestionAudio = "placeProductOffer_price.wav",
    interfaceAudioDir = lang.audioInterfaceURL,
    language = lang.language
    )


@app.route('/audioreferences.html')
def audioReferences():
    finalResultsInterface = []
    finalResultsSparql = []
    pythonFiles = glob.glob(config.pythonFilesDir+'*.py')
    pythonFiles.extend(glob.glob(config.pythonFilesDir+'templates/*'))
    resultsInterface = []
    wavFilePattern = re.compile("""([^\s\\/+"']+\.wav)""",re.I)
    for pythonFile in pythonFiles:
        text = open(pythonFile).read()
        for match in wavFilePattern.findall(text):
            #ignore match on regex above
            if match != "\.wav":
                resultsInterface.append(match)
    #remove duplicates
    resultsInterface.extend(['1.wav','2.wav','3.wav','4.wav','5.wav','6.wav','7.wav','8.wav','9.wav','0.wav','hash.wav','star.wav'])


    languages = []
    getLanguagesQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    PREFIX lexvo: <http://lexvo.org/ontology#>

    SELECT DISTINCT  ?voicelabel  WHERE {
          ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.



    }"""
    outputGetLanguagesQuery = executeSparqlQuery(getLanguagesQuery)
    #get the language code behind the last slash
    for string in outputGetLanguagesQuery:
        #also add the language itself to choose language
        resultsInterface.append(string[0].rsplit('/', 1)[-1]+".wav")
        #add the langauges
        languages.append(string[0].rsplit('/', 1)[-1])

    usedWaveFiles = set(resultsInterface)
    for lang in languages:
        nonExistingWaveFiles = []
        existingWaveFiles = []
        for waveFile in usedWaveFiles:

            url = config.audioURLbase +"/"+lang+"/interface/"+ waveFile
            if urllib.urlopen(url).getcode() == 200:
                existingWaveFiles.append(waveFile)
            else:
                nonExistingWaveFiles.append(waveFile)
                existingWaveFiles = sorted(existingWaveFiles)
                nonExistingWaveFiles = sorted(nonExistingWaveFiles)
        finalResultsInterface.append([lang,existingWaveFiles,nonExistingWaveFiles])

    #check the DB for subjects without a voicelabel
    noVoicelabelQuery = """
    SELECT DISTINCT ?subject   WHERE {
    ?subject rdf:type	rdfs:Resource .
    FILTER(NOT EXISTS {?subject speakle:voicelabel_en ?voicelabel_en .})
    }"""
    subjectsWithoutVoicelabel = executeSparqlQuery(noVoicelabelQuery)
    subjectsWithoutVoicelabel = sorted(subjectsWithoutVoicelabel)
            #TODO: implement language


    #check the DB for subjects with a voicelabel, to check whether it exists or not
    voicelabelQuery = """
    SELECT DISTINCT ?subject ?voicelabel_en  WHERE {
    ?subject rdf:type	rdfs:Resource .
    ?subject speakle:voicelabel_en ?voicelabel_en .
    }"""




    for lang in languages:


        voicelabelQuery = voicelabelQuery.replace("voicelabel_en","voicelabel_"+lang)
        subjectsWithVoicelabel = executeSparqlQuery(voicelabelQuery)
        sparqlNonExistingWaveFiles = []
        sparqlExistingWaveFiles = []
        for subject in subjectsWithVoicelabel:

            url = subject[1]
            if urllib.urlopen(url).getcode() == 200:
                sparqlExistingWaveFiles.append(subject[1])
            else:
                sparqlNonExistingWaveFiles.append(subject[1])
                sparqlExistingWaveFiles = sorted(sparqlExistingWaveFiles)
                sparqlNonExistingWaveFiles = sorted(sparqlNonExistingWaveFiles)
        finalResultsSparql.append([lang,sparqlExistingWaveFiles,sparqlNonExistingWaveFiles])



    return render_template(
    'audiofiles.html',
    scannedFiles = pythonFiles,
    interfaceResults = finalResultsInterface,
    subjectsWithoutVoicelabel = subjectsWithoutVoicelabel,
    sparqlResults = finalResultsSparql)


	


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)
