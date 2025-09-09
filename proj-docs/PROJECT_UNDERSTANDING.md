## **What This Project Is About**

You're building an **AI-powered content moderation system** for Argos SmartSuite. Think of it like a smart filter that can automatically detect bad content on websites - similar to how email spam filters work, but for web content.

## **The Current Situation**

Right now, you're doing this work manually in a Google Sheet. You have:
- **100 pieces of web content** (like blog posts, product descriptions, etc.)
- **Human annotators** who manually read each piece and answer 5 questions about it
- This is slow, expensive, and doesn't scale well

## **What You Want to Achieve**

Replace the manual work with an **AI script** that can automatically analyze content and answer the same 5 questions that humans currently answer.

## **The 5 Questions the AI Needs to Answer**

1. **Keyword Spam?** - Is the content stuffed with repeated keywords to trick search engines?
2. **Malicious Links?** - Are there deceptive links trying to steal personal information?
3. **Advertisements?** - Is the content trying to sell something or promote a business?
4. **Wrong Language?** - Is the content not in English?
5. **Unreadable?** - Is the content gibberish, empty, or corrupted?

## **The Data You Have**

- **CSV file**: Contains the original content and human answers (your "ground truth")
- **JSON file**: Contains the expected output format for your AI script

## **Simple Plan to Solve This**

### **Step 1: Create the AI Analysis Script**
- Build a Python script that reads content from the CSV
- Use AI (like OpenAI's API) to analyze each piece of content
- Ask the AI the same 5 questions using the detailed prompts you provided

### **Step 2: Format the Output**
- Convert the AI's answers into the specific JSON format required
- Handle the special rules (like if content is wrong language, all other answers become "No")

### **Step 3: Compare Results**
- Run your AI script on the same 100 pieces of content
- Compare AI answers with human answers to see how accurate it is
- This tells you if the AI is good enough to replace human work

### **Step 4: Improve and Deploy**
- If accuracy is good, you can use this for real content moderation
- If not, you can adjust the prompts or approach

## **Why This Matters**

This will save you time and money by automating content analysis that currently requires human reviewers. It's like having a tireless, fast employee who can analyze thousands of web pages in minutes instead of hours.

