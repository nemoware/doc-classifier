from json import JSONDecodeError

from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
import base64
import json
import matplotlib.pyplot as plt
import pandas as pd
import re
import requests
import seaborn as sns
import streamlit as st
import tensorflow as tf

parser_version = '1.6.4'
java_subprocess = None
model_checkpoint2 = "sberbank-ai/ruRoberta-large"
path_to_model = "./doc-classification/"

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
          'Практика экспорта, оптовых продаж и сбыта бизнес-единиц (БЕ)']


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
        "http://192.168.10.36:8889/document-parser",
        data=json.dumps({
            "base64Content": encoded_string,
            "documentFileType": filename.split(".")[-1].upper()
        }),
        headers=headers
    )

    try:
        result = response.json()['documents']
        st.session_state.response = result
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
                str(x['paragraphBody']['text']) for x in document['paragraphs'][i + 1:i + 4])

            textHeader = p['paragraphHeader']['text'] + "\n".join(
                str(x['paragraphHeader']['text']) for x in document['paragraphs'][i:i + 4])

            d = i + 4
            while len(text.split()) < 300 and d < len(document['paragraphs']):
                text += document['paragraphs'][d]['paragraphBody']['text']
                d += 1

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


def find_currency_header(paragraph, keys):
    paragraph['paragraphHeader']['text'] = re.sub(' +', ' ', paragraph['paragraphHeader']['text'])
    header_text_in_low_reg = paragraph['paragraphHeader']['text'].lower()
    basic_text_in_low_reg = paragraph['paragraphBody']['text'].lower()
    if paragraph['paragraphBody']['length'] < 20:
        return False
    if len(basic_text_in_low_reg.split()) < 15:
        return False
    if re.search("(:)\s*$", basic_text_in_low_reg):
        return False
    for key in keys:
        if key.lower() in header_text_in_low_reg:
            if 'Статья'.lower() in key.lower() and any(
                    x.lower() in header_text_in_low_reg for x in
                    ['Термины и определения', 'Термин', 'определения']):
                return False

            return True

    return False


