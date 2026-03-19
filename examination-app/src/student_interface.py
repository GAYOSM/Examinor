import streamlit as st
from datetime import datetime
import pandas as pd
import os
import json

def has_already_submitted(reg_no, institution_code):
    responses_file = f"src/responses_{institution_code}.csv"
    if os.path.isfile(responses_file):
        df = pd.read_csv(responses_file)
        return str(reg_no) in df["reg_no"].astype(str).values
    return False

def display_questions(questions_file):
    if not os.path.isfile(questions_file):
        st.error("Questions file not found.")
        return
    df = pd.read_csv(questions_file)
    questions = df["question"].tolist()
    translated_options = df["options"].tolist()
    original_options = df.get("original_options", df["options"]).tolist()
    marks_list = df["marks"].tolist()

    answers = []
    for idx, question in enumerate(questions):
        marks = marks_list[idx]
        t_opts = json.loads(translated_options[idx]) if pd.notna(translated_options[idx]) else []
        o_opts = json.loads(original_options[idx]) if pd.notna(original_options[idx]) else []
        
        label = f"{idx+1}. {question} _(Marks: {marks})_"
        if t_opts:
            option_map = dict(zip(t_opts, o_opts))
            selected = st.radio(label, t_opts, key=f"answer_{idx}", index=None)
            answer = option_map.get(selected, "") if selected else ""
        else:
            answer = st.text_input(label, key=f"answer_{idx}")
        answers.append(answer)

    confirm = st.checkbox("I confirm that I have answered all the questions.")
    if st.button("Submit Answers", disabled=not confirm):
        student_details = st.session_state.get("student_details", {})
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
        df_new = pd.DataFrame([response])
        if os.path.isfile(responses_file):
            df_new.to_csv(responses_file, mode="a", header=False, index=False)
        else:
            df_new.to_csv(responses_file, index=False)
        
        st.success("✅ Your answers have been submitted successfully!")
        st.session_state.details_submitted = False
        st.session_state.student_details = {}
        st.rerun()

def student_interface():
    st.title("Examination Portal")
    languages = {
        "English": "en", "French": "fr", "German": "de", "Spanish": "es",
        "Hindi": "hi", "Malayalam": "ml", "Tamil": "ta", "Kannada": "kn",
        "Telugu": "te", "Gujarati": "gu", "Marathi": "mr", "Bengali": "bn",
        "Punjabi": "pa", "Urdu": "ur", "Odia": "or"
    }

    if "student_details" not in st.session_state: st.session_state.student_details = {}
    if "details_submitted" not in st.session_state: st.session_state.details_submitted = False
    if "questions_file" not in st.session_state: st.session_state.questions_file = None

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
                else:
                    admin_code = open("current_institution.txt").read().strip() if os.path.isfile("current_institution.txt") else ""
                    if code_clean != admin_code:
                        st.warning("Invalid Institution Code.")
                    else:
                        lang_folder = f"src/questions/{code_clean}"
                        questions_file = f"{lang_folder}/questions_{language_code}.csv"
                        if not os.path.isfile(questions_file):
                            questions_file = f"{lang_folder}/questions_en.csv"
                        
                        if not os.path.isfile(questions_file):
                            st.error("Exam not available yet.")
                        elif has_already_submitted(reg_no, code_clean):
                            st.warning("You have already submitted answers.")
                        else:
                            st.session_state.student_details = {"name": name, "reg_no": reg_no, "year": year, "date": date, "institution_code": code_clean}
                            st.session_state.questions_file = questions_file
                            st.session_state.responses_file = f"src/responses_{code_clean}.csv"
                            st.session_state.details_submitted = True
                            st.success("Details submitted successfully!")
                            st.rerun()
    else:
        display_questions(st.session_state.questions_file)

if __name__ == "__main__":
    student_interface()