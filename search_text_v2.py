import re

from search_text import list_of_sheets, remove_signature
from nltk.tokenize import WhitespaceTokenizer


def get_text(document, filename: str = "", path: str = ""):
    text: str = ""
    for ind, par in enumerate(document['paragraphs']):
        text += ' ' + document['paragraphs'][ind]['paragraphBody']['text']
    text = clear_text(text)
    text = remove_signature(text)
    text = remove_header(text)
    list_of_tokenize_words: [str] = WhitespaceTokenizer().tokenize(text)
    text = ' '.join(list_of_tokenize_words[:300])

    return {
               "path": path,
               "documentType": document["documentType"],
               "name": filename if not path else path.split("\\")[-1],
               "text": text,
               "length": len(text),
           }, list_of_sheets.GOOD if basic_text_validation(text) else list_of_sheets.BAD


def clear_text(text: str) -> str:
    text = re.sub(r'\s', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'(([а-яА-Яa-zA-Z\d\s\u0000-\u26FF]{1,2}( |\s)){5})', '', text)
    bad_symbols = ['_+', '_x000D_', '\x07', 'FORMTEXT', 'FORMDROPDOWN',
                   '\u0013', '\u0001', '\u0014', '\u0015', '\u0007']
    for bad_symbol in bad_symbols:
        text = re.sub(bad_symbol, '', text)
    return text


def remove_header(text: str) -> str:
    text = re.sub(r'(\d+, г\. [а-яА-Я\-]+, (ул\.| |)( |)[а-яА-Я\-]+(| )(проспект|улица|| ),( |)д\.( |)[\d\-]+)', ' ',
                  text)
    number = re.findall(r'(\d\.\d\.)', text)
    if number:
        return ' '.join(text.split(number[0])[1:])
    return text


def basic_text_validation(text: str) -> bool:
    basic_text_in_low_reg = text.lower()
    return len(basic_text_in_low_reg) >= 150 and len(WhitespaceTokenizer().tokenize(basic_text_in_low_reg)) >= 15
