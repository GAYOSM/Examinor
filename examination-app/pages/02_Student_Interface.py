import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from deep_translator import GoogleTranslator

st.set_page_config(page_title="Examination Portal", layout="wide")
st.title("📚 Examination Portal")

# --- Subject & Time Limit Management ---
def get_subject_title(institution_code):
    """Get subject title for a specific institution."""
    titles_file = "subject_titles.json"
    if os.path.isfile(titles_file):
        try:
            with open(titles_file) as f:
                titles = json.load(f)
                return titles.get(institution_code, "")
        except:
            return ""
    return ""

def get_time_limit(institution_code):
    """Get time limit (in minutes) for a specific institution."""
    limits_file = "time_limits.json"
    if os.path.isfile(limits_file):
        try:
            with open(limits_file) as f:
                limits = json.load(f)
                return limits.get(institution_code, 60)  # Default 60 minutes
        except:
            return 60
    return 60

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
    institution_code = student_details.get("institution_code", "")
    time_limit_minutes = get_time_limit(institution_code)
    exam_start_time = st.session_state.get("exam_start_time")

    if not questions_file or not os.path.isfile(questions_file):
        st.error("Questions file not found. Please contact your administrator.")
        return

    # --- Timer Display and Auto-Submit Logic ---
    if exam_start_time:
        elapsed_time = datetime.now() - exam_start_time
        total_seconds = int(time_limit_minutes * 60)
        elapsed_seconds = int(elapsed_time.total_seconds())
        remaining_seconds = max(0, total_seconds - elapsed_seconds)
        
        # Convert remaining seconds to minutes and seconds
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60
        
        # Display timer at the top
        timer_col1, timer_col2, timer_col3 = st.columns([2, 2, 1])
        with timer_col1:
            st.write("")  # Empty space
        with timer_col2:
            if remaining_seconds <= 300:  # 5 minutes or less - show in red
                st.markdown(f"<h2 style='text-align: center; color: #FF4444;'>⏱️ Time Remaining: {remaining_minutes:02d}:{remaining_secs:02d}</h2>", unsafe_allow_html=True)
            elif remaining_seconds <= 600:  # 10 minutes or less - show in orange
                st.markdown(f"<h2 style='text-align: center; color: #FF8800;'>⏱️ Time Remaining: {remaining_minutes:02d}:{remaining_secs:02d}</h2>", unsafe_allow_html=True)
            else:  # More than 10 minutes - show in green
                st.markdown(f"<h2 style='text-align: center; color: #00AA00;'>⏱️ Time Remaining: {remaining_minutes:02d}:{remaining_secs:02d}</h2>", unsafe_allow_html=True)
        with timer_col3:
            st.write("")  # Empty space
        
        st.divider()
        
        # Auto-submit if time is up
        if remaining_seconds <= 0:
            st.error("⏰ Time Limit Exceeded! Your exam will be auto-submitted now.")
            st.session_state.auto_submit = True
            st.rerun()
        
        # Rerun every second to update timer
        st.markdown(f"<meta http-equiv='refresh' content='1'>", unsafe_allow_html=True)

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
    
    # Check if auto-submit is triggered
    auto_submit = st.session_state.get("auto_submit", False)

    if st.button("Submit Answers", disabled=not confirm) or auto_submit:

        response = {
            "name": student_details.get("name", ""),
            "reg_no": student_details.get("reg_no", ""),
            "year": student_details.get("year", ""),
            "date": student_details.get("date", ""),
            "institution_code": student_details.get("institution_code", ""),
            "submission_type": "auto-submitted" if auto_submit else "manual"
        }

        for idx, ans in enumerate(answers):
            response[f"answer_{idx}"] = ans

        responses_file = st.session_state.get("responses_file", "")

        df = pd.DataFrame([response])

        if os.path.isfile(responses_file):
            df.to_csv(responses_file, mode="a", header=False, index=False)
        else:
            df.to_csv(responses_file, index=False)

        if auto_submit:
            st.warning("⏰ Your exam has been auto-submitted due to time limit expiration.")
        else:
            st.success("✅ Your answers have been submitted successfully!")

        st.session_state.details_submitted = False
        st.session_state.subject_confirmed = False
        st.session_state.exam_start_time = None
        st.session_state.auto_submit = False
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

if "subject_confirmed" not in st.session_state:
    st.session_state.subject_confirmed = False

if "selected_language" not in st.session_state:
    st.session_state.selected_language = "en"

if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = None

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

        institution_code = st.text_input("Pass Code")

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
                    st.session_state.subject_confirmed = False

                    st.success("Details submitted successfully!")

                    st.rerun()

elif not st.session_state.subject_confirmed:
    # --- Subject Confirmation Page ---
    student_details = st.session_state.get("student_details", {})
    institution_code = student_details.get("institution_code", "")
    subject_title = get_subject_title(institution_code)
    
    st.markdown("---")
    st.subheader("📖 Confirm Exam Subject")
    st.write("Please verify the exam subject before proceeding:")
    
    with st.container(border=True):
        st.markdown(f"### **📚 {subject_title if subject_title else 'Subject Not Set'}**")
        st.info(f"**Student Name:** {student_details.get('name', '')}")
        st.info(f"**Register No:** {student_details.get('reg_no', '')}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        confirm_checkbox = st.checkbox("✅ I confirm that the subject is correct and I am ready to take the exam.")
    
    with col2:
        if st.button("🔙 Back to Details", key="back_to_details"):
            st.session_state.details_submitted = False
            st.session_state.student_details = {}
            st.session_state.subject_confirmed = False
            st.rerun()
    
    if confirm_checkbox:
        if st.button("📝 Proceed to Exam", key="proceed_exam"):
            st.session_state.exam_start_time = datetime.now()
            st.session_state.subject_confirmed = True
            st.rerun()
    else:
        st.warning("Please confirm the subject to proceed.")

else:
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔙 Back to Details", key="back_to_exam"):
            st.session_state.details_submitted = False
            st.session_state.subject_confirmed = False
            st.session_state.exam_start_time = None
            st.session_state.auto_submit = False
            st.session_state.student_details = {}
            st.rerun()
    
    display_questions(st.session_state.selected_language)
