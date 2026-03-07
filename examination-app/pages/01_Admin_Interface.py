import streamlit as st
import pandas as pd
import os
import json
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from question_parser import parse_docx
from email_utils import send_whatsapp_message
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

st.set_page_config(page_title="Examination Admin", layout="wide")
st.title("🛡️ Examination Admin Interface")

# --- Per-Institution Password Management ---
ADMIN_PASSWORDS_FILE = "admin_passwords.json"

def load_admin_passwords():
    """Load all institution passwords from JSON file."""
    if os.path.isfile(ADMIN_PASSWORDS_FILE):
        try:
            with open(ADMIN_PASSWORDS_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_admin_passwords(passwords_dict):
    """Save all institution passwords to JSON file."""
    with open(ADMIN_PASSWORDS_FILE, "w") as f:
        json.dump(passwords_dict, f, indent=4)

def get_admin_password(institution_code):
    """Get password for a specific institution. Return default if new institution."""
    passwords = load_admin_passwords()
    return passwords.get(institution_code, "admin123")

def is_institution_exists(institution_code):
    """Check if institution code has been registered."""
    passwords = load_admin_passwords()
    return institution_code in passwords

def set_admin_password(institution_code, password):
    """Save password for a specific institution."""
    passwords = load_admin_passwords()
    passwords[institution_code] = password
    save_admin_passwords(passwords)

# --- Centered Login Form ---
if "admin_logged_in" not in st.session_state or not st.session_state["admin_logged_in"]:
    st.write("")
    st.write("")
    st.header("🔐 Admin Login")
    st.write("Enter your credentials to access the admin dashboard.")
    
    with st.form("institution_login"):
        institution_code = st.text_input("Institution Code")
        admin_password = st.text_input("Admin Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not institution_code:
                st.error("❌ Please enter Institution Code")
            elif not admin_password:
                st.error("❌ Please enter Admin Password")
            else:
                institution_code_clean = institution_code.strip()
                
                if is_institution_exists(institution_code_clean):
                    # Existing institution - check password
                    if admin_password != get_admin_password(institution_code_clean):
                        st.error("❌ Invalid Admin Password")
                    else:
                        st.session_state["admin_logged_in"] = True
                        st.session_state["institution_code"] = institution_code_clean
                        with open("current_institution.txt", "w") as f:
                            f.write(institution_code_clean)
                        st.success("✅ Login successful!")
                        st.rerun()
                else:
                    # New institution - create with default password
                    if admin_password == "admin123":
                        set_admin_password(institution_code_clean, "admin123")
                        st.session_state["admin_logged_in"] = True
                        st.session_state["institution_code"] = institution_code_clean
                        with open("current_institution.txt", "w") as f:
                            f.write(institution_code_clean)
                        st.success("✅ New institution created! Login successful!")
                        st.info("ℹ️ Default password 'admin123' is active. Please change it in the settings.")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Admin Password. For new institution, use default password: admin123")
    
    # Show password reset option
    st.markdown("---")
    with st.expander("🔑 Change Admin Password"):
        st.write("**Change password for your institution code:**")
        change_inst_code = st.text_input("Institution Code", key="change_inst_code")
        current_pass = st.text_input("Current Password", type="password", key="current_pass")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="confirm_pass")
        
        if st.button("Update Password"):
            change_inst_code = change_inst_code.strip()
            
            if not change_inst_code:
                st.error("Enter your Institution Code")
            elif not is_institution_exists(change_inst_code):
                st.error(f"Institution code '{change_inst_code}' not found. Please login first to register.")
            elif not current_pass:
                st.error("Enter current password")
            elif current_pass != get_admin_password(change_inst_code):
                st.error("Current password is incorrect")
            elif not new_pass or not confirm_pass:
                st.error("Enter new password in both fields")
            elif new_pass != confirm_pass:
                st.error("Passwords don't match")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters")
            else:
                set_admin_password(change_inst_code, new_pass)
                st.success(f"✅ Password updated successfully for institution '{change_inst_code}'!")
    
    st.stop()
else:
    institution_code = st.session_state["institution_code"]

# --- Institution Info and Student Link ---
st.info(f"Institution: {institution_code}")
col1, col2 = st.columns(2)
with col1:
    if st.button("🎓 Go to Student Interface"):
        st.switch_page("pages/02_Student_Interface.py")
with col2:
    if st.button("🚪 Logout"):
        st.session_state["admin_logged_in"] = False
        st.session_state["institution_code"] = ""
        st.rerun()

st_autorefresh(interval=30 * 1000, key="adminrefresh")
st.divider()

# --- Top row: Upload Questions | WhatsApp Share ---
colA, colB = st.columns(2)
with colA:
    st.subheader("📄 Upload Questions")
    st.caption("Upload your exam questions in DOCX format. The file should include questions, options, marks, and correct answers.")
    uploaded_file = st.file_uploader("Upload Questions (DOCX)", type=["docx"])
    if uploaded_file is not None:
        questions, options_list, marks, correct_answers = parse_docx(uploaded_file)
        os.makedirs("src/questions", exist_ok=True)
        pd.DataFrame({
            "question": questions,
            "options": [json.dumps(opt if opt is not None else []) for opt in options_list],
            "marks": marks,
            "correct_answer": correct_answers
        }).to_csv(f"src/questions/questions_{institution_code}.csv", index=False)
        st.success("✅ Questions uploaded successfully!")

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

# --- Uploaded Questions (Expander) ---
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
        st.download_button(
            label="⬇️ Download Questions as CSV",
            data=questions_df.to_csv(index=False).encode('utf-8'),
            file_name="questions.csv",
            mime="text/csv"
        )
        if st.button("🗑️ Clear All Questions"):
            st.session_state.show_confirm_delete_questions = True

        if st.session_state.get("show_confirm_delete_questions", False):
            st.warning("This will delete all questions for this institution. This action cannot be undone.")
            colA1, colB1 = st.columns(2)
            with colA1:
                if st.button("✅ Confirm Delete Questions"):
                    os.remove(questions_file)
                    st.success("All questions have been cleared.")
                    st.session_state.show_confirm_delete_questions = False
                    st.rerun()
            with colB1:
                if st.button("❌ Cancel"):
                    st.session_state.show_confirm_delete_questions = False
    else:
        st.info("No questions uploaded yet.")

# --- Student Responses (Expander) ---
with st.expander("📝 Student Responses", expanded=False):
    if os.path.isfile(responses_file):
        try:
            df = pd.read_csv(responses_file, on_bad_lines='skip')
            questions_df = pd.read_csv(questions_file)
            student_count = len(df)
            st.write(f"👥 Students Submitted: {student_count}")
            st.dataframe(df, use_container_width=True, height=300)
            st.download_button(
                label="⬇️ Download Responses as CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="responses.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"Error reading responses.csv: {e}")

        if st.button("🗑️ Clear All Responses"):
            st.session_state.show_confirm_delete = True

        if st.session_state.get("show_confirm_delete", False):
            st.warning("This will delete all responses for this institution. This action cannot be undone.")
            colA2, colB2 = st.columns(2)
            with colA2:
                if st.button("✅ Confirm Delete"):
                    os.remove(responses_file)
                    st.success("All responses have been cleared.")
                    st.session_state.show_confirm_delete = False
                    st.rerun()
            with colB2:
                if st.button("❌ Cancel"):
                    st.session_state.show_confirm_delete = False
    else:
        st.info("No student responses yet.")

# --- Student Marks Summary (Expander) ---
with st.expander("📊 Student Marks Summary", expanded=False):
    if os.path.isfile(f"src/questions/questions_{institution_code}.csv") and os.path.isfile(responses_file):
        questions_df = pd.read_csv(f"src/questions/questions_{institution_code}.csv")
        responses_df = pd.read_csv(responses_file)

        def calculate_score(row):
            score = 0
            for idx, correct in enumerate(questions_df["correct_answer"]):
                student_answer = row.get(f"answer_{idx}", "")
                if pd.notna(correct) and str(student_answer).strip().lower() == str(correct).strip().lower():
                    score += questions_df["marks"][idx]
            return score

        responses_df["Total Marks"] = responses_df.apply(calculate_score, axis=1)
        st.dataframe(responses_df[["name", "reg_no", "Total Marks"]], use_container_width=True, height=300)
    else:
        st.info("Marks summary will appear after questions and responses are available.")

# --- Student Response PDF (Button) ---
with st.expander("📑 Generate Student Response PDF", expanded=False):
    if os.path.isfile(responses_file):
        responses_df = pd.read_csv(responses_file, on_bad_lines='skip')
        student_names = responses_df["name"].unique()
        selected_student = st.selectbox("Select a student", options=student_names)
        
        if st.button("Generate PDF"):
            def save_student_response_pdf(student_row, questions_df, filename):
                pdf = FPDF()
                pdf.add_page()
                try:
                    font_path = os.path.join("src", "fonts", "dejavu-sans", "ttf", "DejaVuSans.ttf")
                    if os.path.exists(font_path):
                        pdf.add_font("DejaVu", "", font_path, uni=True)
                        pdf.set_font("DejaVu", size=12)
                    else:
                        pdf.set_font("Arial", size=12)
                except:
                    pdf.set_font("Arial", size=12)
                
                pdf.cell(0, 10, f"Student Name: {student_row['name']}", ln=True)
                pdf.cell(0, 10, f"Reg No: {student_row['reg_no']}", ln=True)

                obtained = 0
                total = 0
                for idx, q_row in questions_df.iterrows():
                    correct = str(q_row["correct_answer"]).strip().lower()
                    student_answer = str(student_row.get(f"answer_{idx}", "")).strip().lower()
                    marks = q_row["marks"]
                    total += marks
                    if pd.notna(correct) and student_answer == correct:
                        obtained += marks

                pdf.cell(0, 10, f"Marks Obtained: {obtained} / {total}", ln=True)
                pdf.ln(5)

                for idx, q_row in questions_df.iterrows():
                    question = q_row["question"]
                    options = json.loads(q_row["options"])
                    correct = str(q_row["correct_answer"]).strip().lower()
                    student_answer = str(student_row.get(f"answer_{idx}", "")).strip().lower()

                    pdf.set_text_color(0, 0, 0)
                    pdf.multi_cell(0, 8, f"Q{idx+1}: {question} (Marks: {q_row['marks']})")
                    for opt in options:
                        opt_str = str(opt).strip().lower()
                        if opt_str == student_answer:
                            if opt_str == correct:
                                pdf.set_text_color(0, 128, 0)
                            else:
                                pdf.set_text_color(220, 20, 60)
                            pdf.cell(0, 8, f"  - {opt} (Student Answer)", ln=True)
                        else:
                            pdf.set_text_color(0, 0, 0)
                            pdf.cell(0, 8, f"  - {opt}", ln=True)
                    pdf.ln(2)
                pdf.output(filename)

            student_row = responses_df[responses_df["name"] == selected_student].iloc[0]
            filename = f"{selected_student}_response.pdf"
            save_student_response_pdf(student_row, questions_df, filename)
            st.success(f"PDF generated: {filename}")
            with open(filename, "rb") as f:
                st.download_button(
                    label="⬇️ Download Student Response PDF",
                    data=f.read(),
                    file_name=filename,
                    mime="application/pdf"
                )
    else:
        st.info("No responses available to generate PDF.")
