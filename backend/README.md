# tiktok-clipper-ai Backend Service

A high-performance automated video clipper backend that downloads horizontal YouTube videos, analyzes transcripts using LangChain + Groq LLM to isolate high-engagement viral clips, and crops them into a vertical 9:16 layout complete with large, dynamic yellow subtitles.

---

## Technical Architecture & Core Principles

- **Modular Monolith Layout**: Highly cohesive internal domain contexts structured securely under FastAPI.
- **Secure-by-Design Session Cookies**: Uses HttpOnly, Lax SameSite, and environment-driven Secure flags for absolute JWT storage safety.
- **Dual-Database Persistence**: Orchestrated using Redis connection pooling for low-latency task queue updates and SQLite for permanent query storage (without Alembic migration overhead).
- **Strict 200-Line Limit Compliance**: All operational code files (.py) strictly remain under 200 lines to ensure clean, maintainable logic.
- **PEP 257 Structured Docstrings**: 100% of modules, routes, classes, and public helpers include descriptive, structured docstrings.

---

## Environment Variables (.env)

A `.env` file should be placed at the project root with the following configuration:

```env
SECRET_KEY=your_extremely_secure_long_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=your_groq_api_key_here
SECURE_COOKIE=False  # Set to True in production (forces HTTPS)
```

---

## Local Development & Dependency Setup

### 1. Prerequisites
- **Python**: version 3.10 or higher.
- **Redis**: A running local Redis instance (defaulting to `port 6379`).
- **ImageMagick**: Required by MoviePy's `TextClip` for rendering subtitles. (Install on Ubuntu using `sudo apt install imagemagick`).

### 2. Installation
Initialize your virtual environment and install the required library packages:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## Running the Application

To launch the FastAPI development server locally, execute:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Automated Test Suites

### 1. Execute Unit & Integration Tests
We provide a comprehensive, fully mocked unit and integration test suite:

```bash
python3 -m pytest tests/ -vv
```

### 2. Execute Automated Concurrency Stress Tests
Fulfills Rule 10 requirements by evaluating in-memory ASGI request latencies under concurrent load spikes:

```bash
python3 -m pytest tests/stress_test.py -vv -s
```
