"""
Intelligent model selection based on language, audio quality, and duration
"""
from typing import Dict, Optional, Tuple
from pathlib import Path


class ModelSelector:
    """Intelligent Whisper model selection"""
    
    # Model hierarchy (smallest to largest)
    MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    
    # Language-specific model requirements
    LANGUAGE_MODEL_MAP = {
        # Languages that require large model for best quality
        'large_required': {
            'te',  # Telugu - known to have issues with smaller models
        },
        # Languages that work well with medium model
        'medium_recommended': {
            'hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as',  # Indian languages
            'zh', 'ja', 'ko', 'ar', 'th', 'vi',  # Asian languages
            'ru', 'uk', 'pl', 'cs', 'hu', 'ro',  # Slavic/Eastern European
        },
        # Languages that work well with small model
        'small_sufficient': {
            'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'sv', 'no', 'fi', 'da',  # Western European
            'tr', 'el', 'he',  # Other
        },
    }
    
    @classmethod
    def select_model(
        cls,
        language: Optional[str] = None,
        audio_quality: Optional[str] = None,
        duration: Optional[float] = None,
        current_model: Optional[str] = None,
        force_model: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Select optimal Whisper model based on context
        
        Args:
            language: Language code (if known)
            audio_quality: 'high', 'medium', 'low' (if known)
            duration: Audio duration in seconds (if known)
            current_model: Current model being used
            force_model: Force a specific model (overrides selection)
            
        Returns:
            Tuple of (selected_model, selection_reason)
        """
        reason = {
            'selected_model': None,
            'reason': '',
            'factors': []
        }
        
        # Force model override
        if force_model:
            if force_model in cls.MODELS:
                reason['selected_model'] = force_model
                reason['reason'] = f"Model forced to {force_model}"
                reason['factors'].append(f"force_model={force_model}")
                return force_model, reason
            else:
                # Invalid model, fall back to selection
                reason['factors'].append(f"Invalid force_model={force_model}, using selection")
        
        # Start with base model as default
        selected = 'base'
        
        # Factor 1: Language requirements
        if language:
            if language in cls.LANGUAGE_MODEL_MAP['large_required']:
                selected = 'large'
                reason['factors'].append(f"language={language} requires large model")
            elif language in cls.LANGUAGE_MODEL_MAP['medium_recommended']:
                # Start with medium, but may upgrade based on other factors
                selected = 'medium'
                reason['factors'].append(f"language={language} recommended for medium+")
            elif language in cls.LANGUAGE_MODEL_MAP['small_sufficient']:
                selected = 'small'
                reason['factors'].append(f"language={language} works well with small model")
            else:
                # Unknown language - use medium for safety
                selected = 'medium'
                reason['factors'].append(f"unknown language={language}, using medium for safety")
        
        # Factor 2: Audio quality
        if audio_quality:
            if audio_quality == 'low':
                # Low quality audio needs larger model for better accuracy
                if selected in ['tiny', 'base', 'small']:
                    selected = cls._upgrade_model(selected, 1)  # Upgrade by 1 level
                    reason['factors'].append(f"low audio quality, upgraded to {selected}")
            elif audio_quality == 'high':
                # High quality can use smaller models
                if selected == 'large' and language not in cls.LANGUAGE_MODEL_MAP['large_required']:
                    selected = 'medium'  # Downgrade if not required
                    reason['factors'].append(f"high audio quality, using {selected}")
        
        # Factor 3: Duration (longer audio may benefit from larger models)
        if duration:
            if duration > 3600:  # > 1 hour
                # Very long audio - use medium or large for consistency
                if selected in ['tiny', 'base']:
                    selected = 'small'
                    reason['factors'].append(f"long duration ({duration:.0f}s), upgraded to {selected}")
            elif duration < 10:  # < 10 seconds
                # Very short audio - can use smaller models
                if selected == 'large' and language not in cls.LANGUAGE_MODEL_MAP['large_required']:
                    selected = 'medium'
                    reason['factors'].append(f"short duration ({duration:.0f}s), using {selected}")
        
        # Factor 4: Current model (if already loaded, prefer not to downgrade)
        if current_model:
            current_idx = cls.MODELS.index(current_model) if current_model in cls.MODELS else -1
            selected_idx = cls.MODELS.index(selected) if selected in cls.MODELS else -1
            
            # If current model is larger, consider keeping it (unless much larger)
            if current_idx > selected_idx:
                # Current is larger - only downgrade if significantly larger and not needed
                if current_idx - selected_idx > 1 and language not in cls.LANGUAGE_MODEL_MAP['large_required']:
                    reason['factors'].append(f"downgrading from {current_model} to {selected} (not needed)")
                else:
                    selected = current_model
                    reason['factors'].append(f"keeping current model {current_model} (already loaded)")
        
        reason['selected_model'] = selected
        reason['reason'] = f"Selected {selected} based on: {', '.join(reason['factors'])}"
        
        return selected, reason
    
    @classmethod
    def get_fallback_model(cls, current_model: str, language: Optional[str] = None) -> str:
        """
        Get next model to try if current model fails
        
        Args:
            current_model: Current model that failed
            language: Language code (if known)
            
        Returns:
            Next model to try (one level larger)
        """
        if current_model not in cls.MODELS:
            return 'medium'  # Default fallback
        
        current_idx = cls.MODELS.index(current_model)
        
        # If language requires large, always upgrade to large
        if language and language in cls.LANGUAGE_MODEL_MAP['large_required']:
            return 'large'
        
        # Otherwise, upgrade by one level
        if current_idx < len(cls.MODELS) - 1:
            return cls.MODELS[current_idx + 1]
        
        # Already at largest model
        return current_model
    
    @classmethod
    def _upgrade_model(cls, model: str, levels: int = 1) -> str:
        """Upgrade model by specified number of levels"""
        if model not in cls.MODELS:
            return 'medium'
        
        current_idx = cls.MODELS.index(model)
        new_idx = min(current_idx + levels, len(cls.MODELS) - 1)
        return cls.MODELS[new_idx]
    
    @classmethod
    def should_retry_with_larger_model(
        cls,
        quality_report: Dict,
        current_model: str,
        language: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if transcription should be retried with larger model
        
        Args:
            quality_report: Quality validation report
            current_model: Current model used
            language: Language code
            
        Returns:
            Tuple of (should_retry, next_model)
        """
        # Don't retry if already using largest model
        if current_model == 'large':
            return False, None
        
        # Retry if critical errors detected
        if quality_report.get('errors'):
            # Check for critical issues
            issues = quality_report.get('issues', {})
            if issues.get('repetition') or issues.get('corrupted_unicode') or issues.get('wrong_script'):
                next_model = cls.get_fallback_model(current_model, language)
                return True, next_model
        
        # Retry if quality score is very low
        quality_score = quality_report.get('quality_score', 100)
        if quality_score < 50:
            next_model = cls.get_fallback_model(current_model, language)
            return True, next_model
        
        # Retry if language requires larger model
        if language and language in cls.LANGUAGE_MODEL_MAP['large_required']:
            if current_model != 'large':
                return True, 'large'
        
        return False, None
