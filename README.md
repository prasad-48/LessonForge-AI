# LessonForge AI

LessonForge AI is a small LangGraph + Streamlit MVP that generates beginner-friendly lessons for a topic, evaluates them against strict educational criteria with Groq, and retries up to two times before rejecting the output.

## Features

- Topic-driven lesson generation with Groq
- Independent evaluation using six strict PASS/FAIL checks
- Retry loop with explicit retry tracking
- SQLite persistence for lesson attempts and evaluations
- Rejection history and self-improvement guidance from prior failures
- Streamlit dashboard with markdown and JSON exports
- Controlled error injection for demonstration/testing

## Prerequisites

- Python 3.11
- Groq API key

## Setup

1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

## Run the app

```bash
streamlit run app.py
```

## Run the tests

```bash
python -m pytest -q
```

## Notes

- The default topic is "Introduction to RAG".
- Error injection is disabled by default and only applies to the first generated lesson when enabled in the UI.
- The app never approves a lesson that fails the evaluator.

