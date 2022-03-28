import enum
import json
import re
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
import tensorflow as tf
from nltk.tokenize import WhitespaceTokenizer
from fuzzywuzzy import fuzz

all_key = {
    "CONTRACT": [
        'предмет договра', 'предмет договора', 'Предмет контракта',
        'Предмет догов', 'Предмет и общие условия договора',
        'Общие ', 'Общие сведения', 'Общие положение', 'Статья'
    ],
    "AGREEMENT": [
        'Предмет соглашения', 'Общие ', 'Общие сведения', 'Общие положение', 'определил:', 'Статья'
    ],
    "SUPPLEMENTARY_AGREEMENT": [],
    "POWER_OF_ATTORNEY": ['уполномочивает', 'предоставляет', 'назначает', 'доверенность']
}

all_bad_keys = ['Термины и определения', 'Термин', 'определения', 'Содержание']

all_good_keys = ['Цели и задачи']

labels = ['Практика коммерческой логистики',
          'Практика недропользования и экологии',
          'Практика поддержки региональных, розничных продаж и клиентского сервиса',
          'Практика правового сопровождения закупок МТР и услуг общего профиля',
          'Практика правового сопровождения земельных отношений и сделок с недвижимым имуществом',
          'Практика правового сопровождения операционной деятельности БРД',
          'Практика правового сопровождения переработки и инфраструктуры',
          'Практика правовой поддержки брендов',
          'Практика правовой поддержки использования и коммерциализации ИС',
          'Практика правовой поддержки создания и приобретения ИС',
          'Практика промышленной безопасности и охраны труда',
          'Практика финансового и конкурентного права',
          'Практика экспорта, оптовых продаж и сбыта бизнес-единиц']

model = None
tokenizer = None
path_to_model: str = "./doc-classification/"
model_checkpoint: str = "sberbank-ai/ruRoberta-large"
percentage_of_inaccurate_search: int = 90


def get_key_from_json() -> list:
    keys = []
    json_file_with_key = open('keys_from_documents.json', encoding="utf8")
    data = json.load(json_file_with_key)

    for item in data:
        item = str(item).replace('/', '|').replace('\n', '')
        keys += re.split(r",|;", item)

    for index, item in enumerate(keys):
        if re.search(r'(\S+\|\S+)', item):
            words = re.findall(r'\S+\|\S+', item)
            for word in words:
                key = keys[index]
                word_split = word.split('|')
                keys[index] = keys[index].replace(word, f"{word_split[0]}")
                for sub_word in word_split[1:]:
                    keys.append(key.replace(word, f"{sub_word}"))
    json_file_with_key.close()
    return list(filter(None, keys))


key_from_json = get_key_from_json()


class list_of_sheets(enum.Enum):
    GOOD = 0
    BAD = 1
    BAD2 = 2
    GOOD2 = 3


def wrapper(documents) -> [] or str:
    """
    documents: Массив из документов, который лежит в свойстве documents в json ответе от парсера

    Returns: Массив из практик отсортированных по наибольшему проценту
    """
    if documents is None or len(documents) == 0:
        return 'Empty document'

    global model
    global tokenizer

    for document in documents:
        json_from_text, sheet = find_text(document, path='There\\is\\nothing\\here')

        if json_from_text is None or sheet == list_of_sheets.BAD or json_from_text['text'] == '':
            continue

        if tokenizer is None and model is None:
            model = TFAutoModelForSequenceClassification.from_pretrained(
                str(path_to_model), num_labels=len(labels), from_pt=False
            )
            tokenizer = AutoTokenizer.from_pretrained(str(model_checkpoint))

        result_from_tokenizer = tokenizer(json_from_text['text'], truncation=True, max_length=512)
        predictions = model.predict([result_from_tokenizer['input_ids']])['logits']
        predictions = tf.nn.softmax(predictions, name=None)[0].numpy()
        result = []
        for index, item in enumerate(predictions):
            result.append({
                'id': index,
                'item': labels[index],
                'count': item
            })
        return sorted(result, key=lambda x: x['count'], reverse=True)

    return 'Bad result'


