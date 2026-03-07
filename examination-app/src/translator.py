from deep_translator import GoogleTranslator

def translate_text(text, target_language):

    try:
        translated = GoogleTranslator(source='auto', target=target_language).translate(text)
        return translated
    except Exception:
        return text


def translate_questions(questions, target_languages):

    translated_questions = {}

    for lang in target_languages:

        translated_questions[lang] = [
            translate_text(question, lang) for question in questions
        ]

    return translated_questions