"""
Language codes and names for user selection
Based on Whisper supported languages
"""
from typing import Dict, List, Tuple


class Languages:
    """Language codes and display names for UI selection"""
    
    # All languages supported by Whisper with display names
    ALL_LANGUAGES: Dict[str, str] = {
        # Indian Languages
        'te': 'Telugu (తెలుగు)',
        'hi': 'Hindi (हिंदी)',
        'ta': 'Tamil (தமிழ்)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'gu': 'Gujarati (ગુજરાતી)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)',
        'bn': 'Bengali (বাংলা)',
        'mr': 'Marathi (मराठी)',
        'or': 'Odia (ଓଡ଼ିଆ)',
        'as': 'Assamese (অসমীয়া)',
        
        # European Languages
        'en': 'English',
        'de': 'German (Deutsch)',
        'fr': 'French (Français)',
        'es': 'Spanish (Español)',
        'it': 'Italian (Italiano)',
        'pt': 'Portuguese (Português)',
        'nl': 'Dutch (Nederlands)',
        'ru': 'Russian (Русский)',
        'pl': 'Polish (Polski)',
        'uk': 'Ukrainian (Українська)',
        'cs': 'Czech (Čeština)',
        'sv': 'Swedish (Svenska)',
        'no': 'Norwegian (Norsk)',
        'fi': 'Finnish (Suomi)',
        'da': 'Danish (Dansk)',
        'el': 'Greek (Ελληνικά)',
        'hu': 'Hungarian (Magyar)',
        'ro': 'Romanian (Română)',
        'bg': 'Bulgarian (Български)',
        'hr': 'Croatian (Hrvatski)',
        'sk': 'Slovak (Slovenčina)',
        'sl': 'Slovenian (Slovenščina)',
        'sr': 'Serbian (Српски)',
        
        # Asian Languages
        'zh': 'Chinese (中文)',
        'ja': 'Japanese (日本語)',
        'ko': 'Korean (한국어)',
        'ar': 'Arabic (العربية)',
        'th': 'Thai (ไทย)',
        'vi': 'Vietnamese (Tiếng Việt)',
        'id': 'Indonesian (Bahasa Indonesia)',
        'ms': 'Malay (Bahasa Melayu)',
        'tl': 'Filipino (Tagalog)',
        'tr': 'Turkish (Türkçe)',
        'he': 'Hebrew (עברית)',
        'fa': 'Persian (فارسی)',
        'ur': 'Urdu (اردو)',
        
        # Other Languages
        'af': 'Afrikaans',
        'sq': 'Albanian (Shqip)',
        'am': 'Amharic (አማርኛ)',
        'az': 'Azerbaijani (Azərbaycan)',
        'eu': 'Basque (Euskara)',
        'be': 'Belarusian (Беларуская)',
        'bs': 'Bosnian (Bosanski)',
        'br': 'Breton (Brezhoneg)',
        'ca': 'Catalan (Català)',
        'cy': 'Welsh (Cymraeg)',
        'et': 'Estonian (Eesti)',
        'ga': 'Irish (Gaeilge)',
        'gl': 'Galician (Galego)',
        'ka': 'Georgian (ქართული)',
        'is': 'Icelandic (Íslenska)',
        'lv': 'Latvian (Latviešu)',
        'lt': 'Lithuanian (Lietuvių)',
        'lb': 'Luxembourgish (Lëtzebuergesch)',
        'mk': 'Macedonian (Македонски)',
        'mt': 'Maltese (Malti)',
        'mi': 'Maori (Te Reo Māori)',
        'ne': 'Nepali (नेपाली)',
        'nn': 'Norwegian Nynorsk',
        'oc': 'Occitan',
        'ps': 'Pashto (پښتو)',
        'rm': 'Romansh',
        'sn': 'Shona (ChiShona)',
        'sd': 'Sindhi (سنڌي)',
        'si': 'Sinhala (සිංහල)',
        'so': 'Somali (Soomaali)',
        'sw': 'Swahili (Kiswahili)',
        'tg': 'Tajik (Тоҷикӣ)',
        'tt': 'Tatar (Татар)',
        'uz': 'Uzbek (Oʻzbek)',
        'yi': 'Yiddish (ייִדיש)',
        'yo': 'Yoruba (Yorùbá)',
        'zu': 'Zulu (isiZulu)',
    }
    
    # Popular languages (for quick selection)
    POPULAR_LANGUAGES: List[Tuple[str, str]] = [
        ('en', 'English'),
        ('hi', 'Hindi (हिंदी)'),
        ('te', 'Telugu (తెలుగు)'),
        ('ta', 'Tamil (தமிழ்)'),
        ('kn', 'Kannada (ಕನ್ನಡ)'),
        ('ml', 'Malayalam (മലയാളം)'),
        ('bn', 'Bengali (বাংলা)'),
        ('mr', 'Marathi (मराठी)'),
        ('gu', 'Gujarati (ગુજરાતી)'),
        ('pa', 'Punjabi (ਪੰਜਾਬੀ)'),
        ('zh', 'Chinese (中文)'),
        ('ja', 'Japanese (日本語)'),
        ('ko', 'Korean (한국어)'),
        ('ar', 'Arabic (العربية)'),
        ('de', 'German (Deutsch)'),
        ('fr', 'French (Français)'),
        ('es', 'Spanish (Español)'),
        ('it', 'Italian (Italiano)'),
        ('pt', 'Portuguese (Português)'),
        ('ru', 'Russian (Русский)'),
    ]
    
    # Auto-detect option
    AUTO_DETECT = ('auto', 'Auto-detect (slower)')
    
    @classmethod
    def get_language_name(cls, code: str) -> str:
        """Get display name for language code"""
        return cls.ALL_LANGUAGES.get(code, code.upper())
    
    @classmethod
    def get_all_languages_sorted(cls) -> List[Tuple[str, str]]:
        """Get all languages sorted by name"""
        return sorted(cls.ALL_LANGUAGES.items(), key=lambda x: x[1])
    
    @classmethod
    def get_popular_languages(cls) -> List[Tuple[str, str]]:
        """Get popular languages list"""
        return cls.POPULAR_LANGUAGES
    
    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """Check if language code is valid"""
        return code == 'auto' or code in cls.ALL_LANGUAGES
    
    @classmethod
    def get_language_for_ui(cls) -> List[Tuple[str, str]]:
        """Get languages formatted for UI dropdown"""
        # Return popular + auto-detect, then all others
        result = [cls.AUTO_DETECT]
        result.extend(cls.POPULAR_LANGUAGES)
        
        # Add separator and remaining languages
        remaining = [
            (code, name) for code, name in cls.get_all_languages_sorted()
            if (code, name) not in cls.POPULAR_LANGUAGES
        ]
        if remaining:
            result.append(('---', '--- Other Languages ---'))
            result.extend(remaining)
        
        return result