def find_text(document, filename: str = "", path: str = ""):
    for ind, par in enumerate(document['paragraphs']):
        document['paragraphs'][ind]['paragraphBody']['text'] = re.sub('_+', '', par['paragraphBody']['text'])
        document['paragraphs'][ind]['paragraphHeader']['text'] = re.sub(' +', ' ', par['paragraphHeader']['text'])

    if document['documentType'] == "CONTRACT" or document['documentType'] == "AGREEMENT":
        keys = all_key[document['documentType']]

        # index_of_paragraph, found_key, percentage = find_currency_header(document['paragraphs'], keys)
        # if index_of_paragraph >= 0:
        #     paragraph = document['paragraphs'][index_of_paragraph]
        #     return get_good_result(document, paragraph, path, filename, list_of_sheets.GOOD, found_key, percentage)

        paragraph = find_paragraph_by_keys(document, all_key[document['documentType']] + key_from_json, path, filename)
        if paragraph is not None:
            return paragraph, list_of_sheets.GOOD

        all_text = "".join('\n' + x['paragraphHeader']['text'] + '\n' + x['paragraphBody']['text'] for x in
                           document['paragraphs'])
        all_text = re.sub(' +', ' ', all_text)
        text_from = ""
        found_key = -1
        # f"(?i)({key}([\w\u0430-\u044f]+|[ ]{1,}|))
        for key in keys:
            if key.lower() in all_text.lower():
                found_key = key
                array_of_text = re.split(f"(?i)({key})", all_text)
                end_text = 0
                try:
                    last_symbol = re.search("\s\d[ .]\d?[\s|\u00A0|.\s]*$", array_of_text[0])
                    if last_symbol:
                        end_text = int(last_symbol.group().replace(" ", "").split(".")[0])
                    else:
                        text_from = " ".join(WhitespaceTokenizer().tokenize(array_of_text[2])[:300])
                except ValueError as ex:
                    print(f"cannot converted str to int")
                    text_from = " ".join(WhitespaceTokenizer().tokenize(array_of_text[2])[:300])
                    break

                if end_text:
                    end_text += 1
                    text_from = re.split(f"\s({end_text})[. ]", array_of_text[2])[0]
                break

        if text_from != "":
            return ({
                        "path": path,
                        "name": filename if not path else path.split("\\")[-1],
                        "documentType": document['documentType'],
                        "text": remove_bad_symbols(text_from),
                        "length": len(text_from),
                        "textHeader": "\n".join(str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                        "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                        "key": found_key,
                        "percentage": -2
                    }, list_of_sheets.GOOD)

        obj = find_let(document, filename=filename, path=path)
        if obj is not None:
            return obj, list_of_sheets.GOOD

        return get_bad_results(document, path, filename, list_of_sheets.BAD)

    elif document['documentType'] == "SUPPLEMENTARY_AGREEMENT":
        for i, paragraph in enumerate(document['paragraphs']):
            if paragraph['paragraphBody']['length'] > 20:
                for key in ['Статья']:
                    if key.lower() in paragraph['paragraphHeader']['text'].lower():
                        return get_good_result(document, paragraph, path, filename, list_of_sheets.GOOD, key)

        obj = find_let(document, filename=filename, document_type=document['documentType'], path=path)
        if obj is not None:
            return obj, list_of_sheets.GOOD

        return get_bad_results(document, path, filename, list_of_sheets.GOOD)
    else:
        if document['documentType'] == "POWER_OF_ATTORNEY":
            paragraph = find_paragraph_by_keys(document, all_key[document['documentType']], path, filename)
            if paragraph is not None:
                return paragraph, list_of_sheets.GOOD2

        keys: [str] = [
            'Приказываю', 'Обязываю',
            'СФЕРЕ ПРИРОДОПОЛЬЗОВАНИЯ', 'рыболовству', 'Природоохран',
            'архитектур',
            'дорожн',
            'интеллектуальной деятельности',
            'программного обеспечения',
            'о взыскании',
            'ПЕРЕЧЕНЬ НАРУШЕНИЙ',
            'Перечень услуг',
            'Недропользование',
            'План развития',
            'транспортировка', 'транспортировки',
            'вагон',
            'проверки',
            'Авария',
            'Аукцион',
            'Выброс',
            'Разлив',
            'отход',
        ]
        keys += key_from_json
        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None:
            return paragraph, list_of_sheets.GOOD2

        obj = find_let(document, filename=filename, path=path)
        if obj is not None:
            return obj, list_of_sheets.GOOD2

        return get_bad_results(document, path, filename, list_of_sheets.BAD2)


def find_paragraph_by_keys(document, keys: [str], path: str, filename: str):
    index = None
    currency_text: str = ''
    index_of_paragraph, found_key, percentage = find_currency_header(document['paragraphs'], keys)

    if index_of_paragraph >= 0:
        index = index_of_paragraph
        currency_text = document['paragraphs'][index_of_paragraph]['paragraphBody']['text']

    if index_of_paragraph < 0:
        for i, p in enumerate(document['paragraphs']):
            currency_text, found_key, percentage = find_currency_text(p, keys)
            if currency_text:
                index = i
                break

    if index is not None:
        while currency_text and len(WhitespaceTokenizer().tokenize(currency_text)) < 300 and index != len(
                document['paragraphs']) - 1:
            index += 1
            currency_text += document['paragraphs'][index]['paragraphBody']['text']

        return {
            "path": path,
            "name": filename if not path else path.split("\\")[-1],
            "documentType": document['documentType'],
            "text": remove_bad_symbols(currency_text),
            "length": len(currency_text),
            "textHeader": document['paragraphs'][index]['paragraphHeader']['text'],
            "lengthHeader": document['paragraphs'][index]['paragraphHeader']['length'],
            "key": found_key,
            "percentage": percentage
        }

    return None


def find_currency_header(paragraphs, keys: [str]) -> (int, int, int) or (int, str, int):
    for key in keys:
        for index_of_paragraph, paragraph in enumerate(paragraphs):
            header_text_in_low_reg = paragraph['paragraphHeader']['text'].lower()
            header_text_in_low_reg = str(header_text_in_low_reg).replace(',', '')
            if not basic_text_validation(paragraph):
                continue
            for key_from_good_keys in all_good_keys:
                if key_from_good_keys.lower() in header_text_in_low_reg:
                    return index_of_paragraph, key, 100
            is_it_found, percentage = is_high_percentage(key, header_text_in_low_reg)
            if is_it_found:
                if 'Статья'.lower() in key.lower() and any(x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if any(x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if re.search("(:)\s*$", paragraph['paragraphBody']['text'].lower()):
                    return -2, -1, percentage
                return index_of_paragraph, key, percentage

    return -1, -1, 0


def find_currency_text(paragraph, keys: [str]):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    basic_text_in_low_reg = basic_text_in_low_reg.replace(',', '')
    if not basic_text_validation(paragraph):
        return False, -1, 0
    for key in all_good_keys:
        if key.lower() in basic_text_in_low_reg:
            return paragraph['paragraphBody']['text'], key, 100
    for key in keys:
        is_it_found, percentage = is_high_percentage(key, basic_text_in_low_reg)
        if is_it_found:
            if any(x.lower() in basic_text_in_low_reg for x in all_bad_keys):
                return False, -1, percentage
            # return ''.join(re.split(f"(?i)({key})", paragraph['paragraphBody']['text'])[1:])
            return paragraph['paragraphBody']['text'], key, percentage
    return False, -1, 0


def basic_text_validation(paragraph) -> bool:
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    return len(basic_text_in_low_reg) >= 150 and len(WhitespaceTokenizer().tokenize(basic_text_in_low_reg)) >= 15


def find_let(document, filename: str = "", document_type: str = "", path: str = ""):
    key_value = ['о нижеследующем:', 'нижеследующем:', 'о нижеследующем', 'нижеследующем']
    if document_type == 'SUPPLEMENTARY_AGREEMENT':
        key_value.append('в следующей редакции:')
        key_value.append('заключили настоящее Дополнительное соглашение к Договору.')
        key_value.append('редакции:')

    for i, p in enumerate(document['paragraphs']):
        for index, key in enumerate(key_value):
            is_it_found_in_text, percentage_of_text = is_high_percentage(key, p['paragraphBody']['text'])
            is_it_found_in_header, percentage_of_header = is_high_percentage(key, p['paragraphHeader']['text'])
            if is_it_found_in_text or is_it_found_in_header:
                text = p['paragraphBody']['text']
                text_header = p['paragraphHeader']['text']
                # list_of_tokenize_words: [str] = WhitespaceTokenizer().tokenize(text)
                # text = ''.join(re.split(f"(?i)({x})", p['paragraphBody']['text'])[1:])

                if len(document['paragraphs']) > 1:
                    d = i + 1
                    while len(WhitespaceTokenizer().tokenize(text)) < 300 and d < len(document['paragraphs']):
                        text += document['paragraphs'][d]['paragraphBody']['text']
                        d += 1
                return {
                    "path": path,
                    "name": filename if not path else path.split("\\")[-1],
                    "documentType": document['documentType'],
                    "text": remove_bad_symbols(text),
                    "length": len(text),
                    "textHeader": text_header,
                    "lengthHeader": len(text_header),
                    "key": key,
                    "percentage": percentage_of_text if is_it_found_in_text else percentage_of_header
                }
    return None


def remove_signature(text: str) -> str:
    for key in ["Подписи Сторон:"]:
        if key.lower() in text.lower():
            split_text = re.split(f"(?i)({key})", text)
            text = ''.join(split_text[:-2])
    return text


def remove_bad_symbols(text: str) -> str:
    bad_symbols = ['_+', '_x000D_', '\x07', 'FORMTEXT', 'FORMDROPDOWN',
                   '\u0013', '\u0001', '\u0014', '\u0015', '\u0007']
    text = remove_signature(text)
    text = re.sub(' +', ' ', text)
    for bad_symbol in bad_symbols:
        text = re.sub(bad_symbol, '', text)
    list_of_tokenize_words: [str] = WhitespaceTokenizer().tokenize(text)
    return ' '.join(list_of_tokenize_words[:300])


def get_bad_results(document, path: str,
                    filename: str,
                    sheet: list_of_sheets,
                    percentage: int = -2):
    return ({
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "text": remove_bad_symbols("\n".join(x['paragraphBody']['text'] for x in document['paragraphs'])),
                "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
                "textHeader": "\n+++++++++++++\n".join(x['paragraphHeader']['text'] for x in document['paragraphs']),
                "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                "key": -1,
                "percentage": percentage
            }, sheet)


def get_good_result(document, paragraph,
                    path: str, filename: str,
                    sheet: list_of_sheets,
                    key: str,
                    percentage: int = -2):
    return ({
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "text": remove_bad_symbols(paragraph['paragraphBody']['text']),
                "length": paragraph['paragraphBody']['length'],
                "textHeader": paragraph['paragraphHeader']['text'],
                "lengthHeader": paragraph['paragraphHeader']['length'],
                "key": key,
                "percentage": percentage
            }, sheet)


def is_high_percentage(key: str, text: str) -> (bool, int):
    if len(key) > len(text):
        return False, 0
    percentage = fuzz.partial_ratio(key.lower(), text.lower())
    if percentage > percentage_of_inaccurate_search:
        # print(key, percentage, text)
        return True, percentage
    return False, percentage
