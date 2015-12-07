
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

from getSparql import executeSparqlQuery

import config
import callhandler


app = Flask(__name__)
@app.route('/')
def index():
    return 'This is the Kasadaka Vxml generator'

@app.route('/main.vxml')
def main():
    # if 'lang' in request.args:
        lang = config.LanguageVars(request.args)
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
    # else:
        #give your language
        # languageQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        #     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        #     PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        #     PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        #
        #     SELECT DISTINCT ?voicelabel   WHERE {
        #     ?voicelabel   rdfs:subPropertyOf speakle:voicelabel
        #
        #     }
        #     LIMIT 9"""
        # languages = executeSparqlQuery(languageQuery)
        #
        # return render_template(
        # 'menu.vxml',
        # options = languages,
        # interfaceAudioDir = config.LanguageVars.audioInterfaceURL,
        # questionAudio = "chooseLanguage.wav"

        # )


@app.route('/requestProductOfferings.vxml')
def requestProductOfferings():
    #process the language
    lang = config.LanguageVars(request.args)


    #if the chosen product has been entered, show 20 results
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
        }
        LIMIT 20"""
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
    }
    LIMIT 9"""
    query = lang.replaceVoicelabels(query)
    choices = executeSparqlQuery(query)
    #add the url of this page to the links, so the user gets the results
    #also keep the language
    for choice in choices:
        choice[0] = 'requestProductOfferings.vxml?lang='+lang.language+'&product=' + choice[0]

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
    lang = config.LanguageVars(request.args)


    #if all the nessecary variables are set, update data in store
    if 'user' in request.args and 'product' in request.args and 'location' in request.args and 'price' in request.args and 'currency' in request.args and 'quantity' in request.args and 'confirm' in request.args:
        user = request.args['user']
        product = request.args['product']
        location = request.args['location']
        price = request.args['price']
        currency = request.args['currency']
        quantity = request.args['quantity']
        confirm = request.args['confrim']

        #TODO keuze in query maken
        #TODO confirm eerst doen
        results = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                     ?person  rdf:type radiomarche:Person  .
                     ?person radiomarche:contact_fname ?fname .
                     ?person radiomarche:contact_lname ?lname.
                     ?person speakle:voicelabel_en ?voicelabel_en
            }
            LIMIT 10"""

            )
        return render_template(
            'result.vxml',
            interfaceAudioDir = config.interfaceURL,
            messageAudio = 'presentProductOfferings.wav',
            redirect = 'main.vxml',
            results = results)


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
        }
        LIMIT 10""")

    productChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                     ?person  rdf:type radiomarche:Person  .
                     ?person radiomarche:contact_fname ?fname .
                     ?person radiomarche:contact_lname ?lname.
                     ?person speakle:voicelabel_en ?voicelabel_en
            }
            LIMIT 10""")
    locationChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                     ?person  rdf:type radiomarche:Person  .
                     ?person radiomarche:contact_fname ?fname .
                     ?person radiomarche:contact_lname ?lname.
                     ?person speakle:voicelabel_en ?voicelabel_en
            }
            LIMIT 10""")
    currencyChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                     ?person  rdf:type radiomarche:Person  .
                     ?person radiomarche:contact_fname ?fname .
                     ?person radiomarche:contact_lname ?lname.
                     ?person speakle:voicelabel_en ?voicelabel_en
            }
            LIMIT 10""")

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
    interfaceAudioDir = lang.audioInterfaceURL
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)