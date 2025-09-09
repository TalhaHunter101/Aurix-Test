# Content Moderation Automation

An AI-powered system that automatically classifies web content for spam, advertisements, malicious links, and other issues. Uses Google's Gemini AI to analyze content and compare results with human annotations.

## Quick Start

### 1. Setup Environment
```bash
# Make setup script executable and run it
chmod +x setup.sh
./setup.sh
```

### 2. Configure API Key
```bash
# Edit .env file and add your Gemini API key
nano .env
```

Get your API key from: https://makersuite.google.com/app/apikey

### 3. Run Analysis
```bash
# Activate virtual environment
source venv/bin/activate

# Basic usage - process all content
python content_moderator.py

# Process only 50 content pieces
python content_moderator.py --limit 50

# Process with validation against human annotations
python content_moderator.py --validate

# Process 25 pieces with validation
python content_moderator.py --limit 25 --validate
```

## What It Does

- **Reads** content from `spam_pilot_100_feedback x linguist.csv`
- **Analyzes** each piece using Google Gemini AI
- **Classifies** content for 5 moderation criteria:
  - Keyword Spam
  - Malicious Links  
  - Advertisements
  - Wrong Language
  - Unreadable Content
- **Outputs** results to `ai_moderation_results_N.jsonl` (where N is number of pieces)
- **Validates** results against human annotations (with `--validate` flag)
- **Limits** processing to specified number of pieces (with `--limit N`)

## Command Line Options

- `--limit N` or `-l N`: Process only first N content pieces
- `--validate` or `-v`: Compare AI results with human annotations
- `--csv PATH`: Specify custom CSV file path
- `--help`: Show all available options

## Output Format

```json
{
  "uid": "unique_id",
  "content": "content_text",
  "labels_spam": 1,
  "labels_spam_vector": {
    "keyword_spam": 0,
    "malicious_links": 0,
    "ads": 1
  }
}
```

## Output Files

All output files are saved in the `results/` folder:

- `results/ai_moderation_results_N.jsonl` - AI classification results
- `results/validation_report_N.json` - Detailed accuracy metrics (when using --validate)

## Validation Cross-Checking

When using the `--validate` flag, the system compares AI results with human annotations from the **same CSV file** you're processing. 

**Default validation file**: `proj-data/spam_pilot_100_feedback x linguist.csv`

This CSV file contains:
- Column `1: Keyword Spam` - Human answers for keyword spam detection
- Column `2: Malicious Links` - Human answers for malicious link detection  
- Column `3: Advertisements` - Human answers for advertisement detection
- Column `4: Document not in target language` - Human answers for language detection
- Column `5: Document not readable or incomprehensible` - Human answers for readability
- Column `Answer` - Overall human spam classification

The system will clearly show which file it's using for validation:
```
🔍 VALIDATION MODE
📊 Comparing AI results with human annotations from: spam_pilot_100_feedback x linguist.csv
```

## Requirements

- Python 3.8+
- Google Gemini API key
- Internet connection

## Files

- `content_moderator.py` - Main script
- `requirements.txt` - Python dependencies
- `setup.sh` - Environment setup script
- `.env` - API configuration (create from .env.example)

## Troubleshooting

**API Key Error**: Make sure your Gemini API key is correctly set in `.env`

**Permission Denied**: Run `chmod +x setup.sh` to make setup script executable

**Import Error**: Activate virtual environment with `source venv/bin/activate`

**CSV Not Found**: Check that the CSV file path is correct in the command line arguments