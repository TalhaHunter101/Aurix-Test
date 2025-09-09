#!/usr/bin/env python3
"""
Content Moderation Automation
Uses AI to automatically classify web content for spam, ads, and other issues.
"""

import os
import json
import csv
import pandas as pd
import argparse
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key from environment
load_dotenv()

class ContentModerator:
    def __init__(self):
        """Set up the AI model for content analysis"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Please set GEMINI_API_KEY in your .env file")
        
        # Initialize Google's Gemini AI
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={
                'temperature': 0,
            }
        )
        
        # Master prompt for content analysis
        self.master_prompt = """You are an expert content moderator for Argos SmartSuite.
Analyze the following content and answer these 5 questions with YES or NO:

1. Keyword Spam: Reading the entire content, is there any Keyword Spam in the text? Keyword spam involves the intentional placement of certain words on a web page to influence search engines. These terms will have little to no connection to the content of a page, these terms are used simply to attract more traffic to the website. These keywords may appear many times one after another, or appear in a list or group. Look for repeated terms that appear out of context; unrelated to the text content on the page.

2. Malicious Links: Reading the entire content, is there any Malicious Links in the text? Answer YES if you see a document contains an external link that's obviously intended to deceive visitors. A deceptive web page will often suggest that if a visitor clicks on a link that they will win money, some prize, or be able to view exclusive content, but the real aim is to exploit the visitors. This includes suspected "phishing" where a visitor is tricked into revealing information like their login name and password, or financial information.

3. Advertisements: Reading the entire content, is there any Advertisements in the text? We consider advertisements to be language within the text that encourage the reader to buy or use any product or service. Solicitation that encourages the reader to visit a business or download an app, as well as "want ads" looking for applicants to perform a job or service are also considered advertisements. Note: if the text describes a product and contains useful information about its specifications we do not consider this to be advertising.

4. Wrong Language: Reading the entire content, the content is not in the target language. Answer YES only if the content is not in English and only contains text in another language. Answer NO if the content is in English and only contains a small amount of text in another language, but is otherwise in English.

5. Unreadable: Reading the content, is the content not readable or incomprehensible? Answer YES if the content is unreadable, mal-encoded (strange characters), entirely missing, blank document, or you cannot open the document due to some error. Answer NO if the content is readable and there is any amount of readable text in English.

IMPORTANT RULES:
- If Wrong Language = YES, then all other answers = NO
- If Unreadable = YES, then all other answers = NO
- labels_spam = 1 if ANY of the first 3 questions = YES

Content: {content}

Return ONLY a JSON object in this exact format:
{{
  "labels_spam": 0,
  "labels_spam_vector": {{
    "keyword_spam": 0,
    "malicious_links": 0,
    "ads": 0
  }}
}}

CRITICAL: Only include "wrong_language": 1 in labels_spam_vector if Wrong Language = YES. Do NOT include this field if it's NO.
CRITICAL: Only include "unreadable": 1 in labels_spam_vector if Unreadable = YES. Do NOT include this field if it's NO.

