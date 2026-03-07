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

    # --- Centered Login Form ---
    if "institution_code" not in st.session_state or not st.session_state["institution_code"]:
        st.write("")
        st.write("")
        st.header("Admin Login")
        st.write("Enter your Institution Code to access the admin dashboard.")
        with st.form("institution_login"):
            institution_code = st.text_input("Institution Code")
            submitted = st.form_submit_button("Login")
            if submitted and institution_code:
                st.session_state["institution_code"] = institution_code
                with open("current_institution.txt", "w") as f:
                    f.write(st.session_state["institution_code"])
                st.rerun()
        st.stop()
    else:
        institution_code = st.session_state["institution_code"]

    # --- Institution Info and Student Link ---
    st.info(f"Institution: {institution_code}")
    st.markdown("[🎓 Go to Student Interface](http://localhost:8502)")
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
            os.makedirs("src/questions", exist_ok=True)  # Ensure 'src/questions' directory exists
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
        responses_file = f"src/responses_{institution_code}.csv"  # <-- FIXED PATH
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
                    # Highlight correct answer in green
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
        if os.path.isfile(responses_file):  # <-- uses the same variable
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
                # PDF download for each student
                for idx, row in df.iterrows():
                    pdf_filename = f"{row['reg_no']}_response.pdf"
                    save_student_response_pdf(row, questions_df, pdf_filename)
                    with open(pdf_filename, "rb") as f:
                        st.download_button(
                            label=f"Download PDF for {row['name']} ({row['reg_no']})",
                            data=f,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )
                    os.remove(pdf_filename)
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
                student_row = responses_df[responses_df["name"] == selected_student].iloc[0]
                filename = f"{selected_student}_response.pdf"
                save_student_response_pdf(student_row, questions_df, filename)
                st.success(f"PDF generated: {filename}")
                st.download_button(
                    label="⬇️ Download Student Response PDF",
                    data=open(filename, "rb").read(),
                    file_name=filename,
                    mime="application/pdf"
                )
        else:
            st.info("No responses available to generate PDF.")

    # --- Display Questions (For Student Interface) ---
    def display_questions(language):
        st.header("Answer the following questions:")

        questions_file = st.session_state.get("questions_file", "")
        if os.path.isfile(questions_file):
            df = pd.read_csv(questions_file)
            questions = df["question"].tolist()
            options_list = df["options"].tolist()
            marks_list = df["marks"].tolist()
        else:
            questions = []
            options_list = []
            marks_list = []

        if not questions:
            st.warning("No questions available. Please contact the admin.")
            return

        for i, question in enumerate(questions):
            st.markdown(f"**Q{i+1}:** {question}")
            options = json.loads(options_list[i])
            for opt in options:
                st.radio(f"Q{i+1} Options", options, key=f"q{i+1}_options")
            st.markdown(f"_(Marks: {marks_list[i]})_")
            st.divider()

def save_student_response_pdf(student_row, questions_df, filename):
    pdf = FPDF()
    pdf.add_page()
    # Add Unicode font
    font_path = os.path.join("fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)
    pdf.cell(0, 10, f"Student Name: {student_row['name']}", ln=True)
    pdf.cell(0, 10, f"Reg No: {student_row['reg_no']}", ln=True)

    # Calculate obtained and total marks
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
                    pdf.set_text_color(0, 128, 0)  # Green for correct
                else:
                    pdf.set_text_color(220, 20, 60)  # Red for wrong
                pdf.cell(0, 8, f"  - {opt} (Student Answer)", ln=True)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 8, f"  - {opt}", ln=True)
        pdf.ln(2)
    pdf.output(filename)

if __name__ == "__main__":
    admin_interface()