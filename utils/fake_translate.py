# use the google cloud account to translate between english and spanish
# CB 8/2023

from google.cloud import translate

client = translate.TranslationServiceClient()

project_id="fluffy-waffle-top"
location = "global"
parent = f"projects/{project_id}/locations/{location}"


def to_spanish(text):
    print(text) 
    return text

def is_english(text):
    print(text) 
    return True


if __name__ == "__main__":
    #poem="Ahora, ¡gracias sea Dios que nos ha emparejado con su hora, y atrapó nuestra juventud, y nos despertó del sueño!"
    poem = "Now, God be thanked who has matched us with his hour, And caught our youth, and wakened us from sleeping!"
    print(to_spanish(poem))
    #print(is_spanish(poem))
    #print(to_english(poem))
    #print(is_english(poem))