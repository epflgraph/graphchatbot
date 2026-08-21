import logging

logger = logging.getLogger(__name__)

# ISO 639-2 for "undetermined": the detector's answer
# when a turn carries no supported language.
UNDETERMINED = "und"

# The languages a bot can be instructed to reply in, ISO 639-1 code to English name.
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ro": "Romanian",
    "el": "Greek",
    "ru": "Russian",
    "uk": "Ukrainian",
    "tr": "Turkish",
    "ar": "Arabic",
    "fa": "Persian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

# What the user sees when a model call fails.
# Canned rather than generated, because the model that would generate it
# is the one that just failed; and written per language, since there is no
# working call left to translate it.
NO_ANSWER = {
    "en": "Sorry, an issue occurred while generating this response. Please try again.",
    "fr": "Désolé, une erreur s'est produite lors de la génération de cette réponse. Veuillez réessayer.",
    "de": "Entschuldigung, bei der Erstellung dieser Antwort ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
    "it": "Spiacenti, si è verificato un problema durante la generazione di questa risposta. Riprova.",
    "es": "Lo sentimos, se ha producido un error al generar esta respuesta. Inténtalo de nuevo.",
    "pt": "Lamentamos, ocorreu um erro ao gerar esta resposta. Tente novamente.",
    "nl": "Sorry, er is een probleem opgetreden bij het genereren van dit antwoord. Probeer het opnieuw.",
    "pl": "Przepraszamy, wystąpił problem podczas generowania tej odpowiedzi. Spróbuj ponownie.",
    "ro": "Ne pare rău, a apărut o problemă la generarea acestui răspuns. Încearcă din nou.",
    "el": "Λυπούμαστε, αλλά παρουσιάστηκε ένα πρόβλημα κατά τη δημιουργία αυτής της απάντησης. Δοκιμάστε ξανά.",
    "ru": "Извините, при формировании этого ответа произошла ошибка. Пожалуйста, попробуйте ещё раз.",
    "uk": "Вибачте, під час формування цієї відповіді сталася помилка. Будь ласка, спробуйте ще раз.",
    "tr": "Üzgünüz, bu yanıt oluşturulurken bir sorun oluştu. Lütfen tekrar deneyin.",
    "ar": "عذرًا، حدثت مشكلة أثناء إنشاء هذا الرد. يرجى المحاولة مرة أخرى.",
    "fa": "متأسفیم، هنگام تولید این پاسخ مشکلی رخ داد. لطفاً دوباره تلاش کنید.",
    "zh": "抱歉，生成此回复时出现问题。请再试一次。",
    "ja": "申し訳ありません。回答の生成中に問題が発生しました。もう一度お試しください。",
    "ko": "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다. 다시 시도해 주세요.",
}


def no_answer(lang_code: str | None) -> str:
    default_lang_code = "en"
    if lang_code is None:
        return NO_ANSWER[default_lang_code]

    try:
        return NO_ANSWER[lang_code]
    except KeyError:
        logger.warning("Missing NO_ANSWER entry for language %r; falling back to the English one", lang_code)
    return NO_ANSWER[default_lang_code]
