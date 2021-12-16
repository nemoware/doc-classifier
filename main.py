import base64
import json
import os
import platform
import random
import re
import signal
import subprocess
import sys
import time
from json import JSONDecodeError
import seaborn as sns
import matplotlib.pyplot as plt

import requests
import streamlit as st
import pandas as pd

parser_version = '1.6.4'
java_subprocess = None


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


@st.cache(allow_output_mutation=True)
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


@st.cache(allow_output_mutation=True)
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


@st.cache(allow_output_mutation=True)
def get_table_from_excel():
    result = []
    filename = ''
    for root, dirnames, filenames in os.walk(os.path.abspath(os.curdir), topdown=True):
        for file in filenames:
            if 'ЛОД' in file:
                filename = file
    df = pd.read_excel(filename, sheet_name='Центры. Практики', header=1)
    for row in df.values:
        result.append({
            'item': row[1],
            'count': random.random()
        })
    return result


def start_java_server():
    print("Запуск сервера")
    s = [
        "java",
        "-jar",
        f"document-parser-{parser_version}.jar",
        "--server.port=8083"
    ]
    global java_subprocess
    java_subprocess = subprocess.Popen(s, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                                       stdout=subprocess.PIPE, encoding="utf-8")
    i = 1
    while i < 40:
        time.sleep(0.1)
        output_log_spring = java_subprocess.stdout.readline()
        sys.stdout.write("\rПроверка соединения #%i" % i)
        sys.stdout.flush()
        i += 1
        if output_log_spring.find("Started DocumentParserService") != -1:
            print("\nГотово")
            java_subprocess.stdout.close()
            break
    if i < 40:
        print("Ошибка при запуске сервера")
    return i < 40


def server_activity_check():
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        response = requests.get(
            "http://localhost:8083/status",
            headers=headers
        )
        response_json = response.json()
        status = response_json['status']
        if status == 'ok':
            print(status)
            return True
    except JSONDecodeError:
        print('Decoding JSON has failed')
        return False
    except requests.exceptions.RequestException:
        print("Ошибка при запросе на сервер")
        return False

    return False


def server_turn_off():
    global java_subprocess
    # Смерть java процессу!
    if platform.system() == 'Windows':
        subprocess.run("TASKKILL /F /PID {pid} /T".format(pid=java_subprocess.pid))
    elif platform.system() == 'Linux':
        os.kill(java_subprocess.pid, signal.SIGTERM)
    else:
        print('Не известная платформа, убейте в ручную процесс java')


def predicate_result(text):
    return False


for key in ['result_btn', 'start_btn', 'uploader']:
    if key not in st.session_state:
        st.session_state[key] = False

for key in ['main_text', 'len', 'text_header', 'data_frame']:
    if key not in st.session_state:
        st.session_state[key] = ""

st.set_page_config(layout="wide")

col1, col2 = st.columns([1, 3])

uploader = col1.file_uploader("Выберите файл", ["doc", "docx"])

container_btn = col1.container()
container = col2.container()
container_text = col2.container()

start_btn = container_btn.button("Текст")
result_btn = container_btn.button("Результат")
clean_btn = container_btn.button("Очистить")
turn_on = container_btn.button("Включить")

if clean_btn:
    col1.empty()
    st.session_state.main_text = ""
    st.session_state.data_frame = ""

if start_btn and uploader:
    from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
    if from_parser != "" and from_parser is not None:
        text_ = find_text(from_parser[0], uploader.name)
        if text_ != "":
            st.session_state.text_header = text_['textHeader']
            st.session_state.main_text = text_['text']
            st.session_state.len = text_['length']

            response = predicate_result(text_['text'])
        else:
            col1.write("Ошибка при поиске в доке")
    else:
        col1.write("Ошибка при парсинге дока")

if turn_on:
    if server_activity_check():
        container_btn.write("Сервер запущен")
    elif start_java_server():
        container_btn.write("Сервер запущен")
    else:
        container_btn.write("Сервер выключен")
elif server_activity_check():
    container_btn.write("Сервер запущен")
else:
    container_btn.write("Сервер выключен")

if result_btn:
    st.session_state.data_frame = get_table_from_excel()

if st.session_state.data_frame != "":
    container.header("Результат")
    # width = st.sidebar.slider("plot width", 1, 25, 3)
    # height = st.sidebar.slider("plot height", 1, 25, 1)

    fig = plt.figure(figsize=(8, 5))
    sns.barplot(y="item", x="count", data=pd.DataFrame(st.session_state.data_frame))
    container.pyplot(fig)

if st.session_state.main_text != "":
    col1.subheader("Заголовок")
    col1.write(st.session_state.text_header)

    col1.subheader("Кол-во символов в тексте")
    col1.write(st.session_state.len)

    container_text.header("Текст")
    container_text.write(st.session_state.main_text)
