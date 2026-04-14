# 🧠 AI Copy Evaluator Pro

An intelligent desktop application designed to **automatically evaluate handwritten answer sheets** using a local AI engine, while giving teachers full control to review, edit, and override results.

---

## 🚀 Features

### 📄 Smart Answer Evaluation

* Upload handwritten answer sheets
* Automatic text extraction (OCR)
* AI-based answer evaluation with scoring

### ✏️ Teacher-in-the-Loop System

* Editable extracted text (fix OCR errors)
* Manual marks override
* Final score control by teacher

### 📊 Detailed AI Analysis

* Suggested score
* Missing keywords
* Missing concepts
* Broken concepts
* AI reasoning explanation

### 🖥️ Professional UI

* Clean split layout (Image + Evaluation)
* Real-time updates
* Smooth evaluation workflow
* Review & Save system

---

## 🧩 How It Works

1. Upload answer sheet 📤
2. System extracts text automatically
3. Click **Start Evaluation** ⚡
4. Review:

   * Extracted text
   * AI analysis
   * Suggested score
5. Adjust marks if needed ✏️
6. Click **Review & Save** 💾

---

## 🛠️ Tech Stack

* **Python**
* **Tkinter** (GUI)
* **Local AI Inference Engine**
* **Requests API**
* **JSON storage**

---

## 📁 Project Structure

```
Ai_copy_evaluator/
│
├── src_2/
│   ├── dashboard_2.py        # Main UI
│   ├── core_engine.py        # AI runtime manager
│   ├── answer_key.py         # Model answers
│
├── dataset_sample/           # Sample data (optional)
├── output/                   # Saved evaluations
├── .gitignore
├── README.md
```

---

## ⚙️ Setup & Run

### 1. Clone the repository

```
git clone https://github.com/your-username/AI_copy_evaluator.git
cd AI_copy_evaluator
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Run the application

```
python src_2/dashboard_2.py
```

---

## 🔐 Design Philosophy

* **Human + AI collaboration** (not full automation)
* Teacher always has final authority
* Smooth and non-intrusive workflow
* No unnecessary popups or interruptions

---

## 📌 Future Improvements

* 📑 PDF report generation
* 📊 Student performance dashboard
* 🗂 Batch evaluation system
* ☁️ Database integration

---

## 👨‍💻 Author

**Saiswarup Pradhan**
B.Tech Student | AI & Software Development Enthusiast

---

## ⭐ If you like this project

Give it a ⭐ on GitHub — it really helps!

---
