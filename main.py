import base64
import json
from json import JSONDecodeError

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
import streamlit as st
import tensorflow as tf
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification

from search_text import find_text,wrapper
from search_text_v2 import get_text

parser_version = '1.6.7'
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
          'Практика экспорта, оптовых продаж и сбыта бизнес-единиц']


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
    is_doc = True
    is_docx = True
    is_bad_doc = False
    doc_type = filename.split(".")[-1].upper()
    while is_doc or is_docx:
        # "http://localhost:8889/document-parser"
        # "http://192.168.10.36:8889/document-parser"
        response = requests.post(
            "http://192.168.10.36:8889/document-parser",
            data=json.dumps({
                "base64Content": encoded_string,
                "documentFileType": doc_type
            }),
            headers=headers
        )
        if 'message' in response.json():
            if doc_type == 'DOC':
                is_doc = False
                doc_type = 'DOCX'
                continue
            if doc_type == 'DOCX':
                is_docx = False
                doc_type = 'DOC'
                continue

        try:
            result = response.json()['documents']
            st.session_state.response = result
        except Exception as e:
            col1.error(f"\nОшибка в файле: {doc}\nОтвет от парсера: {response.json()}")
            return
        finally:
            is_doc = False
            is_docx = False

    return result


def server_activity_check():
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json; text/plain'
    }
    try:
        # "http://localhost:8889/status"
        # "http://192.168.10.36:8889/status"
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

for key in ['main_text', 'len', 'text_header', 'data_frame', 'response', 'document_type', 'document']:
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

start_btn = container_btn.button("Текст")
result_btn = container_btn.button("Результат")
clean_btn = container_btn.button("Очистить")
debug_btn = container_btn.button("Ответ от парсера")
debug_clear_btn = container_btn.button("Очистка от ответа парсера")

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
            text_, enum = get_text(from_parser[0], uploader.name)
            # practice = wrapper(from_parser)
            # col1.write(practice)
            if text_['text'] != "":
                documentType = {
                    'SUPPLEMENTARY_AGREEMENT': 'Дополнительное соглашение',
                    'CONTRACT': 'Договор',
                    'AGREEMENT': 'Соглашение',
                    'PROTOCOL': 'Протокол',
                    'CHARTER': 'Устав',
                    'ANNEX': 'Приложение',
                    'UNKNOWN': 'Входящие документы',
                    'REGULATION': 'Регламент',
                    'ORDER': 'Распорядительный документ',
                    'POWER_OF_ATTORNEY': 'Доверенность',
                    'WORK_PLAN': 'Рабочий план'
                }

                # st.session_state.text_header = text_['textHeader']
                st.session_state.document = text_
                st.session_state.document_type = documentType[text_['documentType']]
                st.session_state.main_text = text_['text']
                st.session_state.len = text_['length']
                st.session_state.data_frame = get_dataframe(text_['text'])
            else:
                col1.error("Не получилось найти необходимые данные из документа")
        else:
            col1.error("Ошибка при парсинге дока")

# if st.session_state.document != "":
    # document = st.session_state.document
    # container_btn.write({
    #     "key": document["key"],
    #     "percentage": document["percentage"]
    # })

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

if debug_btn:
    container_debug.write(st.session_state.response)

if debug_clear_btn:
    container_debug.empty()