Do not include the raw content or uid in the JSON output."""

    def load_csv_data(self, csv_path: str, limit: int = None) -> List[Dict[str, Any]]:
        """Load content data from CSV file with optional limit"""
        print(f"📖 Loading data from {csv_path}...")
        
        data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                data.append({
                    'uid': row['uid'],
                    'content': row['content']
                })
        
        print(f"✅ Loaded {len(data)} content pieces" + (f" (limited to {limit})" if limit else ""))
        return data

    def analyze_content(self, content: str, uid: str, max_retries: int = 3) -> Dict[str, Any]:
        """Analyze single content piece using Gemini with rate limiting and retry logic"""
        for attempt in range(max_retries):
            try:
                # Format the prompt with content and UID
                prompt = self.master_prompt.format(content=content, uid=uid)
                
                # Get response from Gemini
                response = self.model.generate_content(prompt)
                
                # Extract JSON from response
                response_text = response.text.strip()
                
                # Find JSON in response (in case there's extra text)
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    raise ValueError("No JSON found in response")
                
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                # Attach uid/content locally and normalize fields
                result['uid'] = uid
                result['content'] = content

                labels = result.setdefault('labels_spam_vector', {})

                # Normalize the three main spam categories (always present)
                for key in ['keyword_spam', 'malicious_links', 'ads']:
                    val = labels.get(key, 0)
                    if isinstance(val, bool):
                        labels[key] = 1 if val else 0
                    else:
                        try:
                            labels[key] = 1 if int(val) == 1 else 0
                        except Exception:
                            labels[key] = 0

                # Handle wrong_language and unreadable conditionally
                # Only include them in JSON if they are YES (1)
                wrong_lang_val = labels.get('wrong_language', 0)
                unreadable_val = labels.get('unreadable', 0)

                if isinstance(wrong_lang_val, bool):
                    wrong_lang_val = 1 if wrong_lang_val else 0
                else:
                    try:
                        wrong_lang_val = 1 if int(wrong_lang_val) == 1 else 0
                    except Exception:
                        wrong_lang_val = 0

                if isinstance(unreadable_val, bool):
                    unreadable_val = 1 if unreadable_val else 0
                else:
                    try:
                        unreadable_val = 1 if int(unreadable_val) == 1 else 0
                    except Exception:
                        unreadable_val = 0

                # Only include wrong_language if it's YES
                if wrong_lang_val == 1:
                    labels['wrong_language'] = 1
                else:
                    labels.pop('wrong_language', None)

                # Only include unreadable if it's YES
                if unreadable_val == 1:
                    labels['unreadable'] = 1
                else:
                    labels.pop('unreadable', None)

                if 'labels_spam' in result:
                    val = result['labels_spam']
                    if isinstance(val, bool):
                        result['labels_spam'] = 1 if val else 0
                    else:
                        try:
                            result['labels_spam'] = 1 if int(val) == 1 else 0
                        except Exception:
                            result['labels_spam'] = 0

                # Apply hierarchical rules
                result = self.apply_hierarchical_rules(result)
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and "quota" in error_msg.lower():
                    # Rate limit exceeded - wait and retry
                    wait_time = 60 + (attempt * 10)  # 60s, 70s, 80s
                    print(f"⏳ Rate limit hit for {uid}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                elif attempt == max_retries - 1:
                    # Final attempt failed
                    print(f"❌ Error analyzing content {uid} after {max_retries} attempts: {error_msg}")
                    break
                else:
                    # Other error - wait briefly and retry
                    print(f"⚠️ Error analyzing content {uid} (attempt {attempt + 1}): {error_msg}")
                    time.sleep(5)
                    continue
        
        # Return default safe result if all retries failed
        # Only include required fields per JSON schema (wrong_language and unreadable not included when 0)
        return {
            "uid": uid,
            "content": content,
            "labels_spam": 0,
            "labels_spam_vector": {
                "keyword_spam": 0,
                "malicious_links": 0,
                "ads": 0
            }
        }

    def apply_hierarchical_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules for hierarchical classification"""
        labels = result.get('labels_spam_vector', {})
        
        # Rule 1: If wrong language, all others = 0
        if labels.get('wrong_language', 0) == 1:
            labels['keyword_spam'] = 0
            labels['malicious_links'] = 0
            labels['ads'] = 0
            result['labels_spam'] = 0
        
        # Rule 2: If unreadable, all others = 0
        elif labels.get('unreadable', 0) == 1:
            labels['keyword_spam'] = 0
            labels['malicious_links'] = 0
            labels['ads'] = 0
            result['labels_spam'] = 0
        
        # Rule 3: Calculate labels_spam based on content issues
        else:
            content_issues = (
                labels.get('keyword_spam', 0) +
                labels.get('malicious_links', 0) +
                labels.get('ads', 0)
            )
            result['labels_spam'] = 1 if content_issues > 0 else 0
        
        return result

    def process_batch(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all content pieces sequentially"""
        print(f"🔄 Processing {len(data)} content pieces sequentially...")
        print(f"⚠️ Using sequential processing to avoid rate limits")
        
        results = []
        completed = 0
        
        for item in data:
            completed += 1
            print(f"   Processing {completed}/{len(data)}: {item['uid'][:8]}...")
            
            try:
                result = self.analyze_content(item['content'], item['uid'])
                results.append(result)
            except Exception as e:
                print(f"❌ Error processing {item['uid'][:8]}: {str(e)}")
                # Add default result for failed items (follow JSON schema - no wrong_language/unreadable when 0)
                results.append({
                    "uid": item['uid'],
                    "content": item['content'],
                    "labels_spam": 0,
                    "labels_spam_vector": {
                        "keyword_spam": 0,
                        "malicious_links": 0,
                        "ads": 0
                    }
                })
        
        print("✅ Processing complete!")
        return results

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """Save results to JSONL file in results folder"""
        # Create results folder if it doesn't exist
        os.makedirs('results', exist_ok=True)
        
        # Save to results folder
        results_path = os.path.join('results', output_path)
        print(f"💾 Saving results to {results_path}...")
        
        with open(results_path, 'w', encoding='utf-8') as file:
            for result in results:
                json.dump(result, file, ensure_ascii=False)
                file.write('\n')
        
        print(f"✅ Results saved to {results_path}")
        return results_path

    def load_human_annotations(self, csv_path: str, limit: int = None) -> Dict[str, Dict[str, Any]]:
        """Load human annotations from CSV for validation"""
        print(f"📖 Loading human annotations from {csv_path}...")
        print(f"🔍 Cross-checking against: {os.path.basename(csv_path)}")
        
        annotations = {}
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                
                # Convert human annotations to our format
                uid = row['uid']
                annotations[uid] = {
                    'keyword_spam': 1 if row['1: Keyword Spam'].lower() == 'yes' else 0,
                    'malicious_links': 1 if row['2: Malicious Links'].lower() == 'yes' else 0,
                    'ads': 1 if row['3: Advertisements'].lower() == 'yes' else 0,
                    'wrong_language': 1 if row['4: Document not in target language'].lower() == 'yes' else 0,
                    'unreadable': 1 if row['5: Document not readable or incomprehensible'].lower() == 'yes' else 0,
                    'labels_spam': 1 if row['Answer'].lower() == 'yes' else 0
                }
        
        print(f"✅ Loaded {len(annotations)} human annotations from {os.path.basename(csv_path)}")
        return annotations

    def validate_results(self, ai_results: List[Dict[str, Any]], human_annotations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare AI results with human annotations"""
        print("\n🔍 VALIDATING RESULTS AGAINST HUMAN ANNOTATIONS")
        print("=" * 60)
        
        total = len(ai_results)
        correct_predictions = 0
        category_stats = {
            'keyword_spam': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0},
            'malicious_links': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0},
            'ads': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0},
            'wrong_language': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0},
            'unreadable': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0},
            'labels_spam': {'correct': 0, 'total': 0, 'ai_yes': 0, 'human_yes': 0}
        }
        
        for result in ai_results:
            uid = result['uid']
            if uid not in human_annotations:
                continue
                
            human = human_annotations[uid]
            ai_labels = result['labels_spam_vector']
            
            # Overall spam detection accuracy
            if result['labels_spam'] == human['labels_spam']:
                correct_predictions += 1
                category_stats['labels_spam']['correct'] += 1
            
            category_stats['labels_spam']['total'] += 1
            if result['labels_spam'] == 1:
                category_stats['labels_spam']['ai_yes'] += 1
            if human['labels_spam'] == 1:
                category_stats['labels_spam']['human_yes'] += 1
            
            # Individual category accuracy
            for category in ['keyword_spam', 'malicious_links', 'ads', 'wrong_language', 'unreadable']:
                ai_val = ai_labels.get(category, 0)
                human_val = human.get(category, 0)
                
                if ai_val == human_val:
                    category_stats[category]['correct'] += 1
                
                category_stats[category]['total'] += 1
                if ai_val == 1:
                    category_stats[category]['ai_yes'] += 1
                if human_val == 1:
                    category_stats[category]['human_yes'] += 1
        
        # Calculate metrics
        overall_accuracy = correct_predictions / total * 100 if total > 0 else 0
        
        print(f"Overall Accuracy: {overall_accuracy:.1f}% ({correct_predictions}/{total})")
        print("\nPer-Category Analysis:")
        print("-" * 60)
        
        for category, stats in category_stats.items():
            if stats['total'] == 0:
                continue
                
            accuracy = stats['correct'] / stats['total'] * 100
            precision = stats['correct'] / stats['ai_yes'] * 100 if stats['ai_yes'] > 0 else 0
            recall = stats['correct'] / stats['human_yes'] * 100 if stats['human_yes'] > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            print(f"{category.replace('_', ' ').title():15} | "
                  f"Acc: {accuracy:5.1f}% | "
                  f"Prec: {precision:5.1f}% | "
                  f"Rec: {recall:5.1f}% | "
                  f"F1: {f1:5.1f}% | "
                  f"AI: {stats['ai_yes']:2d} | "
                  f"Human: {stats['human_yes']:2d}")
        
        print("=" * 60)
        
        return {
            'overall_accuracy': overall_accuracy,
            'total_samples': total,
            'correct_predictions': correct_predictions,
            'category_stats': category_stats
        }

    def generate_summary(self, results: List[Dict[str, Any]]):
        """Generate processing summary"""
        total = len(results)
        spam_count = sum(1 for r in results if r['labels_spam'] == 1)
        
        keyword_spam = sum(1 for r in results if r['labels_spam_vector'].get('keyword_spam', 0) == 1)
        malicious_links = sum(1 for r in results if r['labels_spam_vector'].get('malicious_links', 0) == 1)
        ads = sum(1 for r in results if r['labels_spam_vector'].get('ads', 0) == 1)
        wrong_language = sum(1 for r in results if r['labels_spam_vector'].get('wrong_language', 0) == 1)
        unreadable = sum(1 for r in results if r['labels_spam_vector'].get('unreadable', 0) == 1)
        
        print("\n📊 PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total content pieces: {total}")
        print(f"Spam detected: {spam_count} ({spam_count/total*100:.1f}%)")
        print(f"  - Keyword spam: {keyword_spam}")
        print(f"  - Malicious links: {malicious_links}")
        print(f"  - Advertisements: {ads}")
        print(f"  - Wrong language: {wrong_language}")
        print(f"  - Unreadable: {unreadable}")
        print("=" * 50)

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Content Moderation Automation with AI')
    parser.add_argument('--limit', '-l', type=int, default=None, 
                       help='Limit number of content pieces to process (e.g., 50)')
    parser.add_argument('--validate', '-v', action='store_true', 
                       help='Validate results against human annotations')
    parser.add_argument('--csv', type=str, 
                       default="proj-data/spam_pilot_100_feedback x linguist.csv",
                       help='Path to CSV file with content data')
    args = parser.parse_args()
    
    print("🤖 Content Moderation Automation")
    print("=" * 40)
    if args.limit:
        print(f"📊 Processing limit: {args.limit} content pieces")
    if args.validate:
        print("🔍 Validation mode: Will compare with human annotations")
    print("=" * 40)
    
    try:
        # Initialize moderator
        moderator = ContentModerator()
        
        # Load data
        data = moderator.load_csv_data(args.csv, args.limit)
        
        # Process content
        results = moderator.process_batch(data)
        
        # Save results to results folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"ai_moderation_results_{len(results)}_{timestamp}.jsonl"
        results_path = moderator.save_results(results, output_filename)
        
        # Generate summary
        moderator.generate_summary(results)
        
        # Validation against human annotations
        if args.validate:
            print(f"\n🔍 VALIDATION MODE")
            print(f"📊 Comparing AI results with human annotations from: {os.path.basename(args.csv)}")
            print("=" * 60)
            
            human_annotations = moderator.load_human_annotations(args.csv, args.limit)
            validation_results = moderator.validate_results(results, human_annotations)
            
            # Save validation report to results folder
            os.makedirs('results', exist_ok=True)
            validation_filename = f"validation_report_{len(results)}_{timestamp}.json"
            validation_path = os.path.join('results', validation_filename)
            
            with open(validation_path, 'w') as f:
                json.dump(validation_results, f, indent=2)
            print(f"\n📋 Validation report saved to {validation_path}")
        
        print(f"\n🎉 Success! Check results/ folder for output files.")
        print(f"📁 Results folder: {os.path.abspath('results')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
