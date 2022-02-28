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

        index_of_paragraph = find_currency_header(document['paragraphs'], keys)
        if index_of_paragraph >= 0:
            paragraph = document['paragraphs'][index_of_paragraph]
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
                        "practice": get_practice(path)
                    }, list_of_sheets.GOOD)

        # for i, p in enumerate(document['paragraphs']):
        #     if find_currency_header(p, keys) == -2:
        #         print(1)
        #         break
        #     if find_currency_header(p, keys) >= 0:
        #         print(2)
        #         result = ({
        #                       "path": path,
        #                       "name": filename if not path else path.split("\\")[-1],
        #                       "documentType": document['documentType'],
        #                       "offset": p['paragraphBody']['offset'],
        #                       "text": remove_bad_symbols(p['paragraphBody']['text']),
        #                       "length": p['paragraphBody']['length'],
        #                       "offsetHeader": p['paragraphHeader']['offset'],
        #                       "textHeader": p['paragraphHeader']['text'],
        #                       "lengthHeader": p['paragraphHeader']['length'],
        #                       "practice": get_practice(path)
        #                   }, list_of_sheets.GOOD)
        #         return result

        all_text = "".join(
            str('\n' + x['paragraphHeader']['text'] + '\n' + x['paragraphBody']['text']) for x in
            document['paragraphs'])
        all_text = re.sub(' +', ' ', all_text)
        text_from = ""
        # f"(?i)({key}([\w\u0430-\u044f]+|[ ]{1,}|))
        for key in keys:
            if key.lower() in all_text.lower():
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
                    # print("\nEnd = ", end_text)
                    text_from = re.split(f"\s({end_text})[. ]", array_of_text[2])[0]
                    break
                break

        if text_from != "":
            result = ({
                          "path": path,
                          "name": filename if not path else path.split("\\")[-1],
                          "documentType": document['documentType'],
                          "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                          "text": remove_bad_symbols(text_from),
                          "length": len(text_from),
                          "offsetHeader": -1,
                          "textHeader": "\n".join(str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                          "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                          "practice": get_practice(path)
                      }, list_of_sheets.GOOD)
            return result

        obj = find_let(document, filename=filename, path=path)
        if obj != "": return obj, list_of_sheets.GOOD

        result = get_results(document, path, filename, list_of_sheets.BAD)

    elif document['documentType'] == "SUPPLEMENTARY_AGREEMENT":
        for i, p in enumerate(document['paragraphs']):
            if any(f.lower() in p['paragraphHeader']['text'].lower() for f in
                   ['Статья']) and p['paragraphBody']['length'] > 20:
                result = ({
                              "path": path,
                              "name": filename if not path else path.split("\\")[-1],
                              "documentType": document['documentType'],
                              "offset": p['paragraphBody']['offset'],
                              "text": remove_bad_symbols(p['paragraphBody']['text']),
                              "length": p['paragraphBody']['length'],
                              "offsetHeader": p['paragraphHeader']['offset'],
                              "textHeader": p['paragraphHeader']['text'],
                              "lengthHeader": p['paragraphHeader']['length'],
                              "practice": get_practice(path)
                          }, list_of_sheets.GOOD)
                return result

        obj = find_let(document, filename=filename, document_type=document['documentType'], path=path)
        if obj != "": return obj, list_of_sheets.GOOD

        result = get_results(document, path, filename, list_of_sheets.GOOD)

    elif document['documentType'] == "POWER_OF_ATTORNEY":
        keys = all_key[document['documentType']]
        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None: return paragraph, list_of_sheets.TEST2
        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": remove_bad_symbols("\n".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs'][:4])[:1000]),
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs'][:4]),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs'][:4]),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'][:4]),
                      "practice": get_practice(path)
                  },
                  list_of_sheets.TEST)
    else:
        keys = [
            'Приказываю', 'Обязываю',
            'СФЕРЕ ПРИРОДОПОЛЬЗОВАНИЯ', 'рыболовству', 'Природоохран',
            'архитектур',
            'дорожн',
            'интеллектуальной деятельности',
            'программного обеспечения'
        ]

        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None: return paragraph, list_of_sheets.TEST2

        obj = find_let(document, filename=filename, path=path)
        if obj != "": return obj, list_of_sheets.TEST2

        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": remove_bad_symbols("\n".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs'][:4])[:2000]),
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs'][:4]),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs'][:4]),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'][:4]),
                      "practice": get_practice(path)
                  },
                  list_of_sheets.TEST)
    if result == "":
        return None
    return result


def find_paragraph_by_keys(document, keys, path, filename):
    index = None
    currency_text = ''
    index_of_paragraph = find_currency_header(document['paragraphs'], keys)

    if index_of_paragraph >= 0:
        index = index_of_paragraph
        currency_text = document['paragraphs'][index_of_paragraph]['paragraphBody']['text']

    if index_of_paragraph < 0:
        for i, p in enumerate(document['paragraphs']):
            currency_text = find_currency_text(p, keys)
            if currency_text:
                index = i
                break

    if index is not None:
        while currency_text and len(currency_text) < 300 and index != len(document['paragraphs']) - 1:
            index += 1
            currency_text += document['paragraphs'][index]['paragraphBody']['text']

        result = {
            "path": path,
            "name": filename if not path else path.split("\\")[-1],
            "documentType": document['documentType'],
            "offset": document['paragraphs'][index]['paragraphBody']['offset'],
            "text": remove_bad_symbols(currency_text),
            "length": len(currency_text),
            "offsetHeader": document['paragraphs'][index]['paragraphHeader']['offset'],
            "textHeader": document['paragraphs'][index]['paragraphHeader']['text'],
            "lengthHeader": document['paragraphs'][index]['paragraphHeader']['length'],
            "practice": get_practice(path)
        }
        return result
    return None


