# ✦ ResumeAnalyzer — AI-Powered Matcher

ResumeAnalyzer is a professional-grade tool designed to intelligently analyze resumes against specific job descriptions, internships, or hackathon requirements. Powered by **Google Gemini 2.5 Flash**, it provides deep insights, actionable suggestions, and a compatibility score to help candidates stand out.

## 🚀 Live Demo
**Check it out here:** [https://resumeanalyzer-abc.streamlit.app/](https://resumeanalyzer-abc.streamlit.app/)

## ✨ Features
- **AI-Powered Analysis:** Uses LLMs to detect matched/missing skills and evaluate candidacy beyond simple keywords.
- **Smart Scoring:** Provides a realistic match percentage (0-100%) based on your resume's relevance to the opportunity.
- **Actionable Suggestions:** Generates specific tips on how to improve your resume for a particular role.
- **Multi-Format Support:** Parses both **PDF** and **DOCX** files with high accuracy.
- **History & Tracking:** Keep track of every analysis you've performed in a sleek, organized history tab.
- **Dark Mode Support:** A beautiful, minimalist UI with a deep navy dark theme for late-night sessions.

## 🛠️ Technology Stack
- **Frontend/Backend:** Streamlit (Python)
- **AI Engine:** Google Gemini API (`gemini-2.5-flash`)
- **Database:** SQLite
- **Libraries:** `google-genai`, `PyPDF2`, `python-docx`, `scikit-learn`, `pandas`, `bcrypt`.

## 📦 Installation (Local)
1. Clone the repository:
   ```bash
   git clone https://github.com/Abc319634/ResumeAnalyzer.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your Gemini API key in `.streamlit/secrets.toml`:
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```


