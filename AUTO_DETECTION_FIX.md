# Auto-Detection Fix - Telugu Script Issue

## Problem
When Telugu audio is auto-detected, the output is in Devanagari (Hindi) script instead of Telugu script, even with medium model.

## Solution Implemented

### 1. Auto-Detection with Re-Transcription
- When language is not specified, auto-detect first
- If Telugu is detected, re-transcribe with Telugu script guidance
- Use enhanced parameters (beam_size=10, best_of=10) for Telugu

### 2. Stricter Validation
- Validation now catches Devanagari output for Telugu
- Raises error with clear solution: use `--model large` for Telugu

### 3. Enhanced Parameters for Telugu
- When Telugu is auto-detected, uses:
  - `beam_size=10` (instead of 5)
  - `best_of=10` (instead of 5)
  - Telugu initial prompt: `'తెలుగు భాషలో మాట్లాడుతున్నారు'`

## Usage

### Auto-Detect (No Language Specified)
```bash
python main.py media/teluguaudio1.m4a
```

**What happens**:
1. Auto-detects language (Telugu)
2. Re-transcribes with Telugu script guidance
3. Uses enhanced parameters for Telugu
4. Validates output is in Telugu script
5. If wrong script detected → raises error with solution

### If Medium Model Fails
The validation will catch Devanagari output and suggest:
```bash
python main.py media/teluguaudio1.m4a --language te --model large
```

## Why Large Model for Telugu?

The medium model sometimes still outputs Devanagari for Telugu. The large model has:
- Better script discrimination
- Prevents Devanagari/Tamil confusion
- Best accuracy for Telugu

## Validation

The validation now:
- ✅ Checks if Telugu count = 0 and Devanagari count > 0
- ✅ Raises error immediately
- ✅ Prevents saving wrong output
- ✅ Provides clear solution (use large model)

## Summary

**Auto-detection now works**:
- Detects Telugu automatically
- Re-transcribes with script guidance
- Validates output
- Catches errors and suggests solution

**If medium model fails for Telugu**:
- Validation catches it
- Suggests using `--model large`
- Prevents saving wrong output