def find_currency_header(paragraphs, keys):
    for key in keys:
        for index_of_paragraph, paragraph in enumerate(paragraphs):
            header_text_in_low_reg = paragraph['paragraphHeader']['text'].lower()
            if not basic_text_validation(paragraph):
                continue
            for key_from_good_keys in all_good_keys:
                if key_from_good_keys.lower() in header_text_in_low_reg:
                    return index_of_paragraph
            if key.lower() in header_text_in_low_reg:
                if 'Статья'.lower() in key.lower() and any(
                        x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if any(x.lower() in header_text_in_low_reg for x in all_bad_keys):
                    continue
                if re.search("(:)\s*$", paragraph['paragraphBody']['text'].lower()):
                    # print(key)
                    # print(paragraph['paragraphBody']['text'])
                    return -2
                return index_of_paragraph

    return -1


def find_currency_text(paragraph, keys):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if not basic_text_validation(paragraph):
        return False
    for key in keys:
        if key.lower() in basic_text_in_low_reg:
            if any(x.lower() in basic_text_in_low_reg for x in all_bad_keys):
                return False
            return ''.join(re.split(f"(?i)({key})", paragraph['paragraphBody']['text'])[1:])
    return False


def basic_text_validation(paragraph):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if len(basic_text_in_low_reg) < 150:
        return False
    if len(basic_text_in_low_reg.split()) < 15:
        return False
    return True


def find_let(document, filename=None, document_type=None, path=None):
    key_value = ['о нижеследующем:', 'нижеследующем:', 'о нижеследующем', 'нижеследующем']
    if document_type == 'SUPPLEMENTARY_AGREEMENT':
        key_value.append('в следующей редакции:')
        key_value.append('заключили настоящее Дополнительное соглашение к Договору.')
        key_value.append('редакции:')

    result = ""
    for i, p in enumerate(document['paragraphs']):
        if any(f.lower() in p['paragraphBody']['text'].lower() or f.lower() in
               p['paragraphHeader']['text'].lower() for f in
               key_value[:4]) or any(f.lower() in p['paragraphBody']['text'].lower() or f.lower() in
                                     p['paragraphHeader']['text'].lower() for f in
                                     key_value[5:]):
            text = ""
            for ind, x in enumerate(key_value):
                if ind == 4 and text != "":
                    break
                if x.lower() in p['paragraphBody']['text'].lower():
                    # text += p['paragraphBody']['text'].split(x)[1]
                    text += ''.join(re.split(f"(?i)({x})", p['paragraphBody']['text'])[1:])
                    break
                if x.lower() in p['paragraphHeader']['text'].lower():
                    text += p['paragraphBody']['text']
                    break

            # if text == "":
            #     for x in key_value[5:]:
            #         if x.lower() in p['paragraphBody']['text'].lower():
            #             text += ''.join(re.split(f"(?i)({x})", p['paragraphBody']['text'])[1:])
            #             break
            #         if x.lower() in p['paragraphHeader']['text'].lower():
            #             text += p['paragraphBody']['text']
            #             break

            if text == "": continue

            text += "".join(
                str(x['paragraphBody']['text']) for x in document['paragraphs'][i + 1:i + 4])

            text_header = "\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs'][i:i + 4])

            d = i + 4
            while len(text) < 300 and d < len(document['paragraphs']):
                text += document['paragraphs'][d]['paragraphBody']['text']
                d += 1

            result = {
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": p['paragraphBody']['offset'],
                "text": remove_bad_symbols(text),
                "length": len(text),
                "offsetHeader": p['paragraphHeader']['offset'],
                "textHeader": text_header,
                "lengthHeader": len(text_header),
                "practice": get_practice(path)
            }
            break
    return result


def remove_signature(text):
    for key in ["Подписи Сторон:"]:
        if key.lower() in text.lower():
            split_text = text.split(key)
            text = ''.join(split_text[:-1])
    return text


def remove_bad_symbols(text, sheet=None):
    text = remove_signature(text)
    text = re.sub(' +', ' ', text)
    text = re.sub('_+', '', text)
    text = re.sub('_x000D_', '', text)
    return text[:300]
    # return text


def get_practice(path):
    if path:
        if len(path.split("\\")) == 4:
            return ''.join(path.split("\\")[2:-1]).capitalize()
        else:
            return ''.join(path.split("\\")[2:-2]).capitalize()
    else:
        return 0


def get_results(document, path, filename, sheet):
    return ({
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                "text": remove_bad_symbols("\n".join(
                    str(x['paragraphBody']['text']) for x in document['paragraphs'])),
                "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
                "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                "textHeader": "\n+++++++++++++\n".join(
                    str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs']),
                "practice": get_practice(path)
            }, sheet)
