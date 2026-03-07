# Examination Streamlit Application

This project is an Examination application built using Streamlit. It provides an interface for both administrators and students to facilitate the examination process.

## Features

- **Admin Interface**: 
  - Upload questions in DOCX format.
  - Automatically parse questions and assign marks.
  - Translate questions into multiple languages.
  - Receive students' responses via email.

- **Student Interface**: 
  - Collect student details: Name, Registration Number, and Year of Admission.
  - Display questions after submission of details.
  - Submit answers along with student details.

## Project Structure

```
examination-app
├── src
│   ├── admin_interface.py       # Streamlit interface for admin
│   ├── student_interface.py      # Streamlit interface for students
│   ├── question_parser.py        # Functions to parse DOCX files
│   ├── translator.py             # Functions for translating questions
│   ├── email_utils.py            # Utility functions for sending emails
│   └── types
│       └── index.py              # Data types and interfaces
├── requirements.txt              # Project dependencies
└── README.md                     # Project documentation
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd examination-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   streamlit run src/admin_interface.py
   ```
   or
   ```
   streamlit run src/student_interface.py
   ```

## Usage

- **Admin**: Use the admin interface to upload questions and manage student responses.
- **Students**: Use the student interface to enter your details and answer the questions.

## Dependencies

- Streamlit
- python-docx
- Translation libraries (e.g., googletrans)

## License

This project is licensed under the MIT License.