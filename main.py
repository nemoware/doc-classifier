import base64
import json
import re

import requests
import streamlit as st
import pandas as pd


# @st.cache(allow_output_mutation=True)
def get_json_from_parser(doc, filename):
    result = ""
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        # file = open(doc, 'rb')
        encoded_string = base64.b64encode(doc)
        encoded_string = str(encoded_string)[2:-1]
    except Exception as e:
        print(f"\nОшибка в файле {doc}")
        print(f"при конвертации в base64, исключение = {e}")
        print("=" * 200)
        return

    response = requests.post(
        "http://localhost:8083/document-parser",
        data=json.dumps({
            "base64Content": encoded_string,
            "documentFileType": filename.split(".")[-1].upper()
        }),
        headers=headers
    )

    try:
        result = response.json()['documents']
    except Exception as e:
        print(f"\nОшибка в файле {doc}")
        print(f"Ответ от парсера {response.json()}")
        print(f"Исключение = {e}")
        print("=" * 200)
        return

    return result


# @st.cache(allow_output_mutation=True)
def find_let(document, filename, documentType=None):
    key_value = ['о нижеследующем:', 'нижеследующем:', 'о нижеследующем', 'нижеследующем']
    if documentType == 'SUPPLEMENTARY_AGREEMENT':
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
                str(x['paragraphBody']['text']) if re.match("^ *\d?[.]", str(
                    x['paragraphBody']['text'])) or re.match("^ *\d?[.]", str(
                    x['paragraphHeader']['text'])) else '' for x in
                document['paragraphs'][i:i + 4])

            textHeader = p['paragraphHeader']['text'] + "\n".join(
                str(x['paragraphHeader']['text']) if re.match("^ *\d?[.] ", str(
                    x['paragraphBody']['text'])) or re.match("^ *\d?[.] ", str(
                    x['paragraphHeader']['text'])) else '' for x in document['paragraphs'])
            result = {
                "name": filename,
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


# @st.cache(allow_output_mutation=True)
def find_text(document, filename):
    # print(document)
    result = ""
    if document['documentType'] == "CONTRACT":
        keys = ['предмет договра', 'предмет договора', 'предмет контракта', 'Общие состояние',
                'Общие положение', 'Статья 1']
        flag = False
        for i, p in enumerate(document['paragraphs']):
            if any(z.lower() in re.sub(' +', ' ', p['paragraphHeader']['text'].lower()) for z in
                   keys) and p['paragraphBody']['length'] > 20:
                result = {
                    "name": filename,
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": p['paragraphBody']['text'],
                    "length": p['paragraphBody']['length'],
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": p['paragraphHeader']['text'],
                    "lengthHeader": p['paragraphHeader']['length']
                }
                flag = True
                break
        if flag: return result

        for i, p in enumerate(document['paragraphs']):
            if any(z.lower() in p['paragraphBody']['text'].lower() for z in [
                'предмет договра', 'предмет договора', 'предмет контракта', 'Общие состояние',
                'Общие положение', 'Статья 1']) and p['paragraphBody']['length'] > 20:
                text = ""

                for key in keys:
                    if key.lower() in re.sub(' +', ' ', p['paragraphBody']['text']).lower():
                        array_of_text = re.split(f"(?i)({key})",
                                                 re.sub(' +', ' ', p['paragraphBody']['text']))
                        end_text = 0
                        try:
                            last_symbol = re.search("\s\d[ .]\d?[\s|\u00A0|.]*$", array_of_text[0])
                            if last_symbol:
                                end_text = int(last_symbol.group().replace(" ", "").split(".")[0])
                        except ValueError as ex:
                            print(f"cannot converted str to int")
                            text = array_of_text[2]
                            break

                        if end_text:
                            end_text += 1
                            print("\nEnd = ", end_text)
                            text = re.split(f"\s({end_text})[. ]", array_of_text[2])[0]
                            break

                result = {
                    "name": filename,
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": text,
                    "length": len(text),
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": p['paragraphHeader']['text'],
                    "lengthHeader": p['paragraphHeader']['length']
                }
                flag = True
                break
        if flag: return result
        obj = find_let(document, filename)
        if obj != "":
            result = obj
            flag = True

        if flag: return result
        result = {
            "fail": True,
            "name": filename,
            "documentType": document['documentType'],
            "offset": document['paragraphs'][0]['paragraphBody']['offset'],
            "text": "\n+++++++++++++\n".join(
                str(x['paragraphBody']['text']) for x in document['paragraphs']),
            "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
            "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
            "textHeader": "\n+++++++++++++\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs']),
            "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'])
        }
    elif document['documentType'] == "SUPPLEMENTARY_AGREEMENT":
        flag = False
        for i, p in enumerate(document['paragraphs']):
            if any(f.lower() in p['paragraphHeader']['text'].lower() for f in
                   ['Статья 1']) and p['paragraphBody'][
                'length'] > 20:
                result = {
                    "name": filename,
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": p['paragraphBody']['text'],
                    "length": p['paragraphBody']['length'],
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": p['paragraphHeader']['text'],
                    "lengthHeader": p['paragraphHeader']['length']
                }
                flag = True
                break
        if flag: return result
        obj = find_let(document, filename, document['documentType'])
        if obj != "":
            result = obj
            flag = True

        if flag: return result
        # document['paragraphs'][0]['paragraphHeader']['text']
        result = {
            "name": filename,
            "documentType": document['documentType'],
            "offset": document['paragraphs'][0]['paragraphBody']['offset'],
            "text": "".join(
                str(x['paragraphBody']['text']) for x in document['paragraphs']),
            "length": sum(i['paragraphBody']['length'] for i in document['paragraphs']),
            "offsetHeader": document['paragraphs'][0]['paragraphHeader']['offset'],
            "textHeader": "\n+++++++++++++\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs']),
            "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'])
        }
    elif document['documentType'] == "AGREEMENT":
        flag = False
        for i, p in enumerate(document['paragraphs']):
            if any(f.lower() in re.sub(' +', ' ', p['paragraphHeader']['text'].lower()) for f in
                   ['Предмет соглашения', 'Общие состоян', 'Общие положение', 'Статья 1']) and \
                    p['paragraphBody'][
                        'length'] > 20:
                result = {
                    "name": filename,
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": p['paragraphBody']['text'],
                    "length": p['paragraphBody']['length'],
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": p['paragraphHeader']['text'],
                    "lengthHeader": p['paragraphHeader']['length']
                }
                flag = True
                break
        if flag: return result

        obj = find_let(document, filename)
        if obj != "":
            result = obj
            flag = True

        if flag: return result

        arr_of_paragraphs = document['paragraphs']
        result = {
            "fail": True,
            "name": filename,
            "documentType": document['documentType'],
            "offset": arr_of_paragraphs[0]['paragraphBody']['offset'],
            "text": "\n+++++++++++++\n".join(
                str(x['paragraphBody']['text']) for x in document['paragraphs']),
            "length": sum(i['paragraphBody']['length'] for i in arr_of_paragraphs),
            "offsetHeader": arr_of_paragraphs[0]['paragraphHeader']['offset'],
            "textHeader": "\n+++++++++++++\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs']),
            "lengthHeader": sum(i['paragraphHeader']['length'] for i in document['paragraphs'])
        }
    if result != "":
        return None
    return result


def get_table_from_excel():
    df = pd.read_excel(FOLDER_DOWNLOAD_LOCATION + '1.xlsx', sheet_name='Центры. Практики')
    return None

st.set_page_config(layout="wide")

# state = st.session_state[0]

col1, col2 = st.columns(2)
col2.header("Справочник")
col1.header("Результат")

# b1, b2 = st.columns(2)

uploader = col1.file_uploader("Выберите файл", ["doc", "docx"])

placeholder = col1
start_btn = col1.button("Получить")
clean_btn = col1.button("Очистить")

if start_btn and uploader:
    from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
    if from_parser != "" and from_parser is not None:
        text_ = find_text(from_parser[0], uploader.name)
        if text_ != "":
            placeholder.write(text_['text'])
        else:
            placeholder.write("Ошибка при поиске в доке")
    else:
        placeholder.write("Ошибка при парсинге дока")

if clean_btn:
    placeholder.empty()
