from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class StudentDetails:
    name: str
    registration_number: str
    year_of_admission: int
    date_of_examination: str

@dataclass
class Question:
    question_text: str
    marks: int
    translations: Dict[str, str]  # Language code to translated question text mapping

@dataclass
class StudentResponse:
    student_details: StudentDetails
    answers: List[Dict[str, Any]]  # List of answers with question ID and response
    total_marks: int