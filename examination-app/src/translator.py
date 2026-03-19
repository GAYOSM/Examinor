from deep_translator import GoogleTranslator
import time

def translate_text(text, target_language):
    if not text or target_language == "en":
        return str(text).strip()
    try:
        time.sleep(0.7)  # prevents Google rate limit
        return GoogleTranslator(source='auto', target=target_language).translate(str(text))
    except:
        return str(text).strip()

def translate_all(questions, options_list, target_languages):
    result = {}
    for lang in target_languages:
        t_questions = [translate_text(q, lang) for q in questions]
        t_options = [[translate_text(opt, lang) for opt in opts] if opts else [] for opts in options_list]
        result[lang] = (t_questions, t_options)
    return result