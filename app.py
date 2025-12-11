import random
import re

import pandas as pd
import streamlit as st
from faker import Faker


# Инициализация Faker с кешированием
@st.cache_resource
def get_fakers():
    return Faker('ru_RU'), Faker('en_US')


fake_ru, fake_en = get_fakers()

st.set_page_config(
    page_title="Генератор Тестовых Данных",
    page_icon="🔧",
    layout="wide"
)

# Ограничение для бесплатного хостинга
MAX_RECORDS = 50


def generate_snils():
    digits = [random.randint(0, 9) for _ in range(9)]
    checksum = sum((9 - i) * digits[i] for i in range(9))
    if checksum < 100:
        control = checksum
    elif checksum == 100 or checksum == 101:
        control = 0
    else:
        control = checksum % 101
        if control == 100:
            control = 0
    digits_str = ''.join(map(str, digits))
    return f"{digits_str[:3]}-{digits_str[3:6]}-{digits_str[6:9]} {control:02d}"


def generate_inn_individual():
    digits = [random.randint(0, 9) for _ in range(10)]
    weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    n11 = sum(digits[i] * weights1[i] for i in range(10)) % 11 % 10
    digits.append(n11)
    n12 = sum(digits[i] * weights2[i] for i in range(11)) % 11 % 10
    digits.append(n12)
    return ''.join(map(str, digits))


def generate_inn_company():
    digits = [random.randint(0, 9) for _ in range(9)]
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    n10 = sum(digits[i] * weights[i] for i in range(9)) % 11 % 10
    digits.append(n10)
    return ''.join(map(str, digits))


