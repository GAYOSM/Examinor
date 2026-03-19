import streamlit as st
import pandas as pd
import os
import json
from question_parser import parse_docx
from email_utils import send_whatsapp_message
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

def admin_interface():
    st.set_page_config(page_title="Examination Admin", layout="wide")
    st.title("🛡️ Examination Admin Interface")

    # --- Login ---
    if "institution_code" not in st.session_state or not st.session_state["institution_code"]:
        st.header("Admin Login")
        with st.form("institution_login"):
            institution_code = st.text_input("Institution Code")
            submitted = st.form_submit_button("Login")
            if submitted and institution_code:
                st.session_state["institution_code"] = institution_code.strip()
                with open("current_institution.txt", "w") as f:
                    f.write(st.session_state["institution_code"])
                st.rerun()
        st.stop()

    institution_code = st.session_state["institution_code"]
    st.info(f"Institution: {institution_code}")
    st.markdown("[🎓 Go to Student Interface](http://localhost:8502)")
    st_autorefresh(interval=30 * 1000, key="adminrefresh")
    st.divider()

    # --- Upload with Multi-Language Translation ---
    colA, colB = st.columns(2)
    with colA:
        st.subheader("📄 Upload Questions")
        st.caption("Upload DOCX → Auto-translate to ALL languages")
        uploaded_file = st.file_uploader("Upload Questions (DOCX)", type=["docx"])
        
        if uploaded_file is not None:
            questions, options_list, marks, correct_answers = parse_docx(uploaded_file)
            st.info("Translating to all 15 languages... (30-70 seconds)")
            
            from translator import translate_all
            target_languages = ["en","fr","de","es","hi","ml","ta","kn","te","gu","mr","bn","pa","ur","or"]
            
            with st.spinner("Translating questions & options..."):
                translated_data = translate_all(questions, options_list, target_languages)
            
            lang_folder = f"src/questions/{institution_code}"
            os.makedirs(lang_folder, exist_ok=True)
            
            for lang_code, (t_questions, t_options) in translated_data.items():
                df = pd.DataFrame({
                    "question": t_questions,
                    "options": [json.dumps(opt) for opt in t_options],
                    "original_options": [json.dumps(orig) for orig in options_list],
                    "marks": marks,
                    "correct_answer": correct_answers
                })
                df.to_csv(f"{lang_folder}/questions_{lang_code}.csv", index=False)
            
            # Master English file for admin
            df_en = pd.DataFrame({
                "question": questions,
                "options": [json.dumps(opt) for opt in options_list],
                "original_options": [json.dumps(opt) for opt in options_list],
                "marks": marks,
                "correct_answer": correct_answers
            })
            df_en.to_csv(f"src/questions/questions_{institution_code}.csv", index=False)
            
            st.success(f"✅ Questions uploaded and translated into {len(target_languages)} languages!")

    with colB:
        st.subheader("📲 WhatsApp Share")
        st.caption("Send a summary of student responses to a WhatsApp number.")
        phone_number = st.text_input("Recipient WhatsApp Number (with country code, e.g., 91XXXXXXXXXX)")
        responses_file = f"src/responses_{institution_code}.csv"
        if os.path.isfile(responses_file):
            df = pd.read_csv(responses_file, on_bad_lines='skip')
            if st.button("Generate WhatsApp Message Link"):
                if phone_number:
                    send_whatsapp_message(phone_number, df)
                    st.info("Click the link above to open WhatsApp and send the message.")
                else:
                    st.warning("Please enter a WhatsApp number.")
        else:
            st.info("No student responses to send.")

    st.divider()

    # --- All your original expanders and functions (unchanged) ---
    with st.expander("❓ Uploaded Questions", expanded=False):
        questions_file = f"src/questions/questions_{institution_code}.csv"
        if os.path.isfile(questions_file):
            questions_df = pd.read_csv(questions_file)
            st.write(f"Total Questions: {len(questions_df)}")
            for i, row in questions_df.iterrows():
                options = json.loads(row["options"])
                correct = row["correct_answer"]
                st.markdown(f"**Q{i+1}:** {row['question']} _(Marks: {row['marks']})_")
                if options:
                    option_strs = []
                    for opt in options:
                        if str(opt).strip().lower() == str(correct).strip().lower():
                            option_strs.append(f":green[**{opt}**]")
                        else:
                            option_strs.append(opt)
                    st.markdown("Options: " + ", ".join(option_strs))
                st.markdown("---")
            st.download_button("⬇️ Download Questions as CSV", data=questions_df.to_csv(index=False).encode('utf-8'), file_name="questions.csv", mime="text/csv")
        else:
            st.info("No questions uploaded yet.")

    # Student Responses, Marks Summary, PDF sections (paste your original code here - it is unchanged)
    # ... (your original code for these expanders and def save_student_response_pdf stays exactly as it was)

    # (For space, I kept only the structure - copy the rest from your current admin file if you want)

if __name__ == "__main__":
    admin_interface()