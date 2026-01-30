"""
Output quality validation module
Detects corrupted, repetitive, or low-quality transcriptions
"""
import re
from typing import Dict, List, Optional, Tuple
from unicodedata import category


class QualityValidator:
    """Validate transcription output quality"""
    
    # Unicode ranges for various scripts
    UNICODE_SCRIPTS = {
        'telugu': (0x0C00, 0x0C7F),
        'devanagari': (0x0900, 0x097F),  # Hindi, Marathi
        'tamil': (0x0B80, 0x0BFF),
        'kannada': (0x0C80, 0x0CFF),
        'malayalam': (0x0D00, 0x0D7F),
        'gujarati': (0x0A80, 0x0AFF),
        'gurmukhi': (0x0A00, 0x0A7F),  # Punjabi
        'bengali': (0x0980, 0x09FF),
        'odia': (0x0B00, 0x0B7F),
        'chinese': (0x4E00, 0x9FFF),
        'japanese_hiragana': (0x3040, 0x309F),
        'japanese_katakana': (0x30A0, 0x30FF),
        'korean': (0xAC00, 0xD7AF),
        'arabic': (0x0600, 0x06FF),
        'thai': (0x0E00, 0x0E7F),
        'cyrillic': (0x0400, 0x04FF),  # Russian, etc.
    }
    
    @classmethod
    def validate(
        cls,
        text: str,
        language: Optional[str] = None,
        compression_ratio: Optional[float] = None,
        segments: Optional[List[Dict]] = None
    ) -> Tuple[bool, Dict]:
        """
        Validate transcription output quality
        
        Args:
            text: Transcribed text
            language: Detected or specified language code
            compression_ratio: Whisper compression ratio (if available)
            segments: Whisper segments (if available)
            
        Returns:
            Tuple of (is_valid, quality_report)
        """
        report = {
            'is_valid': True,
            'quality_score': 100,
            'errors': [],
            'warnings': [],
            'issues': {
                'repetition': False,
                'corrupted_unicode': False,
                'missing_boundaries': False,
                'wrong_script': False,
                'low_confidence': False
            }
        }
        
        if not text or len(text.strip()) < 3:
            report['is_valid'] = False
            report['errors'].append("Transcription is empty or too short")
            report['quality_score'] = 0
            return False, report
        
        # Check 1: Repetition detection
        repetition_issues = cls._detect_repetition(text, compression_ratio)
        if repetition_issues['has_repetition']:
            report['issues']['repetition'] = True
            report['warnings'].extend(repetition_issues['warnings'])
            report['quality_score'] -= 30
            if repetition_issues['severity'] == 'critical':
                report['errors'].extend(repetition_issues['errors'])
                report['is_valid'] = False
        
        # Check 2: Corrupted Unicode patterns
        unicode_issues = cls._detect_corrupted_unicode(text)
        if unicode_issues['has_corruption']:
            report['issues']['corrupted_unicode'] = True
            report['warnings'].extend(unicode_issues['warnings'])
            report['quality_score'] -= 25
            if unicode_issues['severity'] == 'critical':
                report['errors'].extend(unicode_issues['errors'])
                report['is_valid'] = False
        
        # Check 3: Missing sentence boundaries
        boundary_issues = cls._detect_missing_boundaries(text)
        if boundary_issues['has_issues']:
            report['issues']['missing_boundaries'] = True
            report['warnings'].extend(boundary_issues['warnings'])
            report['quality_score'] -= 10
        
        # Check 4: Script validation (for languages with specific scripts)
        if language:
            script_issues = cls._validate_script(text, language)
            if script_issues['has_issues']:
                report['issues']['wrong_script'] = True
                report['warnings'].extend(script_issues['warnings'])
                report['quality_score'] -= 20
                if script_issues['severity'] == 'critical':
                    report['errors'].extend(script_issues['errors'])
                    report['is_valid'] = False
        
        # Check 5: Low confidence detection (using segments if available)
        if segments:
            confidence_issues = cls._detect_low_confidence(segments)
            if confidence_issues['has_low_confidence']:
                report['issues']['low_confidence'] = True
                report['warnings'].extend(confidence_issues['warnings'])
                report['quality_score'] -= 15
        
        # Final quality assessment
        if report['quality_score'] < 50:
            report['is_valid'] = False
        
        return report['is_valid'], report
    
    @classmethod
    def _detect_repetition(
        cls,
        text: str,
        compression_ratio: Optional[float] = None
    ) -> Dict:
        """Detect repetitive patterns in text"""
        issues = {
            'has_repetition': False,
            'severity': 'none',
            'warnings': [],
            'errors': []
        }
        
        # Check compression ratio (Whisper metric)
        if compression_ratio is not None:
            if compression_ratio > 5.0:
                issues['has_repetition'] = True
                issues['severity'] = 'critical'
                issues['errors'].append(
                    f"Critical repetition detected (compression_ratio: {compression_ratio:.2f})"
                )
            elif compression_ratio > 2.5:
                issues['has_repetition'] = True
                issues['severity'] = 'warning'
                issues['warnings'].append(
                    f"Possible repetition detected (compression_ratio: {compression_ratio:.2f})"
                )
        
        # Check for repeated characters (e.g., ुुुु)
        char_pattern = re.compile(r'(.)\1{4,}')  # Same char repeated 5+ times
        matches = char_pattern.findall(text)
        if matches:
            issues['has_repetition'] = True
            if issues['severity'] != 'critical':
                issues['severity'] = 'warning'
            issues['warnings'].append(
                f"Repeated character patterns detected: {set(matches)}"
            )
        
        # Check for repeated words (3+ consecutive)
        words = text.split()
        if len(words) > 5:
            for i in range(len(words) - 2):
                if words[i] == words[i+1] == words[i+2]:
                    issues['has_repetition'] = True
                    if issues['severity'] != 'critical':
                        issues['severity'] = 'warning'
                    issues['warnings'].append(
                        f"Repeated word pattern detected: '{words[i]}'"
                    )
                    break
        
        # Check for repeated phrases (2+ word phrases repeated)
        if len(words) > 10:
            for phrase_len in [2, 3]:
                for i in range(len(words) - phrase_len * 2):
                    phrase1 = ' '.join(words[i:i+phrase_len])
                    phrase2 = ' '.join(words[i+phrase_len:i+phrase_len*2])
                    if phrase1 == phrase2 and len(phrase1) > 5:
                        issues['has_repetition'] = True
                        if issues['severity'] != 'critical':
                            issues['severity'] = 'warning'
                        issues['warnings'].append(
                            f"Repeated phrase detected: '{phrase1}'"
                        )
                        break
                if issues['has_repetition']:
                    break
        
        return issues
    
    @classmethod
    def _detect_corrupted_unicode(cls, text: str) -> Dict:
        """Detect corrupted Unicode patterns"""
        issues = {
            'has_corruption': False,
            'severity': 'none',
            'warnings': [],
            'errors': []
        }
        
        # Check for abnormal Unicode patterns
        # Pattern 1: Repeated combining marks (e.g., ुुुु)
        combining_pattern = re.compile(r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF]{4,}')
        if combining_pattern.search(text):
            issues['has_corruption'] = True
            issues['severity'] = 'critical'
            issues['errors'].append(
                "Corrupted Unicode: Excessive combining marks detected"
            )
        
        # Pattern 2: Invalid Unicode sequences
        try:
            text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            issues['has_corruption'] = True
            issues['severity'] = 'critical'
            issues['errors'].append("Invalid Unicode sequences detected")
        
        # Pattern 3: Mixed scripts inappropriately (may indicate corruption)
        # Count different script types
        script_counts = {}
        for char in text:
            if char.isalpha():
                for script_name, (start, end) in cls.UNICODE_SCRIPTS.items():
                    if start <= ord(char) <= end:
                        script_counts[script_name] = script_counts.get(script_name, 0) + 1
                        break
        
        # If too many different scripts mixed (more than 3), might be corrupted
        if len(script_counts) > 3:
            issues['has_corruption'] = True
            if issues['severity'] != 'critical':
                issues['severity'] = 'warning'
            issues['warnings'].append(
                f"Unusual script mixing detected: {list(script_counts.keys())}"
            )
        
        # Pattern 4: Broken words (spaces in middle of words for non-space languages)
        # This is language-specific and handled in script validation
        
        return issues
    
    @classmethod
    def _detect_missing_boundaries(cls, text: str) -> Dict:
        """Detect missing sentence boundaries"""
        issues = {
            'has_issues': False,
            'warnings': []
        }
        
        # Check for very long sentences (no punctuation for >200 chars)
        sentences = re.split(r'[.!?।।।]', text)
        long_sentences = [s for s in sentences if len(s.strip()) > 200]
        
        if long_sentences:
            issues['has_issues'] = True
            issues['warnings'].append(
                f"Found {len(long_sentences)} very long sentences "
                f"(>200 chars without punctuation). May indicate missing boundaries."
            )
        
        # Check for lack of punctuation in general
        punctuation_count = len(re.findall(r'[.!?।।।]', text))
        word_count = len(text.split())
        
        if word_count > 50 and punctuation_count == 0:
            issues['has_issues'] = True
            issues['warnings'].append(
                "No sentence boundaries detected in text. "
                "May indicate transcription quality issues."
            )
        
        return issues
    
    @classmethod
    def _validate_script(cls, text: str, language: str) -> Dict:
        """Validate that text uses correct script for language"""
        issues = {
            'has_issues': False,
            'severity': 'none',
            'warnings': [],
            'errors': []
        }
        
        # Language to script mapping
        lang_script_map = {
            'te': 'telugu',
            'hi': 'devanagari',
            'mr': 'devanagari',
            'ta': 'tamil',
            'kn': 'kannada',
            'ml': 'malayalam',
            'gu': 'gujarati',
            'pa': 'gurmukhi',
            'bn': 'bengali',
            'or': 'odia',
            'zh': 'chinese',
            'ja': 'japanese_hiragana',  # Simplified check
            'ko': 'korean',
            'ar': 'arabic',
            'th': 'thai',
            'ru': 'cyrillic',
            'uk': 'cyrillic',
        }
        
        expected_script = lang_script_map.get(language)
        if not expected_script:
            return issues  # No script validation for this language
        
        expected_range = cls.UNICODE_SCRIPTS.get(expected_script)
        if not expected_range:
            return issues
        
        # Count characters in expected script
        expected_count = sum(
            1 for char in text
            if expected_range[0] <= ord(char) <= expected_range[1]
        )
        
        # Count total alphabetic characters
        total_alpha = sum(1 for char in text if char.isalpha())
        
        if total_alpha == 0:
            return issues
        
        expected_ratio = expected_count / total_alpha
        
        # Check for wrong scripts
        wrong_scripts = []
        for script_name, (start, end) in cls.UNICODE_SCRIPTS.items():
            if script_name == expected_script:
                continue
            
            count = sum(1 for char in text if start <= ord(char) <= end)
            if count > expected_count * 0.3:  # More than 30% of expected
                wrong_scripts.append((script_name, count))
        
        if wrong_scripts:
            issues['has_issues'] = True
            issues['severity'] = 'critical'
            issues['errors'].append(
                f"Wrong script detected. Expected {expected_script}, "
                f"but found: {[s[0] for s in wrong_scripts]}"
            )
        
        # Check if expected script is present
        if expected_ratio < 0.3 and total_alpha > 10:
            issues['has_issues'] = True
            if issues['severity'] != 'critical':
                issues['severity'] = 'warning'
            issues['warnings'].append(
                f"Low presence of expected script ({expected_script}): "
                f"{expected_ratio*100:.1f}% of alphabetic characters"
            )
        
        return issues
    
    @classmethod
    def _detect_low_confidence(cls, segments: List[Dict]) -> Dict:
        """Detect low confidence segments"""
        issues = {
            'has_low_confidence': False,
            'warnings': []
        }
        
        if not segments:
            return issues
        
        # Check average log probability (confidence metric)
        logprobs = [
            seg.get('avg_logprob', -1.0)
            for seg in segments
            if 'avg_logprob' in seg
        ]
        
        if logprobs:
            avg_logprob = sum(logprobs) / len(logprobs)
            
            # Log probability threshold: -1.0 is reasonable, < -1.5 is low confidence
            if avg_logprob < -1.5:
                issues['has_low_confidence'] = True
                issues['warnings'].append(
                    f"Low average confidence detected (avg_logprob: {avg_logprob:.2f})"
                )
            
            # Check for segments with very low confidence
            low_conf_segments = [lp for lp in logprobs if lp < -2.0]
            if len(low_conf_segments) > len(logprobs) * 0.3:  # More than 30%
                issues['has_low_confidence'] = True
                issues['warnings'].append(
                    f"Many low-confidence segments: {len(low_conf_segments)}/{len(logprobs)}"
                )
        
        return issues
