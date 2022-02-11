import enum
import re


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
        keys = ['Общие ', 'Общие сведения', 'Общие положение', 'Статья']
        if document['documentType'] == "CONTRACT":
            sup_keys = ['предмет договра', 'предмет договора', 'Предмет контракта', 'Предмет догов',
                        'Предмет и общие условия договора']
            keys = sup_keys + keys
        if document['documentType'] == "AGREEMENT":
            keys.insert(0, 'Предмет соглашения')

        for i, p in enumerate(document['paragraphs']):
            if find_currency_header(p, keys):
                result = ({
                              "path": path,
                              "name": filename if not path else path.split("\\")[-1],
                              "documentType": document['documentType'],
                              "offset": p['paragraphBody']['offset'],
                              "text": re.sub(' +', ' ', p['paragraphBody']['text']),
                              "length": p['paragraphBody']['length'],
                              "offsetHeader": p['paragraphHeader']['offset'],
                              "textHeader": p['paragraphHeader']['text'],
                              "lengthHeader": p['paragraphHeader']['length']
                          }, list_of_sheets.GOOD)
                return result

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

        if text_from != "":
            result = ({
                          "path": path,
                          "name": filename if not path else path.split("\\")[-1],
                          "documentType": document['documentType'],
                          "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                          "text": text_from,
                          "length": len(text_from),
                          "offsetHeader": p['paragraphHeader']['offset'],
                          "textHeader": p['paragraphHeader']['text'],
                          "lengthHeader": p['paragraphHeader']['length']
                      }, list_of_sheets.GOOD)
            return result

        obj = find_let(document, filename=filename, path=path)
        if obj != "": return obj, list_of_sheets.GOOD

        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": "\n+++++++++++++\n".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs']),
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n+++++++++++++\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'])
                  }, list_of_sheets.BAD)

    elif document['documentType'] == "SUPPLEMENTARY_AGREEMENT":
        for i, p in enumerate(document['paragraphs']):
            if any(f.lower() in p['paragraphHeader']['text'].lower() for f in
                   ['Статья']) and p['paragraphBody']['length'] > 20:
                result = ({
                              "path": path,
                              "name": filename if not path else path.split("\\")[-1],
                              "documentType": document['documentType'],
                              "offset": p['paragraphBody']['offset'],
                              "text": p['paragraphBody']['text'],
                              "length": p['paragraphBody']['length'],
                              "offsetHeader": p['paragraphHeader']['offset'],
                              "textHeader": p['paragraphHeader']['text'],
                              "lengthHeader": p['paragraphHeader']['length']
                          }, list_of_sheets.GOOD)
                return result

        obj = find_let(document, filename=filename, document_type=document['documentType'], path=path)
        if obj != "": return obj, list_of_sheets.GOOD

        # document['paragraphs'][0]['paragraphHeader']['text']
        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": "".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs']),
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n+++++++++++++\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs']),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'])
                  }, list_of_sheets.GOOD)
    elif document['documentType'] == "POWER_OF_ATTORNEY":
        keys = ['уполномочивает', 'предоставляет', 'назначает']
        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None: return paragraph, list_of_sheets.TEST2
        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": "\n".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs'][:4])[:1000],
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs'][:4]),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs'][:4]),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'][:4])
                  },
                  list_of_sheets.TEST)
    else:
        keys = ['Приказываю', 'Обязываю']
        paragraph = find_paragraph_by_keys(document, keys, path, filename)
        if paragraph is not None: return paragraph, list_of_sheets.TEST2
        result = ({
                      "path": path,
                      "name": filename if not path else path.split("\\")[-1],
                      "documentType": document['documentType'],
                      "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                      "text": "\n".join(
                          str(x['paragraphBody']['text']) for x in document['paragraphs'][:4])[:1000],
                      "length": sum(i['paragraphBody']['length'] for i in document['paragraphs'][:4]),
                      "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
                      "textHeader": "\n".join(
                          str(x['paragraphHeader']['text']) for x in document['paragraphs'][:4]),
                      "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'][:4])
                  },
                  list_of_sheets.TEST)
    # else:
    #     result = ({
    #                   "path": path,
    #                   "name": filename if not path else path.split("\\")[-1],
    #                   "documentType": document['documentType'],
    #                   "offset": document['paragraphs'][0]['paragraphBody']['offset'],
    #                   "text": "\n".join(
    #                       str(x['paragraphBody']['text']) for x in document['paragraphs'][:4])[:1000],
    #                   "length": sum(i['paragraphBody']['length'] for i in document['paragraphs'][:4]),
    #                   "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
    #                   "textHeader": "\n".join(
    #                       str(x['paragraphHeader']['text']) for x in document['paragraphs'][:4]),
    #                   "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'][:4])
    #               },
    #               list_of_sheets.TEST)
    if result == "":
        return None
    return result


def find_paragraph_by_keys(document, keys, path, filename):
    for i, p in enumerate(document['paragraphs']):
        if find_currency_header(p, keys) or find_currency_text(p, keys):
            result = {
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": p['paragraphBody']['offset'],
                "text": re.sub(' +', ' ', p['paragraphBody']['text']),
                "length": p['paragraphBody']['length'],
                "offsetHeader": p['paragraphHeader']['offset'],
                "textHeader": p['paragraphHeader']['text'],
                "lengthHeader": p['paragraphHeader']['length']
            }
            return result
    return None


def find_currency_header(paragraph, keys):
    header_text_in_low_reg = paragraph['paragraphHeader']['text'].lower()
    if not basic_text_validation(paragraph):
        return False
    if re.search("(:)\s*$", paragraph['paragraphBody']['text'].lower()):
        return False
    for key in keys:
        if key.lower() in header_text_in_low_reg:
            if 'Статья'.lower() in key.lower() and any(
                    x.lower() in header_text_in_low_reg for x in
                    ['Термины и определения', 'Термин', 'определения']):
                return False

            return True

    return False


def find_currency_text(paragraph, keys):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if not basic_text_validation(paragraph):
        return False
    for key in keys:
        if key.lower() in basic_text_in_low_reg:
            if any(x.lower() in basic_text_in_low_reg for x in ['Термины и определения', 'Термин', 'определения']):
                return False
            return True
    return False


def basic_text_validation(paragraph):
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if paragraph['paragraphBody']['length'] < 20:
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
            for x in key_value[:4]:
                if x.lower() in p['paragraphBody']['text'].lower():
                    text += p['paragraphBody']['text'].split(x)[1]
                    break
                if x.lower() in p['paragraphHeader']['text'].lower():
                    text += p['paragraphBody']['text']
                    break

            if text == "":
                for x in key_value[5:]:
                    if x.lower() in p['paragraphBody']['text'].lower():
                        text += p['paragraphBody']['text'].split(x)[1]
                        break
                    if x.lower() in p['paragraphHeader']['text'].lower():
                        text += p['paragraphBody']['text']
                        break

            if text == "": continue

            text += "".join(
                str(x['paragraphBody']['text']) for x in document['paragraphs'][i + 1:i + 4])

            textHeader = "\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs'][i:i + 4])

            d = i + 4
            while len(text.split()) < 300 and d < len(document['paragraphs']):
                text += document['paragraphs'][d]['paragraphBody']['text']
                d += 1

            result = {
                "path": path,
                "name": filename if not path else path.split("\\")[-1],
                "documentType": document['documentType'],
                "offset": p['paragraphBody']['offset'],
                "text": text,
                "length": len(text),
                "offsetHeader": p['paragraphHeader']['offset'],
                "textHeader": textHeader,
                "lengthHeader": len(textHeader)
            }
            break
    return result
