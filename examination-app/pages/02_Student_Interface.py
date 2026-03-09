import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
import sys
import json
from streamlit_autorefresh import st_autorefresh
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

# time limit helpers duplicated here since admin file isn't imported
TIME_LIMITS_FILE = "time_limits.json"

def normalize_limit_entry(entry):
    if isinstance(entry, dict):
        return {"enabled": entry.get("enabled", True), "minutes": entry.get("minutes", 60)}
    else:
        try:
            mins = int(entry)
        except Exception:
            mins = 60
        return {"enabled": True, "minutes": mins}


def load_time_limits():
    if os.path.isfile(TIME_LIMITS_FILE):
        try:
            with open(TIME_LIMITS_FILE) as f:
                raw = json.load(f)
                return {k: normalize_limit_entry(v) for k, v in raw.items()}
        except:
            return {}
    return {}


def get_time_limit_data(institution_code):
    limits = load_time_limits()
    return limits.get(institution_code, {"enabled": False, "minutes": 60})


def save_partial_answers(institution_code, reg_no, answers, exam_start_time=None):
    """Save student's partial answers to a JSON file."""
    os.makedirs("src/partial_answers", exist_ok=True)
    filename = f"src/partial_answers/{institution_code}_{reg_no}.json"
    
    # Handle both datetime objects and ISO strings
    if exam_start_time is None:
        start_time_iso = None
    elif isinstance(exam_start_time, str):
        start_time_iso = exam_start_time
    else:
        start_time_iso = exam_start_time.isoformat()
    
    data = {
        "answers": answers,
        "exam_start_time": start_time_iso,
        "last_saved": datetime.now().isoformat()
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_partial_answers(institution_code, reg_no):
    """Load student's partial answers from JSON file."""
    filename = f"src/partial_answers/{institution_code}_{reg_no}.json"
    
    if not os.path.isfile(filename):
        return None
    
    try:
        with open(filename) as f:
            data = json.load(f)
        
        # Parse exam_start_time back to datetime
        if data.get("exam_start_time"):
            data["exam_start_time"] = datetime.fromisoformat(data["exam_start_time"])
        
        return data
    except:
        return None


def clear_partial_answers(institution_code, reg_no):
    """Remove partial answers file after submission."""
    filename = f"src/partial_answers/{institution_code}_{reg_no}.json"
    if os.path.isfile(filename):
        os.remove(filename)


def submit_responses(auto_submit=False):
    """Collect answers from session and write to CSV, then clear state."""
    student_details = st.session_state.get("student_details", {})
    responses_file = st.session_state.get("responses_file", "")
    institution_code = student_details.get("institution_code", "")
    reg_no = student_details.get("reg_no", "")
    
    # gather answers stored in session state
    answers = {}
    for key, val in st.session_state.items():
        if key.startswith("answer_"):
            answers[key] = val

    response = {
        "name": student_details.get("name", ""),
        "reg_no": reg_no,
        "year": student_details.get("year", ""),
        "date": student_details.get("date", ""),
        "institution_code": institution_code,
        "submission_type": "auto-submitted" if auto_submit else "manual",
        "selected_language": st.session_state.get("selected_language", "en")
    }
    response.update(answers)

    df = pd.DataFrame([response])
    if os.path.isfile(responses_file):
        df.to_csv(responses_file, mode="a", header=False, index=False)
    else:
        df.to_csv(responses_file, index=False)

    # Clear partial answers after submission
    clear_partial_answers(institution_code, reg_no)

    if auto_submit:
        st.success("✅ Time limit reached; your answers have been auto-submitted.")
        st.info("Redirecting back to login...")
    else:
        st.success("✅ Your answers have been submitted successfully!")

    # reset session
    st.session_state.details_submitted = False
    st.session_state.subject_confirmed = False
    st.session_state.exam_start_time = None
    st.session_state.auto_submit = False
    st.session_state.student_details = {}

    # navigate
    if auto_submit:
        st.experimental_rerun()
    else:
        st.stop()

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
    reg_no = student_details.get("reg_no", "")
    lim_data = get_time_limit_data(institution_code)
    time_limit_minutes = lim_data.get("minutes", 60)
    time_limit_active = lim_data.get("enabled", False)
    exam_start_time_str = st.session_state.get("exam_start_time")
    exam_start_time = datetime.fromisoformat(exam_start_time_str) if exam_start_time_str else None

    if not questions_file or not os.path.isfile(questions_file):
        st.error("Questions file not found. Please contact your administrator.")
        return

    # Load partial answers if resuming
    partial_data = load_partial_answers(institution_code, reg_no)
    if partial_data and not exam_start_time:
        # Resuming exam - restore start time and answers
        saved_start_time = partial_data.get("exam_start_time")
        if saved_start_time:
            st.session_state.exam_start_time = saved_start_time.isoformat()
            exam_start_time = saved_start_time
            st.info("📝 Resuming your previous exam session...")
        
        # Restore saved answers to session state (translate back to student's language)
        saved_answers = partial_data.get("answers", {})
        for key, value in saved_answers.items():
            if key.startswith("answer_"):
                # Translate English answer back to student's language for display
                if language_code != "en" and value.strip():
                    try:
                        # For multiple choice, find the translated option that maps to this English answer
                        question_idx = int(key.split('_')[1])
                        if question_idx < len(options_list) and pd.notna(options_list[question_idx]):
                            original_options = json.loads(options_list[question_idx])
                            translated_opts = translated_options_list[question_idx]
                            option_map_reverse = dict(zip(original_options, translated_opts))
                            if value in option_map_reverse:
                                st.session_state[key] = option_map_reverse[value]
                            else:
                                st.session_state[key] = value
                        else:
                            # For text input, translate back to student's language
                            translated_back = GoogleTranslator(source='en', target=language_code).translate(value)
                            st.session_state[key] = translated_back
                    except Exception:
                        st.session_state[key] = value  # Fallback to saved value
                else:
                    st.session_state[key] = value

    # --- Timer Display and Auto-Submit Logic ---
    if exam_start_time and time_limit_active:
        # schedule periodic rerun so timer updates and triggers auto-submission
        st_autorefresh(interval=1 * 1000, key="student_timer_refresh")

        elapsed_time = datetime.now() - exam_start_time
        total_seconds = int(time_limit_minutes * 60)
        elapsed_seconds = int(elapsed_time.total_seconds())
        remaining_seconds = max(0, total_seconds - elapsed_seconds)

        # if time expired, immediately perform submission and return early
        if remaining_seconds <= 0:
            submit_responses(auto_submit=True)
            return

        # Convert remaining seconds to minutes and seconds
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60

        # Display timer at the top using a placeholder
        timer_placeholder = st.empty()
        with timer_placeholder.container():
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

            # Map back to English for saving
            answer = option_map[selected_translated] if selected_translated else ""
        else:
            # For text input questions, get the input and translate to English for saving
            text_answer = st.text_input(label, key=f"answer_{idx}")
            if language_code != "en" and text_answer.strip():
                try:
                    answer = GoogleTranslator(source=language_code, target='en').translate(text_answer)
                except Exception:
                    answer = text_answer  # Fallback to original if translation fails
            else:
                answer = text_answer

        answers.append(answer)

    # Save partial answers periodically (every few seconds when timer is active)
    if exam_start_time:
        # Save the translated answers (in English) instead of raw session state
        save_partial_answers(institution_code, reg_no, answers, exam_start_time)

    confirm = st.checkbox("I confirm that I have answered all the questions.")

    if st.button("Submit Answers", disabled=not confirm):
        submit_responses(auto_submit=False)
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
                    # Check for partial answers
                    partial_data = load_partial_answers(code_clean, reg_no)
                    has_partial = partial_data is not None and partial_data.get("answers")

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
                    st.session_state.has_partial_answers = has_partial

                    st.success("Details submitted successfully!")

                    st.rerun()

elif not st.session_state.subject_confirmed:
    # --- Subject Confirmation Page ---
    student_details = st.session_state.get("student_details", {})
    institution_code = student_details.get("institution_code", "")
    subject_title = get_subject_title(institution_code)
    has_partial = st.session_state.get("has_partial_answers", False)
    
    st.markdown("---")
    if has_partial:
        st.subheader("📝 Resume or Restart Exam")
        st.write("You have a previous exam session in progress. Choose how to proceed:")
    else:
        st.subheader("📖 Confirm Exam Subject")
        st.write("Please verify the exam subject before proceeding:")
    
    with st.container(border=True):
        st.markdown(f"### **📚 {subject_title if subject_title else 'Subject Not Set'}**")
        st.info(f"**Student Name:** {student_details.get('name', '')}")
        st.info(f"**Register No:** {student_details.get('reg_no', '')}")
        if has_partial:
            st.info("📋 **Previous session found** - You can resume where you left off or start fresh.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if has_partial:
            exam_option = st.radio(
                "Choose your option:",
                ["📝 Resume previous exam", "🔄 Start fresh exam"],
                key="exam_option"
            )
            confirm_checkbox = st.checkbox("✅ I confirm my choice and am ready to proceed.")
        else:
            confirm_checkbox = st.checkbox("✅ I confirm that the subject is correct and I am ready to take the exam.")
    
    with col2:
        if st.button("🔙 Back to Details", key="back_to_details"):
            st.session_state.details_submitted = False
            st.session_state.student_details = {}
            st.session_state.subject_confirmed = False
            st.session_state.has_partial_answers = False
            st.rerun()
    
    if confirm_checkbox:
        if has_partial and exam_option == "🔄 Start fresh exam":
            # Clear partial answers and start fresh
            clear_partial_answers(institution_code, student_details.get("reg_no", ""))
            st.session_state.exam_start_time = datetime.now().isoformat()
            st.session_state.subject_confirmed = True
            st.success("Starting fresh exam...")
            st.rerun()
        elif st.button("📝 Proceed to Exam", key="proceed_exam"):
            # Either resuming or starting new exam
            if has_partial and exam_option == "📝 Resume previous exam":
                # Resuming - exam_start_time will be loaded from partial data
                pass
            else:
                # Fresh exam - set start time now
                st.session_state.exam_start_time = datetime.now().isoformat()
            st.session_state.subject_confirmed = True
            st.rerun()
    else:
        if has_partial:
            st.warning("Please choose an option and confirm to proceed.")
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
            st.session_state.has_partial_answers = False
            st.session_state.student_details = {}
            st.rerun()
    
    display_questions(st.session_state.selected_language)
