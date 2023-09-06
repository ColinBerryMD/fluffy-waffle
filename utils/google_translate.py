# use the google cloud account to translate between english and spanish
# CB 8/2023
from gevent import monkey
monkey.patch_all()

import grpc.experimental.gevent as grpc_gevent
grpc_gevent.init_gevent()

from google.cloud import translate

client = translate.TranslationServiceClient()

project_id="fluffy-waffle-top"
location = "global"
parent = f"projects/{project_id}/locations/{location}"

def to_spanish(text):
    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",
            "source_language_code": "en-US",
            "target_language_code": "es",
        }
    )
    
    return response.translations[0].translated_text

def to_english(text):
    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",
            "source_language_code": "es",
            "target_language_code": "en-US",
        }
    )
    
    return response.translations[0].translated_text

def is_spanish(text):
    response = client.detect_language(
        parent = parent,
        content= text,
        mime_type="text/plain"
    )
    
    if response.languages[0].language_code == 'es':
        return True
    else:
        return False

def is_english(text):
#    return True
    response = client.detect_language(
        parent = parent,
        content= text,
        mime_type="text/plain"
    )
    
    if response.languages[0].language_code == 'en':
        return True
    else:
        return False

if __name__ == "__main__":
    #poem="Ahora, ¡gracias sea Dios que nos ha emparejado con su hora, y atrapó nuestra juventud, y nos despertó del sueño!"
    poem = "Now, God be thanked who has matched us with his hour, And caught our youth, and wakened us from sleeping!"
    print(to_spanish(poem))
    #print(is_spanish(poem))
    #print(to_english(poem))
    #print(is_english(poem))