import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

# ------------------------------------------------------------
# 1. Настройка страницы
# ------------------------------------------------------------
st.set_page_config(page_title="Анализ счастья в мире (2015–2019)", layout="wide")
st.title("Мировой индекс счастья — анализ 2015–2019")
st.markdown("Интерактивный дашборд для исследования данных о счастье в разных странах и регионах.")

# ------------------------------------------------------------
# 2. Загрузка и объединение данных (с кэшированием)
# ------------------------------------------------------------
@st.cache_data
def load_and_merge():
    # Словарь с маппингом старых и новых названий колонок
    # Для 2015-2017
    cols_old = {
        "Country": "Country",
        "Region": "Region",
        "Happiness Score": "Score",
        "Economy (GDP per Capita)": "GDP per capita",
        "Family": "Social support",
        "Health (Life Expectancy)": "Healthy life expectancy",
        "Freedom": "Freedom to make life choices",
        "Generosity": "Generosity",
        "Trust (Government Corruption)": "Perceptions of corruption"
    }
    # Для 2018-2019 (названия уже близки, но переименуем для единообразия)
    cols_new = {
        "Country or region": "Country",
        "Overall rank": "Happiness Rank",
        "Score": "Score",
        "GDP per capita": "GDP per capita",
        "Social support": "Social support",
        "Healthy life expectancy": "Healthy life expectancy",
        "Freedom to make life choices": "Freedom to make life choices",
        "Generosity": "Generosity",
        "Perceptions of corruption": "Perceptions of corruption"
    }

    data_frames = []
    for year in range(2015, 2020):
        file_path = f"data/{year}.csv"
        try:
            df = pd.read_csv(file_path)
            # Удалим лишние пробелы в названиях колонок
            df.columns = df.columns.str.strip()
            if year <= 2017:
                # Выбираем только нужные колонки (которые есть в маппинге)
                available = [col for col in cols_old.keys() if col in df.columns]
                df = df[available]
                df = df.rename(columns=cols_old)
            else:
                # Для 2018 и 2019
                available = [col for col in cols_new.keys() if col in df.columns]
                df = df[available]
                df = df.rename(columns=cols_new)
            df["Year"] = year
            data_frames.append(df)
        except FileNotFoundError:
            st.warning(f"Файл {year}.csv не найден в папке data/")
    if not data_frames:
        st.error("Не удалось загрузить ни одного файла. Проверьте путь к данным.")
        st.stop()
    merged = pd.concat(data_frames, ignore_index=True)
    # Приведём числовые колонки к float (на случай ошибок)
    numeric_cols = ["Score", "GDP per capita", "Social support", "Healthy life expectancy",
                    "Freedom to make life choices", "Generosity", "Perceptions of corruption"]
    for col in numeric_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
    # Удалим строки, где нет Score (целевой показатель)
    merged = merged.dropna(subset=["Score"])
    return merged

df = load_and_merge()

# ------------------------------------------------------------
# 3. Боковая панель с фильтрами
# ------------------------------------------------------------
st.sidebar.header("Фильтры")

# Выбор года (мультивыбор)
years = sorted(df["Year"].unique())
selected_years = st.sidebar.multiselect("Год(ы):", years, default=years)

# Выбор региона (если есть колонка Region, иначе показываем все)
if "Region" in df.columns:
    regions = ["Все"] + sorted(df["Region"].dropna().unique())
    selected_region = st.sidebar.selectbox("Регион:", regions)
else:
    selected_region = "Все"

# Диапазон счастья (Score)
min_score = float(df["Score"].min())
max_score = float(df["Score"].max())
score_range = st.sidebar.slider("Диапазон Happiness Score:",
                                 min_value=min_score, max_value=max_score,
                                 value=(min_score, max_score))

# Применяем фильтры
filtered = df.copy()
filtered = filtered[filtered["Year"].isin(selected_years)]
if selected_region != "Все" and "Region" in filtered.columns:
    filtered = filtered[filtered["Region"] == selected_region]
filtered = filtered[(filtered["Score"] >= score_range[0]) & (filtered["Score"] <= score_range[1])]

