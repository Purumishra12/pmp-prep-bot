# PMP Prep Bot

PMP Prep Bot is a local AI-powered study assistant for PMP exam preparation.

It helps users:
- explore PMP topics
- ask AI-based topic explanations
- generate quizzes in single-topic, multi-topic, and mock-test modes
- track quiz progress and accuracy
- use local study documents through a knowledge index

---

## Features

### 1. Topic Learning
Browse PMP topics across multiple domains such as:
- Foundations
- People
- Process
- Business Environment
- Agile & Hybrid

### 2. AI Explanation
Select a topic and ask a question to get a detailed explanation.

### 3. Quiz Modes
The app supports:
- **Single Topic Quiz**
- **Multi Topic Quiz**
- **Mock Test**

### 4. Progress Tracking
Tracks:
- total attempts
- total questions answered
- correct answers
- accuracy
- topics practiced

### 5. Knowledge Base
The backend can build a searchable knowledge index from local PMP study PDFs.

---

## Tech Stack

### Backend
- Python
- FastAPI
- Uvicorn
- Ollama
- Local knowledge indexing services

### Frontend
- React
- Vite
- CSS

---

## Required Software

To run this project on a standalone computer, install:

- **Python 3.11+**
- **Node.js 18+**
- **npm**
- **Git**
- **Ollama**
- A modern browser such as Chrome, Edge, or Firefox

Optional but recommended:
- **VS Code**

---

## Project Structure

```text
pmp-prep-bot/
│
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── data/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
