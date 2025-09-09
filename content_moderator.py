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
import requests

# Load API key from environment
load_dotenv()

class ContentModerator:
    def __init__(self):
        """Set up the AI model for content analysis"""
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Please set GROQ_API_KEY in your .env file")
        
        # Groq API configuration
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model_name = "llama-3.1-8b-instant"  # Fast model available in free tier
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting configuration for Groq free tier
        self.rate_limit_delay = 1.0  # 1 second between requests (conservative for free tier)
        self.max_requests_per_minute = 30  # Conservative limit for free tier
        self.request_times = []  # Track request times for rate limiting
        
        # Master prompt for content analysis
        self.master_prompt = """You are an expert content moderator for Argos SmartSuite.
Analyze the following content and answer these 5 questions with YES or NO:

1. Keyword Spam: Reading the entire content, is there any Keyword Spam in the text? 
Keyword spam involves the intentional placement of certain words on a web page to influence search engines or other websites that index the page. These terms will have little to no connection to the content of a page, these terms are used simply to attract more traffic to the website. These keywords may appear many times one after another, or appear in a list or group. You can identify this keyword spam by looking for repeated terms that appear out of context; unrelated to the text content on the page. If you see certain terms repeated many times in this manner, please select this category in your annotation.

Example: "Our site provides you with more streams and more links to see Catanzaro vs Lecce game than any other website. And now you can enjoy the Catanzaro vs Lecce live telecast stream. Enjoy watching Catanzaro vs Lecce online game using our live online streaming. If You are looking for watch online stream Lecce, watch online stream Catanzaro, livestreaming Lecce, live streaming Catanzaro, live stream Lecce, live stream Catanzaro..."
Answer: Yes

2. Malicious Links: Reading the entire content, is there any Malicious Links in the text?
You should answer Yes if you see a document contains an external link that's obviously intended to deceive visitors to the web page. A deceptive web page will often suggest that if a visitor clicks on a link that they will win money, some prize, or be able to view exclusive content, but the real aim is to exploit the visitors to the website. This includes suspected "phishing", where a visitor is tricked into revealing information like their login name and password, or financial information like credit card number. Use your best judgment when comparing an external link to the content of a document: if you believe an external link is intended to solicit the reader's personal or financial information please select this category in your annotation.

Example: "You're the 1 millionth visitor to this website! Click here to win a free iPad!"
Answer: Yes
Explanation: Here a malicious link to steal the reader's personal information is disguised as an enticing offer to win a prize.

3. Advertisements: Reading the entire content, is there any Advertisements in the text?
We consider advertisements to be language within the text of a web page that encourage the reader to buy or use any product or service. Solicitation that encourages the reader to visit a business or download an app, as well as "want ads" looking for applicants to perform a job or service are also considered to be advertisements.

IMPORTANT: Look for ANY commercial content including:
- Product listings with prices, sizes, specifications
- Shop/store information and contact details
- Shipping information and purchase instructions
- Copyright notices from commercial entities
- Promotional language encouraging visits or engagement
- Business contact information or "contact us" messages
- Any content that appears to be from an e-commerce or commercial website

Note that if the text describes a product and contains useful information about its specifications we do not consider this to be advertising and you should not select Yes in your annotation.

Examples:
"Cozy Inn $99 ($247). Excellent location close to the water. Walk to restaurants and the beach. This deal won't last, click here to book now!"
Answer: Yes

"Size Name Dress length Shoulder width Chest length Arm length 1 75.0cm 61.0cm 130.0cm 30.0cm 2 85.0cm 65.0cm 138.0cm 35.0cm ※ Please use this size for reference. Please contact the seller if you have any questions before purchasing the item. Shipping - Shipping anywhere in the world! Hello! Thank you for visiting my shop 'Sui.!' If you have any questions, please send me a message by clicking the 'Questions?' button."
Answer: Yes

"©2018 BUYMA Inc. All right reserved."
Answer: Yes

4. Wrong Language: Reading the entire content, the content is not in the target language. Yes or No?
The text documents should be in English.
- Answer YES if the content is not in English and only contains text in another language
- Answer NO if the content is in English and only contains a small amount of text in another language, but is otherwise in English

5. Unreadable: Reading the content, is the content not readable or incomprehensible?
Some contents may be mal-encoded (where text may appear as strange characters like "ÃƒÆ"), entirely missing (e.g. a blank document ""), or otherwise unreadable. In these cases:
- Answer YES if the content is unreadable or if the text file is entirely empty or you cannot open the document due to some error
- Answer NO if the content is readable and there is any amount of readable text in English

6. Confidence Score: How confident are you with the answers provided? Give me a score from 1 to 5 where 1 is the lowest confidence and 5 is the highest.

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
  }},
  "confidence_score": 5
}}

CRITICAL: Only include "wrong_language": 1 in labels_spam_vector if Wrong Language = YES. Do NOT include this field if it's NO.
CRITICAL: Only include "unreadable": 1 in labels_spam_vector if Unreadable = YES. Do NOT include this field if it's NO.

Do not include the raw content or uid in the JSON output."""

    def _enforce_rate_limit(self):
        """Enforce rate limiting for Groq API"""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # If we're at the limit, wait
        if len(self.request_times) >= self.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0]) + 1
            if sleep_time > 0:
                print(f"⏳ Rate limit reached, waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                # Clean up old requests after waiting
                current_time = time.time()
                self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # Add minimum delay between requests
        if self.request_times:
            time_since_last = current_time - self.request_times[-1]
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(time.time())

    def _call_groq_api(self, prompt: str, max_retries: int = 3) -> str:
        """Call Groq API with proper error handling and retries"""
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert content moderator. Always respond with valid JSON only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0,
            "max_tokens": 1000,
            "stream": False
        }
        
        for attempt in range(max_retries):
            try:
                # Enforce rate limiting
                self._enforce_rate_limit()
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"⏳ Rate limit exceeded, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                elif response.status_code == 400:
                    # Bad request - don't retry
                    error_msg = response.json().get('error', {}).get('message', 'Bad request')
                    raise ValueError(f"Bad request: {error_msg}")
                
                else:
                    # Other error - retry
                    error_msg = response.json().get('error', {}).get('message', f'HTTP {response.status_code}')
                    if attempt == max_retries - 1:
                        raise Exception(f"API error after {max_retries} attempts: {error_msg}")
                    print(f"⚠️ API error (attempt {attempt + 1}): {error_msg}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise Exception("API request timed out after multiple attempts")
                print(f"⚠️ Request timeout (attempt {attempt + 1}), retrying...")
                time.sleep(2 ** attempt)
                continue
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Request failed after {max_retries} attempts: {str(e)}")
                print(f"⚠️ Request error (attempt {attempt + 1}): {str(e)}")
                time.sleep(2 ** attempt)
                continue
        
        raise Exception(f"Failed to get response after {max_retries} attempts")

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
        """Analyze single content piece using Groq API with rate limiting and retry logic"""
        for attempt in range(max_retries):
            try:
                # Format the prompt with content and UID
                prompt = self.master_prompt.format(content=content, uid=uid)
                
                # Get response from Groq API
                response_text = self._call_groq_api(prompt, max_retries=1)  # Single retry per call
                
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

                # Handle confidence score
                confidence_score = result.get('confidence_score', 5)
                if isinstance(confidence_score, str):
                    try:
                        confidence_score = int(confidence_score)
                    except ValueError:
                        confidence_score = 5
                result['confidence_score'] = max(1, min(5, confidence_score))  # Clamp between 1-5

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
                if "Rate limit" in error_msg or "429" in error_msg:
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
            },
            "confidence_score": 1  # Low confidence for failed analysis
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
        print(f"🤖 Using Groq API ({self.model_name}) with rate limiting")
        print(f"⏳ Rate limit: {self.max_requests_per_minute} requests/minute, {self.rate_limit_delay}s between requests")
        
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
                    },
                    "confidence_score": 1  # Low confidence for failed analysis
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
            
            # Calculate true positives, false positives, false negatives
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            
            # Count true positives (both AI and human said YES)
            for result in ai_results:
                uid = result['uid']
                if uid in human_annotations:
                    human = human_annotations[uid]
                    ai_labels = result['labels_spam_vector']
                    
                    if category == 'labels_spam':
                        ai_val = result['labels_spam']
                        human_val = human['labels_spam']
                    else:
                        ai_val = ai_labels.get(category, 0)
                        human_val = human.get(category, 0)
                    
                    if ai_val == 1 and human_val == 1:
                        true_positives += 1
                    elif ai_val == 1 and human_val == 0:
                        false_positives += 1
                    elif ai_val == 0 and human_val == 1:
                        false_negatives += 1
            
            # Calculate precision and recall
            precision = true_positives / (true_positives + false_positives) * 100 if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) * 100 if (true_positives + false_negatives) > 0 else 0
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

    def validate_json_schema(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that results match the expected JSON schema format"""
        print("\n🔍 VALIDATING JSON SCHEMA FORMAT")
        print("=" * 50)
        
        schema_issues = []
        total_results = len(results)
        
        for i, result in enumerate(results):
            issues = []
            
            # Check required fields
            required_fields = ['uid', 'content', 'labels_spam', 'labels_spam_vector']
            for field in required_fields:
                if field not in result:
                    issues.append(f"Missing required field: {field}")
            
            # Check labels_spam_vector structure
            if 'labels_spam_vector' in result:
                labels = result['labels_spam_vector']
                
                # Check required spam categories
                required_spam_cats = ['keyword_spam', 'malicious_links', 'ads']
                for cat in required_spam_cats:
                    if cat not in labels:
                        issues.append(f"Missing required spam category: {cat}")
                    elif not isinstance(labels[cat], int) or labels[cat] not in [0, 1]:
                        issues.append(f"Invalid value for {cat}: {labels[cat]} (must be 0 or 1)")
                
                # Check conditional fields
                wrong_lang = labels.get('wrong_language', 0)
                unreadable = labels.get('unreadable', 0)
                
                if wrong_lang == 1 and unreadable == 1:
                    issues.append("Both wrong_language and unreadable cannot be 1 simultaneously")
                
                # Check that wrong_language/unreadable are only present when 1
                if wrong_lang == 0 and 'wrong_language' in labels:
                    issues.append("wrong_language should not be present when value is 0")
                
                if unreadable == 0 and 'unreadable' in labels:
                    issues.append("unreadable should not be present when value is 0")
            
            # Check labels_spam value
            if 'labels_spam' in result:
                if not isinstance(result['labels_spam'], int) or result['labels_spam'] not in [0, 1]:
                    issues.append(f"Invalid labels_spam value: {result['labels_spam']} (must be 0 or 1)")
            
            # Check confidence score (optional but if present should be 1-5)
            if 'confidence_score' in result:
                conf = result['confidence_score']
                if not isinstance(conf, int) or conf < 1 or conf > 5:
                    issues.append(f"Invalid confidence_score: {conf} (must be 1-5)")
            
            if issues:
                schema_issues.append({
                    'index': i,
                    'uid': result.get('uid', 'unknown')[:8],
                    'issues': issues
                })
        
        # Report results
        if schema_issues:
            print(f"❌ Found {len(schema_issues)} results with schema issues:")
            for issue in schema_issues[:5]:  # Show first 5 issues
                print(f"  Result {issue['index']} ({issue['uid']}): {', '.join(issue['issues'])}")
            if len(schema_issues) > 5:
                print(f"  ... and {len(schema_issues) - 5} more issues")
        else:
            print("✅ All results match expected JSON schema format")
        
        print(f"Schema validation: {total_results - len(schema_issues)}/{total_results} results valid")
        print("=" * 50)
        
        return {
            'total_results': total_results,
            'valid_results': total_results - len(schema_issues),
            'schema_issues': schema_issues,
            'schema_valid': len(schema_issues) == 0
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
        
        # Confidence score statistics
        confidence_scores = [r.get('confidence_score', 1) for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        low_confidence = sum(1 for score in confidence_scores if score <= 2)
        
        print("\n📊 PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total content pieces: {total}")
        print(f"Spam detected: {spam_count} ({spam_count/total*100:.1f}%)")
        print(f"  - Keyword spam: {keyword_spam}")
        print(f"  - Malicious links: {malicious_links}")
        print(f"  - Advertisements: {ads}")
        print(f"  - Wrong language: {wrong_language}")
        print(f"  - Unreadable: {unreadable}")
        print(f"\nConfidence Analysis:")
        print(f"  - Average confidence: {avg_confidence:.1f}/5")
        print(f"  - Low confidence (≤2): {low_confidence} ({low_confidence/total*100:.1f}%)")
        print("=" * 50)

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Content Moderation Automation with AI')
    parser.add_argument('--limit', '-l', type=int, default=None, 
                       help='Limit number of content pieces to process (e.g., 50)')
    parser.add_argument('--validate', '-v', action='store_true', 
                       help='Validate results against human annotations')
    parser.add_argument('--schema-check', action='store_true', 
                       help='Validate JSON schema format (always enabled)')
    parser.add_argument('--csv', type=str, 
                       default="proj-data/spam_pilot_100_feedback x linguist.csv",
                       help='Path to CSV file with content data')
    args = parser.parse_args()
    
    print("🤖 Content Moderation Automation with Groq")
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
        
        # Validate JSON schema format
        schema_validation = moderator.validate_json_schema(results)
        
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
