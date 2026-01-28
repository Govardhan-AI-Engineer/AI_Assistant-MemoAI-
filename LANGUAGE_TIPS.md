# Language-Specific Transcription Tips

## Telugu and Indian Languages

### Problem
Telugu and some other languages may produce poor results with the default "base" model, especially if:
- Audio quality is low
- Background noise is present
- Speech is fast or unclear

### Solution

**1. Use a Larger Model**
```bash
# For Telugu - use 'small' or larger model
python main.py teluguvideo.mp4 --language te --model small

# For best accuracy (slower)
python main.py teluguvideo.mp4 --language te --model medium
```

**2. Always Specify Language**
```bash
# Telugu
python main.py video.mp4 --language te

# Hindi
python main.py video.mp4 --language hi

# Tamil
python main.py video.mp4 --language ta
```

**3. Model Recommendations by Language**

| Language | Recommended Model | Code |
|----------|------------------|------|
| Telugu | small, medium | `te` |
| Hindi | small, medium | `hi` |
| Tamil | small, medium | `ta` |
| Kannada | small, medium | `kn` |
| Malayalam | small, medium | `ml` |
| Bengali | small, medium | `bn` |
| Marathi | small, medium | `mr` |
| Gujarati | small, medium | `gu` |
| Punjabi | small, medium | `pa` |
| English | base (default) | `en` |
| Korean | base, small | `ko` |
| Chinese | base, small | `zh` |
| Japanese | base, small | `ja` |

## Why Larger Models Help

- **Base model**: Good for English, common languages
- **Small model**: Better for non-English, especially Indian languages
- **Medium/Large**: Best accuracy, but slower

## Enhanced Parameters

The code now automatically uses:
- `beam_size=5` for better decoding
- `best_of=5` to try multiple decodings
- Language-specific hints for Indian languages

## Troubleshooting

### If you get only punctuation marks:
1. **Use larger model**: `--model small` or `--model medium`
2. **Specify language**: `--language te`
3. **Check audio quality**: Ensure clear audio without heavy background noise

### If transcription is slow:
- Use `--model base` for faster processing (less accurate)
- Use `--model small` for balance (recommended for Telugu)

### If results are still poor:
- Try `--model medium` (best accuracy, slower)
- Ensure audio is clear and not too noisy
- Check if language code is correct

## Example Commands

```bash
# Telugu with small model (recommended)
python main.py teluguvideo.mp4 --language te --model small

# Hindi with medium model (best accuracy)
python main.py hindi_audio.mp3 --language hi --model medium

# Tamil with small model
python main.py tamil_video.mp4 --language ta --model small
```
