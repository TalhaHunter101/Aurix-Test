#!/bin/bash

# Content Moderation Automation Setup Script

echo "🚀 Setting up Content Moderation Automation Environment..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔑 Creating .env file..."
    echo "GEMINI_API_KEY=your_api_key_here" > .env
    echo "⚠️  Please add your Gemini API key to .env file"
fi

echo "✅ Setup complete!"
echo "📝 Next steps:"
echo "1. Add your Gemini API key to .env file"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python content_moderator.py"
