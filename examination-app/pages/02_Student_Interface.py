import streamlit as st
from datetime import datetime
import pandas as pd
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from deep_translator import GoogleTranslator

st.set_page_config(page_title="Examination Portal", layout="wide")
st.title("📚 Examination Portal")

@st.cache_data(show_spinner=False)
def get_translated_questions_and_options(questions, options_list, language_code):
    if language_code == "en":
        translated_questions = questions
        translated_options_list = [json.loads(opt) if pd.notna(opt) and opt else [] for opt in options_list]
        return translated_questions, translated_options_list

    translated_questions = []
    translated_options_list = []

    for idx, q in enumerate(questions):
        try:
            translated_q = GoogleTranslator(source='auto', target=language_code).translate(q)
        except Exception:
            translated_q = q

        options_raw = options_list[idx]
        options = json.loads(options_raw) if pd.notna(options_raw) and options_raw else []

        translated_opts = []
        for opt in options:
            try:
                translated_opt = GoogleTranslator(source='auto', target=language_code).translate(opt)
            except Exception:
                translated_opt = opt
            translated_opts.append(translated_opt)

        translated_questions.append(translated_q)
        translated_options_list.append(translated_opts)

    return translated_questions, translated_options_list


def has_already_submitted(reg_no, institution_code):
    responses_file = f"src/responses_{institution_code}.csv"
    if os.path.isfile(responses_file):
        df = pd.read_csv(responses_file)
        return reg_no in df["reg_no"].astype(str).values
    return False


def display_questions(language_code):
    student_details = st.session_state.get("student_details", {})
    questions_file = st.session_state.get("questions_file", "")

    if not questions_file or not os.path.isfile(questions_file):
        st.error("Questions file not found. Please contact your administrator.")
        return

    df = pd.read_csv(questions_file)
    questions = df["question"].tolist()
    options_list = df["options"].tolist()
    marks_list = df["marks"].tolist()

    translated_questions, translated_options_list = get_translated_questions_and_options(
        questions, options_list, language_code
    )

    answers = []

    for idx, question in enumerate(translated_questions):
        marks = marks_list[idx]

        original_options = json.loads(options_list[idx]) if pd.notna(options_list[idx]) and options_list[idx] else []
        translated_opts = translated_options_list[idx]

        label = f"{idx+1}. {question}  _(Marks: {marks})_"

        if original_options:
            option_map = dict(zip(translated_opts, original_options))

            selected_translated = st.radio(
                label,
                translated_opts,
                key=f"answer_{idx}",
                index=None
            )

            answer = option_map[selected_translated] if selected_translated else ""
        else:
            answer = st.text_input(label, key=f"answer_{idx}")

        answers.append(answer)

    confirm = st.checkbox("I confirm that I have answered all the questions.")

    if st.button("Submit Answers", disabled=not confirm):

        response = {
            "name": student_details.get("name", ""),
            "reg_no": student_details.get("reg_no", ""),
            "year": student_details.get("year", ""),
            "date": student_details.get("date", ""),
            "institution_code": student_details.get("institution_code", ""),
        }

        for idx, ans in enumerate(answers):
            response[f"answer_{idx}"] = ans

        responses_file = st.session_state.get("responses_file", "")

        df = pd.DataFrame([response])

        if os.path.isfile(responses_file):
            df.to_csv(responses_file, mode="a", header=False, index=False)
        else:
            df.to_csv(responses_file, index=False)

        st.success("✅ Your answers have been submitted successfully!")

        st.session_state.details_submitted = False
        st.session_state.student_details = {}

        st.stop()


# Main student interface
languages = {
    "English": "en",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Hindi": "hi",
    "Malayalam": "ml",
    "Tamil": "ta",
    "Kannada": "kn",
    "Telugu": "te",
    "Gujarati": "gu",
    "Marathi": "mr",
    "Bengali": "bn",
    "Punjabi": "pa",
    "Urdu": "ur",
    "Odia": "or"
}

if "student_details" not in st.session_state:
    st.session_state.student_details = {}

if "details_submitted" not in st.session_state:
    st.session_state.details_submitted = False

if "selected_language" not in st.session_state:
    st.session_state.selected_language = "en"

admin_code_path = "current_institution.txt"
admin_institution_code = ""

if os.path.isfile(admin_code_path):
    with open(admin_code_path) as f:
        admin_institution_code = f.read().strip()

if not st.session_state.details_submitted:

    with st.form("student_details_form"):

        name = st.text_input("Name")
        reg_no = st.text_input("Register No:")
        year = st.text_input("Year of Admission")
        date = st.date_input("Date of Examination", value=datetime.today(), disabled=True)

        language_name = st.selectbox("Select Language", list(languages.keys()))
        language_code = languages[language_name]

        institution_code = st.text_input("Institution Code")

        submitted = st.form_submit_button("Submit Details")

        if submitted:

            code_clean = institution_code.strip()

            if not name or not reg_no or not year or not code_clean:
                st.warning("Please fill all details.")

            elif code_clean != admin_institution_code:
                st.warning("Invalid Institution Code.")

            else:

                questions_file = os.path.join("src", f"questions/questions_{code_clean}.csv")
                responses_file = os.path.join("src", f"responses_{code_clean}.csv")

                if not os.path.isfile(questions_file):

                    st.error("Exam not available yet.")

                elif has_already_submitted(reg_no, code_clean):

                    st.warning("You have already submitted answers.")

                else:

                    st.session_state.student_details = {
                        "name": name,
                        "reg_no": reg_no,
                        "year": year,
                        "date": date,
                        "institution_code": code_clean
                    }

                    st.session_state.questions_file = questions_file
                    st.session_state.responses_file = responses_file
                    st.session_state.selected_language = language_code
                    st.session_state.details_submitted = True

                    st.success("Details submitted successfully!")

                    st.rerun()

else:
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔙 Back to Details"):
            st.session_state.details_submitted = False
            st.session_state.student_details = {}
            st.rerun()
    
    display_questions(st.session_state.selected_language)
