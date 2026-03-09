def parse_docx(file_path):
    from docx import Document
    import re

    document = Document(file_path)
    questions = []
    options_list = []
    marks = []
    correct_answers = []

    current_question = None
    current_options = []
    current_marks = None
    current_correct_answer = None

    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue  # skip empty lines
        # Match "Question:" or "Question 1:" etc.
        if re.match(r"^Question(\s*\d*)\s*:", text):
            if current_question is not None:
                questions.append(current_question)
                options_list.append(current_options if current_options else [])
                marks.append(current_marks)
                correct_answers.append(current_correct_answer)
            # Remove "Question", number, and colon
            current_question = re.sub(r"^Question(\s*\d*)\s*:", "", text).strip()
            current_options = []
            current_marks = None
            current_correct_answer = None
        elif text.startswith("Options:"):
            opts = [opt.strip() for opt in text.replace("Options:", "").split(",") if opt.strip()]
            current_options = [opt.replace("*", "") for opt in opts]
            for opt in opts:
                if opt.startswith("*") and opt.endswith("*"):
                    current_correct_answer = opt.replace("*", "")
        elif text.startswith("Marks:"):
            try:
                current_marks = int(text.replace("Marks:", "").strip())
            except:
                current_marks = 1  # Default to 1 mark if parsing fails

    # Save the last question
    if current_question is not None:
        questions.append(current_question)
        options_list.append(current_options if current_options else [])
        marks.append(current_marks)
        correct_answers.append(current_correct_answer)

    return questions, options_list, marks, correct_answers

def translate_questions(questions, target_language):
    from translator import translate_text  # Assuming translate_text is a function in translator.py

    translated_questions = []
    for question in questions:
        translated_question = translate_text(question, target_language)
        translated_questions.append(translated_question)

    return translated_questions