# ------------------------------------------------------------
# 4. Метрики (карточки)
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Стран в выборке", len(filtered))
col2.metric("Средний Score", f"{filtered['Score'].mean():.2f}")
col3.metric("Макс. Score", f"{filtered['Score'].max():.2f}")
col4.metric("Мин. Score", f"{filtered['Score'].min():.2f}")

# ------------------------------------------------------------
# 5. Вкладки
# ------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Графики", "Данные", "Корреляции", "Выводы"])

with tab1:
    st.subheader("Топ-10 стран по уровню счастья (выбранный период)")
    # Агрегируем по странам (средний Score за выбранные годы)
    top10 = filtered.groupby("Country")["Score"].mean().sort_values(ascending=False).head(10)
    fig_bar = px.bar(x=top10.values, y=top10.index, orientation='h',
                     labels={'x': 'Happiness Score', 'y': 'Country'},
                     title="Топ-10 счастливых стран")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("ВВП на душу населения vs Уровень счастья")
    # Scatter plot с возможностью выбрать цвет по году или региону
    color_col = "Year" if "Year" in filtered.columns else None
    fig_scatter = px.scatter(filtered, x="GDP per capita", y="Score",
                             color=color_col, hover_name="Country",
                             title="Зависимость счастья от ВВП")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Динамика счастья по годам (топ-5 стран)")
    # Выберем 5 стран с наибольшим средним Score
    top5_countries = filtered.groupby("Country")["Score"].mean().nlargest(5).index
    df_top5 = filtered[filtered["Country"].isin(top5_countries)]
    fig_line = px.line(df_top5, x="Year", y="Score", color="Country",
                       title="Изменение индекса счастья")
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    st.subheader("Таблица данных (с фильтрами)")
    st.dataframe(filtered, use_container_width=True)

    st.subheader("Описательная статистика (числовые столбцы)")
    numeric_df = filtered.select_dtypes(include=[np.number])
    st.write(numeric_df.describe())

with tab3:
    st.subheader("Корреляционная матрица")
    # Выбираем только числовые колонки, которые нас интересуют
    corr_cols = ["Score", "GDP per capita", "Social support", "Healthy life expectancy",
                 "Freedom to make life choices", "Generosity", "Perceptions of corruption"]
    available_corr = [c for c in corr_cols if c in filtered.columns]
    if len(available_corr) > 1:
        corr_matrix = filtered[available_corr].corr().round(2)
        # Тепловая карта с plotly
        fig_corr = px.imshow(corr_matrix, text_auto=True, aspect="auto",
                             color_continuous_scale="RdBu_r",
                             title="Корреляция между показателями")
        st.plotly_chart(fig_corr, use_container_width=True)
        # Дополнительно покажем таблицу
        st.write("Таблица корреляций:")
        st.dataframe(corr_matrix)
    else:
        st.warning("Недостаточно числовых колонок для корреляционного анализа.")

with tab4:
    st.subheader("Основные выводы по данным")
    st.markdown("""
    - **Связь ВВП и счастья:** наблюдается умеренная положительная корреляция (обычно 0.6–0.8). Более богатые страны в среднем счастливее.
    - **Социальная поддержка** и **ожидаемая продолжительность здоровой жизни** также сильно коррелируют с уровнем счастья.
    - **Восприятие коррупции** обычно имеет отрицательную корреляцию: в странах с меньшей коррупцией люди счастливее.
    - **Щедрость** (Generosity) влияет слабее, но в некоторых культурах даёт положительный вклад.
    - **Динамика по годам:** лидеры (Финляндия, Дания, Норвегия) стабильно занимают высокие позиции. Страны с военными конфликтами или экономическими проблемами (Сирия, Йемен, Бурунди) находятся внизу рейтинга.
    - **Региональные различия:** Западная Европа, Северная Америка и Океания лидируют; Африка южнее Сахары и Южная Азия замыкают рейтинг.
    """)

# ------------------------------------------------------------
# 6. Дополнительно: кнопка для скачивания отфильтрованных данных
# ------------------------------------------------------------
st.sidebar.markdown("---")
csv = filtered.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Скачать отфильтрованные данные (CSV)", data=csv,
                           file_name="filtered_happiness_data.csv", mime="text/csv")