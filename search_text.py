import enum
import re

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


class list_of_sheets(enum.Enum):
    GOOD = 0
    BAD = 1
    TEST = 2
    TEST2 = 3


def find_text(document, filename=None, path=None):
    for ind, par in enumerate(document['paragraphs']):
        document['paragraphs'][ind]['paragraphBody']['text'] = re.sub('_+', '', par['paragraphBody']['text'])
        document['paragraphs'][ind]['paragraphHeader']['text'] = re.sub(' +', ' ', par['paragraphHeader']['text'])

    if document['documentType'] == "CONTRACT" or document['documentType'] == "AGREEMENT":
        keys = all_key[document['documentType']]

        index_of_paragraph, found_key = find_currency_header(document['paragraphs'], keys)
        if index_of_paragraph >= 0:
            paragraph = document['paragraphs'][index_of_paragraph]
            return get_good_result(document, paragraph, path, filename, list_of_sheets.GOOD, found_key)

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
                        text_from = " ".join(array_of_text[2].split()[:300])
                except ValueError as ex:
                    print(f"cannot converted str to int")
                    text_from = " ".join(array_of_text[2].split()[:300])
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
                        "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                        "text": remove_bad_symbols(text_from),
                        "length": len(text_from),
                        "offsetHeader": -1,
                        "textHeader": "\n".join(str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                        "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                        "key": found_key
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

    elif document['documentType'] == "POWER_OF_ATTORNEY":
        keys = all_key[document['documentType']]
        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None:
            return paragraph, list_of_sheets.TEST2
        return get_bad_results(document, path, filename, list_of_sheets.TEST)
    else:
        keys = [
            'Приказываю', 'Обязываю',
            'СФЕРЕ ПРИРОДОПОЛЬЗОВАНИЯ', 'рыболовству', 'Природоохран',
            'архитектур',
            'дорожн',
            'интеллектуальной деятельности',
            'программного обеспечения',
            'о взыскании',
            'ПЕРЕЧЕНЬ НАРУШЕНИЙ',
            'транспортировка', 'транспортировки',
            'вагон',
            # 'проверки'
        ]

        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None:
            return paragraph, list_of_sheets.TEST2

        obj = find_let(document, filename=filename, path=path)
        if obj is not None:
            return obj, list_of_sheets.TEST2

        return get_bad_results(document, path, filename, list_of_sheets.TEST)


def find_paragraph_by_keys(document, keys, path, filename):
    index = None
    currency_text = ''
    index_of_paragraph, found_key = find_currency_header(document['paragraphs'], keys)

    if index_of_paragraph >= 0:
        index = index_of_paragraph
        currency_text = document['paragraphs'][index_of_paragraph]['paragraphBody']['text']

    if index_of_paragraph < 0:
        for i, p in enumerate(document['paragraphs']):
            currency_text, found_key = find_currency_text(p, keys)
            if currency_text:
                index = i
                break

    if index is not None:
        while currency_text and len(currency_text.split()) < 300 and index != len(document['paragraphs']) - 1:
            index += 1
            currency_text += document['paragraphs'][index]['paragraphBody']['text']

        return {
            "path": path,
            "name": filename if not path else path.split("\\")[-1],
            "documentType": document['documentType'],
            "offset": document['paragraphs'][index]['paragraphBody']['offset'],
            "text": remove_bad_symbols(currency_text),
            "length": len(currency_text),
            "offsetHeader": document['paragraphs'][index]['paragraphHeader']['offset'],
            "textHeader": document['paragraphs'][index]['paragraphHeader']['text'],
            "lengthHeader": document['paragraphs'][index]['paragraphHeader']['length'],
            "key": found_key
        }

    return None


def find_currency_header(paragraphs, keys):
    for key in keys:
        for index_of_paragraph, paragraph in enumerate(paragraphs):
            header_text_in_low_reg = paragraph['paragraphHeader']['text'].lower()
            if not basic_text_validation(paragraph):
                continue
            for key_from_good_keys in all_good_keys:
                if key_from_good_keys.lower() in header_text_in_low_reg:
                    return index_of_paragraph, key
            if key.lower() in header_text_in_low_reg:
                if 'Статья'.lower() in key.lower() and any(x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if any(x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if re.search("(:)\s*$", paragraph['paragraphBody']['text'].lower()):
                    return -2, -1
                return index_of_paragraph, key

    return -1, -1


def find_currency_text(paragraph, keys):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if not basic_text_validation(paragraph):
        return False, -1
    for key in all_good_keys:
        if key.lower() in basic_text_in_low_reg:
            return paragraph['paragraphBody']['text'], key
    for key in keys:
        if key.lower() in basic_text_in_low_reg:
            if any(x.lower() in basic_text_in_low_reg for x in all_bad_keys):
                return False, -1
            # return ''.join(re.split(f"(?i)({key})", paragraph['paragraphBody']['text'])[1:])
            return paragraph['paragraphBody']['text'], key
    return False, -1


def basic_text_validation(paragraph):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    return len(basic_text_in_low_reg) >= 150 and len(basic_text_in_low_reg.split()) >= 15


def find_let(document, filename=None, document_type=None, path=None):
    key_value = ['о нижеследующем:', 'нижеследующем:', 'о нижеследующем', 'нижеследующем']
    if document_type == 'SUPPLEMENTARY_AGREEMENT':
        key_value.append('в следующей редакции:')
        key_value.append('заключили настоящее Дополнительное соглашение к Договору.')
        key_value.append('редакции:')

    for i, p in enumerate(document['paragraphs']):
        for index, key in enumerate(key_value):
            if key.lower() in p['paragraphBody']['text'].lower() or key.lower() in p['paragraphHeader']['text'].lower():
                text = p['paragraphBody']['text']
                text_header = p['paragraphHeader']['text']
                # text = ''.join(re.split(f"(?i)({x})", p['paragraphBody']['text'])[1:])

                if len(document['paragraphs']) > 1:
                    d = i + 1
                    while len(text.split()) < 300 and d < len(document['paragraphs']):
                        text += document['paragraphs'][d]['paragraphBody']['text']
                        d += 1
                return {
                    "path": path,
                    "name": filename if not path else path.split("\\")[-1],
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": remove_bad_symbols(text),
                    "length": len(text),
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": text_header,
                    "lengthHeader": len(text_header),
                    "key": key
                }
    return None


def remove_signature(text):
    for key in ["Подписи Сторон:"]:
        if key.lower() in text.lower():
            split_text = re.split(f"(?i)({key})", text)
            text = ''.join(split_text[:-2])
    return text


def remove_bad_symbols(text):
    bad_symbols = ['_+', '_x000D_', '\x07', 'FORMTEXT', 'FORMDROPDOWN', ]
    text = remove_signature(text)
    text = re.sub(' +', ' ', text)
    for bad_symbol in bad_symbols:
        text = re.sub(bad_symbol, '', text)

    return ' '.join(text.split()[:300])


def get_bad_results(document, path, filename, sheet):
    return ({
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                "text": "\n".join(x['paragraphBody']['text'] for x in document['paragraphs']),
                "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
                "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                "textHeader": "\n".join(x['paragraphHeader']['text'] for x in document['paragraphs']),
                "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                "key": -1
            }, sheet)


def get_good_result(document, paragraph, path, filename, sheet, key):
    return ({
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": paragraph['paragraphBody']['offset'],
                "text": remove_bad_symbols(paragraph['paragraphBody']['text']),
                "length": paragraph['paragraphBody']['length'],
                "offsetHeader": paragraph['paragraphHeader']['offset'],
                "textHeader": paragraph['paragraphHeader']['text'],
                "lengthHeader": paragraph['paragraphHeader']['length'],
                "key": key
            }, sheet)
