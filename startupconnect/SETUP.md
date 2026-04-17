# StartupConnect TN - Setup Instructions

## 1. Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Configure OpenAI API Key

Edit the `.env` file and replace `your-openai-api-key-here` with your actual OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-key-here
```

To get an API key:
1. Go to https://platform.openai.com/api-keys
2. Sign up or login
3. Create a new API key
4. Copy and paste it in the .env file

## 3. Run the Application
```bash
python app.py
```

## 4. Access the Platform
Open your browser and go to: http://127.0.0.1:5000

## 5. Resetting/Cleaning the Database
A helper script `delete_login_and_messages.py` can reset development data. It **does not run automatically** and must be invoked manually. Usage:

```bash
# remove only messages (default)
python delete_login_and_messages.py

# remove all users, messages, startups, and related tables
python delete_login_and_messages.py --all
```

Be careful: the `--all` flag is destructive and will wipe the users table. A backup is always created before any changes.

## 6. Email normalization
To avoid case sensitivity issues when logging in, all emails are now stored in lowercase. The application automatically lowercases input on register and login.

If you have existing accounts with mixed-case addresses, run the following in a Python shell to normalize them:

```python
import sqlite3, os
DB = r"c:\Users\PUNITHA ELIZABETH\Documents\startupconnect\startupconnect.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("UPDATE users SET email = LOWER(email);")
conn.commit()
conn.close()
```

This ensures users can sign in regardless of how they typed their address.


## Features

### AI-Powered Chatbot (🤖 button in bottom-left)
- Uses OpenAI GPT-3.5-turbo when API key is configured
- Falls back to rule-based responses if OpenAI is unavailable
- Available in all three dashboards (Student, Mentor, Investor)
- Answers questions about startups, mentors, investors, schemes, and platform features

### Platform Features
- Role-based dashboards (Student, Mentor, Investor)
- AI domain classification
- Readiness score calculation
- Government scheme recommendations
- Mentor-student matching
- Investor-startup connections
- Messaging system

## Troubleshooting

If you see "⚠️ OpenAI not available":
- Check that your API key is correctly set in .env file
- Make sure you installed: pip install openai python-dotenv
- Verify your API key is valid at https://platform.openai.com

The chatbot will still work with rule-based responses even without OpenAI!