# @st.cache(allow_output_mutation=True)
def find_text(document, filename):
    result = ""
    if document['documentType'] == "CONTRACT" or document['documentType'] == "AGREEMENT":
        for ind, par in enumerate(document['paragraphs']):
            document['paragraphs'][ind]['paragraphBody']['text'] = re.sub('_+', ' ',
                                                                          par['paragraphBody'][
                                                                              'text'])

        keys = ['Общие ', 'Общие сведения', 'Общие положение', 'Статья']
        if document['documentType'] == "CONTRACT":
            sup_keys = ['предмет договра', 'предмет договора', 'Предмет контракта', 'Предмет догов',
                        'Предмет и общие условия договора']
            keys = sup_keys + keys
        if document['documentType'] == "AGREEMENT":
            keys.insert(0, 'Предмет соглашения')

        flag = False
        for i, p in enumerate(document['paragraphs']):
            if find_currency_header(p, keys):
                result = {
                    "name": filename,
                    "documentType": document['documentType'],
                    "offset": p['paragraphBody']['offset'],
                    "text": re.sub(' +', ' ', p['paragraphBody']['text']),
                    "length": p['paragraphBody']['length'],
                    "offsetHeader": p['paragraphHeader']['offset'],
                    "textHeader": p['paragraphHeader']['text'],
                    "lengthHeader": p['paragraphHeader']['length']
                }
                flag = True
                break
        if flag: return result

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
                    print("\nEnd = ", end_text)
                    text_from = re.split(f"\s({end_text})[. ]", array_of_text[2])[0]
                    break

        if text_from != "":
            result = {
                "name": filename,
                "documentType": document['documentType'],
                "offset": document['paragraphs'][0]['paragraphBody']['offset'],
                "text": text_from,
                "length": len(text_from),
                "offsetHeader": p['paragraphHeader']['offset'],
                "textHeader": p['paragraphHeader']['text'],
                "lengthHeader": p['paragraphHeader']['length']
            }
            return result

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
        for ind, par in enumerate(document['paragraphs']):
            document['paragraphs'][ind]['paragraphBody']['text'] = re.sub('_+', '',
                                                                          par['paragraphBody'][
                                                                              'text'])
        flag = False
        for i, p in enumerate(document['paragraphs']):
            if any(f.lower() in p['paragraphHeader']['text'].lower() for f in
                   ['Статья']) and p['paragraphBody'][
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
    if result != "":
        return None
    return result


def server_activity_check():
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        response = requests.get(
            "http://192.168.10.36:8889/status",
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


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_model():
    model = TFAutoModelForSequenceClassification.from_pretrained(
        str(path_to_model), num_labels=len(labels), from_pt=False
    )
    return model


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(str(model_checkpoint2))
    return tokenizer


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_tokens(text):
    tokenizer = get_tokenizer()
    result = tokenizer(text, truncation=True, max_length=512)
    return result


@st.cache(allow_output_mutation=True, show_spinner=False)
def predicate_result(text):
    tokens = get_tokens(text)
    model = get_model()
    predictions = model.predict([tokens['input_ids']])['logits']
    predictions = tf.nn.softmax(predictions, name=None)[0].numpy()
    return predictions


@st.cache(allow_output_mutation=True, show_spinner=False)
def get_dataframe(text):
    if text == "": return
    result = []
    predicate_res = predicate_result(text)
    for index, item in enumerate(predicate_res):
        result.append({
            'item': labels[index],
            'count': item
        })
    return result


for key in ['result_btn', 'start_btn', 'uploader']:
    if key not in st.session_state:
        st.session_state[key] = False

for key in ['main_text', 'len', 'text_header', 'data_frame', 'response', 'document_type']:
    if key not in st.session_state:
        st.session_state[key] = ""

st.set_page_config(layout="wide")
# st.markdown('<style>'
#             # '.css-ns78wr:nth-of-type(1){ visibility: hidden;}'
#             '.css-ns78wr:first-of-type::after{content: "Загрузить файл";}'
#             '</style>',
#             unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

uploader = col1.file_uploader("Выберите файл", ["doc", "docx"])

container_btn = col1.container()
container = col2.container()
container_text = col2.container()
container_debug = col2.container()

# start_btn = container_btn.button("Текст")
result_btn = container_btn.button("Результат")
clean_btn = container_btn.button("Очистить")
# debug_btn = container_btn.button("Ответ от парсера")
# debug_clear_btn = container_btn.button("Очистка от ответа парсера")

if clean_btn:
    col1.empty()
    col2.empty()
    st.session_state.main_text = ""
    st.session_state.data_frame = ""

if not server_activity_check():
    container_btn.error("Сервер выключен")

if result_btn and uploader:
    with st.spinner(text="Обработка документа"):
        from_parser = get_json_from_parser(uploader.getvalue(), uploader.name)
        if from_parser != "" and from_parser is not None:
            text_ = find_text(from_parser[0], uploader.name)
            if text_ != "":
                documentType = {
                    'SUPPLEMENTARY_AGREEMENT': 'Доплнительное соглашение',
                    'CONTRACT': 'Договор',
                    'AGREEMENT': 'Соглашение',
                    'PROTOCOL': 'Протокол',
                    'ANNEX': 'Устав'
                }
                st.session_state.text_header = text_['textHeader']
                st.session_state.document_type = documentType[text_['documentType']]
                st.session_state.main_text = text_['text']
                st.session_state.len = text_['length']
                st.session_state.data_frame = get_dataframe(text_['text'])
            elif from_parser[0]['documentType'] == 'PROTOCOL':
                col1.error("Данный документ является протоколом")
            elif from_parser[0]['documentType'] == 'ANNEX':
                col1.error("Данный документ является приложением")
            elif from_parser[0]['documentType'] == 'CHARTER':
                col1.error("Данный документ является уставом")
            else:
                col1.error("Не получилось найти необходимые данные из документа")
        else:
            col1.error("Ошибка при парсинге дока")

if st.session_state.data_frame != "":
    container.header("Результат")
    # width = st.sidebar.slider("plot width", 1, 25, 3)
    # height = st.sidebar.slider("plot height", 1, 25, 1)

    fig = plt.figure(figsize=(8, 5))
    sns.barplot(y="item", x="count", data=pd.DataFrame(st.session_state.data_frame))
    x1, x2, y1, y2 = plt.axis()
    plt.axis((0, 1, y1, y2))
    container.pyplot(fig)

if st.session_state.main_text != "":
    col1.subheader("Тип документа")
    col1.write(st.session_state.document_type)

    col1.subheader("Заголовок")
    col1.write(st.session_state.text_header)

    col1.subheader("Кол-во символов в тексте")
    col1.write(st.session_state.len)

    container_text.header("Текст")
    container_text.write(st.session_state.main_text)

# if debug_btn:
#     container_debug.write(st.session_state.response)
#
# if debug_clear_btn:
#     container_debug.empty()