def generate_bank_card():
    prefixes = ['4', '51', '52', '53', '54', '55', '2200', '2201', '2202', '2203', '2204']
    prefix = random.choice(prefixes)
    remaining = 16 - len(prefix) - 1
    digits = list(prefix) + [str(random.randint(0, 9)) for _ in range(remaining)]

    def luhn_checksum(card_number):
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits_list = digits_of(card_number)
        odd_digits = digits_list[-1::-2]
        even_digits = digits_list[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10

    partial = ''.join(digits)
    for check_digit in range(10):
        if luhn_checksum(partial + str(check_digit)) == 0:
            digits.append(str(check_digit))
            break

    card = ''.join(digits)
    return f"{card[:4]} {card[4:8]} {card[8:12]} {card[12:16]}"


@st.cache_data(ttl=3600)
def validate_snils(snils):
    clean = re.sub(r'\D', '', snils)
    if len(clean) != 11:
        return False, "СНИЛС должен содержать 11 цифр"
    digits = [int(d) for d in clean[:9]]
    control = int(clean[9:11])
    checksum = sum((9 - i) * digits[i] for i in range(9))
    if checksum < 100:
        expected = checksum
    elif checksum == 100 or checksum == 101:
        expected = 0
    else:
        expected = checksum % 101
        if expected == 100:
            expected = 0
    if control == expected:
        return True, "СНИЛС валиден"
    return False, f"Неверная контрольная сумма (ожидалось {expected:02d})"


@st.cache_data(ttl=3600)
def validate_inn(inn):
    clean = re.sub(r'\D', '', inn)
    if len(clean) == 12:
        digits = [int(d) for d in clean]
        weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        n11 = sum(digits[i] * weights1[i] for i in range(10)) % 11 % 10
        n12 = sum(digits[i] * weights2[i] for i in range(11)) % 11 % 10
        if digits[10] == n11 and digits[11] == n12:
            return True, "ИНН физлица валиден"
        return False, "Неверная контрольная сумма ИНН физлица"
    elif len(clean) == 10:
        digits = [int(d) for d in clean]
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        n10 = sum(digits[i] * weights[i] for i in range(9)) % 11 % 10
        if digits[9] == n10:
            return True, "ИНН юрлица валиден"
        return False, "Неверная контрольная сумма ИНН юрлица"
    return False, "ИНН должен содержать 10 или 12 цифр"


@st.cache_data(ttl=3600)
def validate_card(card):
    clean = re.sub(r'\D', '', card)
    if len(clean) != 16:
        return False, "Номер карты должен содержать 16 цифр"

    def luhn_check(card_number):
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(int(x) for x in str(d * 2))
        return checksum % 10 == 0

    if luhn_check(clean):
        return True, "Номер карты валиден (Luhn)"
    return False, "Неверная контрольная сумма Luhn"


@st.cache_data(ttl=3600)
def df_to_xml(df, root_name="data", row_name="record"):
    xml_lines = [f'<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append(f'<{root_name}>')
    for _, row in df.iterrows():
        xml_lines.append(f'  <{row_name}>')
        for col in df.columns:
            safe_col = re.sub(r'[^\w]', '_', col)
            value = str(row[col]).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            xml_lines.append(f'    <{safe_col}>{value}</{safe_col}>')
        xml_lines.append(f'  </{row_name}>')
    xml_lines.append(f'</{root_name}>')
    return '\n'.join(xml_lines)


@st.cache_data(ttl=3600)
def df_to_sql(df, table_name="test_data"):
    safe_table = re.sub(r'[^\w]', '_', table_name)
    columns = [re.sub(r'[^\w]', '_', col) for col in df.columns]
    sql_lines = []
    for _, row in df.iterrows():
        values = []
        for col in df.columns:
            val = str(row[col]).replace("'", "''")
            values.append(f"'{val}'")
        sql_lines.append(f"INSERT INTO {safe_table} ({', '.join(columns)}) VALUES ({', '.join(values)});")
    return '\n'.join(sql_lines)


@st.cache_data(ttl=3600)
def generate_related_data(count):
    if count > 20:  # Ограничение для связанных данных
        count = 20

    users = []
    orders = []

    for i in range(count):
        user_id = i + 1
        user = {
            'user_id': user_id,
            'name': fake_ru.name(),
            'email': fake_en.email(),
            'phone': fake_ru.phone_number(),
            'registration_date': fake_ru.date_this_year().strftime('%d.%m.%Y')
        }
        users.append(user)

        num_orders = random.randint(1, 3)
        for j in range(num_orders):
            order = {
                'order_id': len(orders) + 1,
                'user_id': user_id,
                'product': fake_ru.word().capitalize(),
                'amount': round(random.uniform(100, 10000), 2),
                'order_date': fake_ru.date_this_month().strftime('%d.%m.%Y'),
                'status': random.choice(['Новый', 'В обработке', 'Отправлен', 'Доставлен'])
            }
            orders.append(order)

    return pd.DataFrame(users), pd.DataFrame(orders)


DATA_TYPES = {
    "Имя (русское)": lambda: fake_ru.first_name(),
    "Фамилия (русская)": lambda: fake_ru.last_name(),
    "Полное имя (русское)": lambda: fake_ru.name(),
    "Имя (английское)": lambda: fake_en.first_name(),
    "Фамилия (английская)": lambda: fake_en.last_name(),
    "Полное имя (английское)": lambda: fake_en.name(),
    "Email": lambda: fake_en.email(),
    "Телефон (Россия)": lambda: fake_ru.phone_number(),
    "Телефон (США)": lambda: fake_en.phone_number(),
    "Адрес (Россия)": lambda: fake_ru.address().replace('\n', ', '),
    "Адрес (США)": lambda: fake_en.address().replace('\n', ', '),
    "Город (Россия)": lambda: fake_ru.city(),
    "Город (США)": lambda: fake_en.city(),
    "Почтовый индекс": lambda: fake_ru.postcode(),
    "Дата рождения": lambda: fake_ru.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d.%m.%Y'),
    "Дата (случайная)": lambda: fake_ru.date_this_decade().strftime('%d.%m.%Y'),
    "Время": lambda: fake_ru.time(),
    "Пароль (простой)": lambda: fake_en.password(length=8, special_chars=False),
    "Пароль (сложный)": lambda: fake_en.password(length=16, special_chars=True, digits=True, upper_case=True),
    "Компания": lambda: fake_ru.company(),
    "Должность": lambda: fake_ru.job(),
    "UUID": lambda: str(fake_en.uuid4()),
    "IPv4 адрес": lambda: fake_en.ipv4(),
    "URL": lambda: fake_en.url(),
    "Номер карты (простой)": lambda: fake_en.credit_card_number(),
    "Текст (предложение)": lambda: fake_ru.sentence(),
    "Текст (абзац)": lambda: fake_ru.paragraph(nb_sentences=3),
    "Логин": lambda: fake_en.user_name(),
    "СНИЛС": generate_snils,
    "ИНН (физлицо)": generate_inn_individual,
    "ИНН (юрлицо)": generate_inn_company,
    "Банковская карта": generate_bank_card,
}

st.markdown("""
<style>
    /* Основной контейнер */
    .main .block-container {
        max-width: 1200px;
        padding: 1rem;
    }

    /* Адаптация под мобильные */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
            max-width: 100%;
        }

        /* Сделать колонки вертикальными */
        [data-testid="column"] {
            width: 100% !important;
            margin-bottom: 1rem;
        }

        /* Кнопки на всю ширину */
        .stButton > button {
            width: 100% !important;
            height: auto !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }

        /* Слайдеры и инпуты */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            width: 100% !important;
        }

        /* Метрики в одну колонку */
        div[data-testid="stMetric"] {
            flex-direction: column;
            align-items: flex-start;
        }

        /* Уменьшить шрифты в таблицах */
        .dataframe {
            font-size: 0.85rem !important;
        }

        /* Уменьшить отступы заголовков */
        .main-header {
            font-size: 1.8rem !important;
        }
        .sub-header {
            font-size: 1rem !important;
        }
    }

    /* Экспорт-кнопки на мобильных */
    @media (max-width: 600px) {
        section[data-testid="stDownloadButton"] > button {
            width: 100% !important;
            margin-bottom: 0.5rem;
        }
    }

    /* Ваш стиль */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Генератор Тестовых Данных</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Инструмент для QA-специалистов и разработчиков</p>', unsafe_allow_html=True)

# Предупреждение о бесплатном хостинге
st.markdown("""
<div class="warning-box">
⚠️ <strong>Бесплатный хостинг</strong>: некоторые функции ограничены (макс. 50 записей)
</div>
""", unsafe_allow_html=True)

if 'templates' not in st.session_state:
    st.session_state.templates = {}

tabs = st.tabs(["Генератор данных", "Связанные данные", "Валидация", "Шаблоны"])

with tabs[0]:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Настройки генерации")

        categories = {
            "Персональные данные": ["Имя (русское)", "Фамилия (русская)", "Полное имя (русское)",
                                    "Имя (английское)", "Фамилия (английская)", "Полное имя (английское)"],
            "Контакты": ["Email", "Телефон (Россия)", "Телефон (США)"],
            "Адреса": ["Адрес (Россия)", "Адрес (США)", "Город (Россия)", "Город (США)", "Почтовый индекс"],
            "Даты и время": ["Дата рождения", "Дата (случайная)", "Время"],
            "Безопасность": ["Пароль (простой)", "Пароль (сложный)", "Логин"],
            "Документы РФ": ["СНИЛС", "ИНН (физлицо)", "ИНН (юрлицо)", "Банковская карта"],
            "Работа": ["Компания", "Должность"],
            "Технические": ["UUID", "IPv4 адрес", "URL", "Номер карты (простой)"],
            "Текст": ["Текст (предложение)", "Текст (абзац)"]
        }

        selected_category = st.selectbox("Категория:", list(categories.keys()))

        available_types = categories[selected_category]
        selected_types = st.multiselect(
            "Выберите типы данных:",
            options=available_types,
            default=[available_types[0]] if available_types else [],
            help="Можно выбрать несколько типов данных"
        )

        count = st.slider(
            "Количество записей:",
            min_value=1,
            max_value=MAX_RECORDS,
            value=10,
            help=f"На бесплатном хостинге ограничение: {MAX_RECORDS} записей"
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            generate_button = st.button("Сгенерировать", type="primary", use_container_width=True)
        with col_btn2:
            save_template = st.button("Сохранить шаблон", use_container_width=True)

        if save_template and selected_types:
            template_name = st.session_state.get('new_template_name', f"Шаблон {len(st.session_state.templates) + 1}")
            st.session_state.templates[template_name] = {
                'types': selected_types,
                'count': count
            }
            st.success(f"Шаблон сохранён!")

        template_name_input = st.text_input("Имя шаблона:", key="new_template_name", placeholder="Введите имя шаблона")

    with col2:
        st.subheader("Результат")

        if generate_button and selected_types:
            with st.spinner("Генерация данных..."):
                data = {dtype: [DATA_TYPES[dtype]() for _ in range(count)] for dtype in selected_types}
                df = pd.DataFrame(data)
                st.session_state['generated_data'] = df
                st.session_state['generated'] = True
        elif generate_button and not selected_types:
            st.session_state['generated'] = False
            if 'generated_data' in st.session_state:
                del st.session_state['generated_data']

        if 'generated_data' in st.session_state and st.session_state.get('generated', False):
            df = st.session_state['generated_data']

            stat_cols = st.columns(3)
            with stat_cols[0]:
                st.metric("Записей", len(df))
            with stat_cols[1]:
                st.metric("Полей", len(df.columns))
            with stat_cols[2]:
                st.metric("Всего ячеек", len(df) * len(df.columns))

            st.dataframe(df, use_container_width=True, height=300)

            st.subheader("Экспорт данных")

            csv_data = df.to_csv(index=False, encoding='utf-8')
            json_data = df.to_json(orient='records', force_ascii=False, indent=2)
            xml_data = df_to_xml(df)
            sql_data = df_to_sql(df)

            export_cols = st.columns(4)

            with export_cols[0]:
                st.download_button(
                    label="CSV",
                    data=csv_data,
                    file_name="test_data.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with export_cols[1]:
                st.download_button(
                    label="JSON",
                    data=json_data,
                    file_name="test_data.json",
                    mime="application/json",
                    use_container_width=True
                )

            with export_cols[2]:
                st.download_button(
                    label="XML",
                    data=xml_data,
                    file_name="test_data.xml",
                    mime="application/xml",
                    use_container_width=True
                )

            with export_cols[3]:
                st.download_button(
                    label="SQL",
                    data=sql_data,
                    file_name="test_data.sql",
                    mime="text/plain",
                    use_container_width=True
                )

            st.subheader("Копировать в буфер")
            copy_format = st.selectbox("Формат:", ["CSV", "JSON", "XML", "SQL"])

            if copy_format == "CSV":
                copy_data = csv_data
            elif copy_format == "JSON":
                copy_data = json_data
            elif copy_format == "XML":
                copy_data = xml_data
            else:
                copy_data = sql_data

            st.code(copy_data[:500] + ("..." if len(copy_data) > 500 else ""), language='text')
            st.info("Выделите текст выше и скопируйте (Ctrl+C / Cmd+C)")

            with st.expander("Полный просмотр данных"):
                preview_format = st.radio("Формат просмотра:", ["JSON", "CSV", "XML", "SQL"], horizontal=True)
                if preview_format == "JSON":
                    st.code(json_data, language='json')
                elif preview_format == "CSV":
                    st.code(csv_data, language='csv')
                elif preview_format == "XML":
                    st.code(xml_data, language='xml')
                else:
                    st.code(sql_data, language='sql')

        elif generate_button and not selected_types:
            st.warning("Пожалуйста, выберите хотя бы один тип данных")
        else:
            st.info("Выберите типы данных и нажмите 'Сгенерировать'")

with tabs[1]:
    st.subheader("Генерация связанных данных")
    st.markdown("Создание связанных наборов данных: пользователи и их заказы")

    related_count = st.slider("Количество пользователей:", min_value=1, max_value=20, value=5, key="related_count")

    if st.button("Сгенерировать связанные данные", type="primary"):
        with st.spinner("Генерация связанных данных..."):
            users_df, orders_df = generate_related_data(related_count)
            st.session_state['users_data'] = users_df
            st.session_state['orders_data'] = orders_df

    if 'users_data' in st.session_state and 'orders_data' in st.session_state:
        col_users, col_orders = st.columns(2)

        with col_users:
            st.markdown("**Пользователи**")
            st.dataframe(st.session_state['users_data'], use_container_width=True, height=300)

            users_csv = st.session_state['users_data'].to_csv(index=False, encoding='utf-8')
            users_json = st.session_state['users_data'].to_json(orient='records', force_ascii=False, indent=2)

            ucol1, ucol2 = st.columns(2)
            with ucol1:
                st.download_button("CSV", users_csv, "users.csv", "text/csv", use_container_width=True)
            with ucol2:
                st.download_button("JSON", users_json, "users.json", "application/json", use_container_width=True)

        with col_orders:
            st.markdown("**Заказы**")
            st.dataframe(st.session_state['orders_data'], use_container_width=True, height=300)

            orders_csv = st.session_state['orders_data'].to_csv(index=False, encoding='utf-8')
            orders_json = st.session_state['orders_data'].to_json(orient='records', force_ascii=False, indent=2)

            ocol1, ocol2 = st.columns(2)
            with ocol1:
                st.download_button("CSV", orders_csv, "orders.csv", "text/csv", use_container_width=True,
                                   key="orders_csv")
            with ocol2:
                st.download_button("JSON", orders_json, "orders.json", "application/json", use_container_width=True,
                                   key="orders_json")

        st.markdown("**SQL для создания таблиц:**")
        sql_schema = """
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    registration_date DATE
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    product VARCHAR(255),
    amount DECIMAL(10, 2),
    order_date DATE,
    status VARCHAR(50)
);
"""
        st.code(sql_schema, language='sql')

        combined_sql = sql_schema + "\n\n-- Данные пользователей\n" + df_to_sql(st.session_state['users_data'], 'users')
        combined_sql += "\n\n-- Данные заказов\n" + df_to_sql(st.session_state['orders_data'], 'orders')

        st.download_button("Скачать SQL (схема + данные)", combined_sql, "related_data.sql", "text/plain",
                           use_container_width=True)

with tabs[2]:
    st.subheader("Валидация данных")
    st.markdown("Проверьте корректность сгенерированных данных")

    validation_type = st.selectbox("Тип данных для проверки:", ["СНИЛС", "ИНН", "Банковская карта"])

    col_val1, col_val2 = st.columns([2, 1])

    with col_val1:
        if validation_type == "СНИЛС":
            test_value = st.text_input("Введите СНИЛС:", placeholder="123-456-789 00")
            example = generate_snils()
            st.caption(f"Пример: {example}")

            if test_value:
                is_valid, message = validate_snils(test_value)
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)

            st.markdown("**Алгоритм проверки СНИЛС:**")
            st.markdown("""
1. СНИЛС состоит из 11 цифр: 9 основных + 2 контрольных
2. Контрольная сумма = сумма произведений цифр на позиционные веса (9, 8, 7, 6, 5, 4, 3, 2, 1)
3. Если сумма < 100 — это и есть контрольное число
4. Если сумма = 100 или 101 — контрольное число = 00
5. Иначе: сумма mod 101 (если результат = 100, то 00)
            """)

        elif validation_type == "ИНН":
            test_value = st.text_input("Введите ИНН:", placeholder="123456789012 или 1234567890")
            example_ind = generate_inn_individual()
            example_comp = generate_inn_company()
            st.caption(f"Пример (физлицо): {example_ind}")
            st.caption(f"Пример (юрлицо): {example_comp}")

            if test_value:
                is_valid, message = validate_inn(test_value)
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)

            st.markdown("**Алгоритм проверки ИНН:**")
            st.markdown("""
**ИНН физлица (12 цифр):**
- 11-я цифра: контрольная сумма первых 10 цифр с весами [7,2,4,10,3,5,9,4,6,8] mod 11 mod 10
- 12-я цифра: контрольная сумма первых 11 цифр с весами [3,7,2,4,10,3,5,9,4,6,8] mod 11 mod 10

**ИНН юрлица (10 цифр):**
- 10-я цифра: контрольная сумма первых 9 цифр с весами [2,4,10,3,5,9,4,6,8] mod 11 mod 10
            """)

        else:
            test_value = st.text_input("Введите номер карты:", placeholder="4276 1234 5678 9012")
            example = generate_bank_card()
            st.caption(f"Пример: {example}")

            if test_value:
                is_valid, message = validate_card(test_value)
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)

            st.markdown("**Алгоритм Луна (Luhn):**")
            st.markdown("""
1. Начиная с последней цифры, удваиваем каждую вторую цифру
2. Если результат > 9, вычитаем 9
3. Суммируем все цифры
4. Если сумма делится на 10 без остатка — номер валиден
            """)

    with col_val2:
        st.markdown("**Быстрая генерация:**")
        if st.button("Сгенерировать СНИЛС"):
            st.code(generate_snils())
        if st.button("Сгенерировать ИНН физлица"):
            st.code(generate_inn_individual())
        if st.button("Сгенерировать ИНН юрлица"):
            st.code(generate_inn_company())
        if st.button("Сгенерировать карту"):
            st.code(generate_bank_card())

with tabs[3]:
    st.subheader("Сохранённые шаблоны")

    if st.session_state.templates:
        template_to_delete = None
        template_names = list(st.session_state.templates.keys())

        for name in template_names:
            template = st.session_state.templates[name]
            with st.expander(f"📋 {name}"):
                st.write(f"**Типы данных:** {', '.join(template['types'])}")
                st.write(f"**Количество записей:** {template['count']}")

                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    if st.button(f"Применить", key=f"apply_{name}"):
                        data = {dtype: [DATA_TYPES[dtype]() for _ in range(template['count'])] for dtype in
                                template['types']}
                        df = pd.DataFrame(data)
                        st.session_state['generated_data'] = df
                        st.session_state['generated'] = True
                        st.success("Данные сгенерированы! Перейдите на вкладку 'Генератор данных'")
                with col_t2:
                    if st.button(f"Удалить", key=f"delete_{name}"):
                        template_to_delete = name

        if template_to_delete:
            del st.session_state.templates[template_to_delete]
            st.rerun()
    else:
        st.info("Нет сохранённых шаблонов. Создайте шаблон на вкладке 'Генератор данных'")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>Создано с использованием Python, Streamlit и Faker</p>
    <p>Инструмент для генерации тестовых данных для QA-специалистов</p>
</div>
""", unsafe_allow_html=True)
