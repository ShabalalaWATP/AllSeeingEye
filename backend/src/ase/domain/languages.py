"""Language presentation and adapter capabilities, not a claim of source coverage."""

import re
from dataclasses import dataclass
from typing import Literal
from unicodedata import normalize

ReportLanguage = Literal["en", "fr", "de", "es", "ar", "fa", "ru", "uk", "zh", "zh-Hans", "zh-Hant"]
LANGUAGE_CODE_PATTERN = r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$"


@dataclass(frozen=True, slots=True)
class SearchEdition:
    hl: str
    gl: str
    ceid: str


@dataclass(frozen=True, slots=True)
class LanguageCapability:
    code: str
    label: str
    native_label: str
    direction: Literal["ltr", "rtl"] = "ltr"
    report_supported: bool = False
    pdf_supported: bool = True
    detector_code: str | None = None
    google_news_edition: SearchEdition | None = None


# An edition identifies the existing adapter's explicit regional request parameters.
# It is not an availability guarantee, a language detector or geographic evidence.
LANGUAGES: tuple[LanguageCapability, ...] = (
    LanguageCapability(
        "en",
        "English",
        "English",
        report_supported=True,
        detector_code="en",
        google_news_edition=SearchEdition("en-GB", "GB", "GB:en"),
    ),
    LanguageCapability(
        "fr",
        "French",
        "Français",
        report_supported=True,
        detector_code="fr",
        google_news_edition=SearchEdition("fr", "FR", "FR:fr"),
    ),
    LanguageCapability(
        "de",
        "German",
        "Deutsch",
        report_supported=True,
        detector_code="de",
        google_news_edition=SearchEdition("de", "DE", "DE:de"),
    ),
    LanguageCapability(
        "es",
        "Spanish",
        "Español",
        report_supported=True,
        detector_code="es",
        google_news_edition=SearchEdition("es", "ES", "ES:es"),
    ),
    LanguageCapability(
        "ar", "Arabic", "العربية", "rtl", True, False, "ar", SearchEdition("ar", "SA", "SA:ar")
    ),
    LanguageCapability("fa", "Persian", "فارسی", "rtl", True, False, "fa"),
    LanguageCapability(
        "ru",
        "Russian",
        "Русский",
        report_supported=True,
        detector_code="ru",
        google_news_edition=SearchEdition("ru", "RU", "RU:ru"),
    ),
    LanguageCapability(
        "uk",
        "Ukrainian",
        "Українська",
        report_supported=True,
        detector_code="uk",
        google_news_edition=SearchEdition("uk", "UA", "UA:uk"),
    ),
    LanguageCapability(
        "zh",
        "Chinese (unspecified script)",
        "中文",
        report_supported=True,
        pdf_supported=True,
        detector_code="zh",
    ),
    LanguageCapability(
        "zh-Hans",
        "Chinese (Simplified)",
        "简体中文",
        report_supported=True,
        pdf_supported=True,
        detector_code="zh",
    ),
    LanguageCapability(
        "zh-Hant",
        "Chinese (Traditional)",
        "繁體中文",
        report_supported=True,
        pdf_supported=True,
        detector_code="zh",
    ),
    LanguageCapability(
        "zh-CN",
        "Chinese, mainland China search edition",
        "中国大陆版",
        pdf_supported=False,
        detector_code="zh",
        google_news_edition=SearchEdition("zh-CN", "CN", "CN:zh-Hans"),
    ),
    LanguageCapability(
        "zh-TW",
        "Chinese, Taiwan search edition",
        "台灣版",
        pdf_supported=False,
        detector_code="zh",
        google_news_edition=SearchEdition("zh-TW", "TW", "TW:zh-Hant"),
    ),
    LanguageCapability(
        "pt",
        "Portuguese",
        "Português",
        detector_code="pt",
        google_news_edition=SearchEdition("pt-PT", "PT", "PT:pt-150"),
    ),
    LanguageCapability(
        "ja",
        "Japanese",
        "日本語",
        pdf_supported=False,
        detector_code="ja",
        google_news_edition=SearchEdition("ja", "JP", "JP:ja"),
    ),
    LanguageCapability(
        "ko",
        "Korean",
        "한국어",
        pdf_supported=False,
        detector_code="ko",
        google_news_edition=SearchEdition("ko", "KR", "KR:ko"),
    ),
    LanguageCapability(
        "hi",
        "Hindi",
        "हिन्दी",
        pdf_supported=False,
        detector_code="hi",
        google_news_edition=SearchEdition("hi", "IN", "IN:hi"),
    ),
    LanguageCapability("it", "Italian", "Italiano", detector_code="it"),
    LanguageCapability("nl", "Dutch", "Nederlands", detector_code="nl"),
    LanguageCapability("pl", "Polish", "Polski", detector_code="pl"),
    LanguageCapability("tr", "Turkish", "Türkçe", detector_code="tr"),
    LanguageCapability("he", "Hebrew", "עברית", "rtl", pdf_supported=False, detector_code="he"),
    LanguageCapability("ur", "Urdu", "اردو", "rtl", pdf_supported=False, detector_code="ur"),
    LanguageCapability("id", "Indonesian", "Bahasa Indonesia", detector_code="id"),
    LanguageCapability("vi", "Vietnamese", "Tiếng Việt", detector_code="vi"),
    LanguageCapability("th", "Thai", "ไทย", pdf_supported=False, detector_code="th"),
    LanguageCapability("sv", "Swedish", "Svenska", detector_code="sv"),
    LanguageCapability("el", "Greek", "Ελληνικά", detector_code="el"),
)
_BY_CODE = {language.code.lower(): language for language in LANGUAGES}


def language_capability(code: str) -> LanguageCapability | None:
    return _BY_CODE.get(code.lower())


def valid_language_code(code: str) -> bool:
    return re.fullmatch(LANGUAGE_CODE_PATTERN, code) is not None


def matching_text(value: str, language: str) -> str:
    """Create a matching key only. Never replace stored evidence or zero-width characters.

    Persian input often contains Arabic kaf/yeh. Restrict that equivalence to
    explicitly Persian records; Arabic words and Chinese scripts remain distinct.
    """
    key = normalize("NFC", value).casefold()
    if language.lower().split("-", 1)[0] == "fa":
        key = key.translate(str.maketrans("كي", "کی"))
    return key
