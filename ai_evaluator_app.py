# ============================================================
# ai_evaluator_app.py — Teacher Desktop App
# Uses: minicpm-v (OCR) + rapidfuzz (grading) — no extra installs
# Dependencies: pip install rapidfuzz requests pillow
# ============================================================
import os, base64, json, requests, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from rapidfuzz import fuzz
from datetime import datetime
from answer_key import answer_keys

# ============================================================
# CONFIG
# ============================================================
OLLAMA_URL   = "http://localhost:11434/api/generate"
OCR_MODEL    = "minicpm-v"
RESULTS_JSON = os.path.join(os.path.dirname(__file__), "results.json")
BIT_MAP      = {"a": 0, "b": 1, "c": 2}

# ============================================================
# PIPELINE (your working code)
# ============================================================
def encode_image(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_text(img_path):
    image_b64 = encode_image(img_path)
    payload = {
        "model": OCR_MODEL,
        "prompt": "Read the handwritten text in this image. Output only what is written. Do not add anything.",
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024}
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    return response.json().get("response", "").strip()

def evaluate_answer(extracted_text, model_answer, max_marks=5):
    score = fuzz.token_set_ratio(extracted_text.lower(), model_answer.lower())
    marks = round((score / 100) * max_marks, 1)
    if score >= 80:   grade = "Excellent"
    elif score >= 60: grade = "Good"
    elif score >= 40: grade = "Average"
    else:             grade = "Poor"
    return {"similarity": round(score, 2), "marks": marks,
            "max_marks": max_marks, "grade": grade}

# ============================================================
# STORAGE
# ============================================================
def load_results():
    if os.path.exists(RESULTS_JSON):
        with open(RESULTS_JSON) as f:
            return json.load(f)
    return []

def save_results(data):
    with open(RESULTS_JSON, "w") as f:
        json.dump(data, f, indent=2)

# ============================================================
# APP
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Copy Evaluator")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.configure(bg="#0f1117")
        self.results      = load_results()
        self.student_name = tk.StringVar()
        self.q_rows       = []
        self.batch_q_rows = []
        self._pending     = []
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg="#0f1117")
        hdr.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(hdr, text="AI Copy Evaluator", font=("Courier", 22, "bold"),
                 bg="#0f1117", fg="#00e5ff").pack(side="left")
        tk.Label(hdr, text="  offline · core-v · optimized",
                 font=("Courier", 9), bg="#0f1117", fg="#333").pack(side="left")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",     background="#0f1117", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a1d27", foreground="#888",
                        font=("Courier", 10, "bold"), padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", "#00e5ff")],
                  foreground=[("selected", "#0f1117")])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_eval    = tk.Frame(nb, bg="#0f1117")
        self.tab_batch   = tk.Frame(nb, bg="#0f1117")
        self.tab_results = tk.Frame(nb, bg="#0f1117")

        nb.add(self.tab_eval,    text="  Evaluate  ")
        nb.add(self.tab_batch,   text="  Batch Mode  ")
        nb.add(self.tab_results, text="  Results  ")

        self._build_eval_tab()
        self._build_batch_tab()
        self._build_results_tab()

    # ── EVALUATE TAB ─────────────────────────────────────────
    def _build_eval_tab(self):
        p = self.tab_eval

        r0 = tk.Frame(p, bg="#0f1117")
        r0.pack(fill="x", padx=15, pady=(10, 5))
        tk.Label(r0, text="Student Name:", bg="#0f1117", fg="#aaa",
                 font=("Courier", 10)).pack(side="left")
        tk.Entry(r0, textvariable=self.student_name, bg="#1a1d27", fg="#fff",
                 font=("Courier", 11), insertbackground="#fff",
                 relief="flat", width=30).pack(side="left", padx=8)

        qf = tk.LabelFrame(p, text=" Questions & Images ",
                           bg="#0f1117", fg="#00e5ff",
                           font=("Courier", 10, "bold"), bd=1, relief="solid")
        qf.pack(fill="x", padx=15, pady=5)

        self.q_frame_inner = tk.Frame(qf, bg="#0f1117")
        self.q_frame_inner.pack(fill="x", padx=5, pady=5)

        br = tk.Frame(qf, bg="#0f1117")
        br.pack(fill="x", padx=5, pady=(0, 8))
        self._btn(br, "+ Add Question",  self._add_question,    "#00e5ff", "#0f1117").pack(side="left", padx=4)
        self._btn(br, "- Remove Last",   self._remove_question, "#ff4d6d", "#fff"   ).pack(side="left", padx=4)
        self._add_question()

        self._btn(p, "⚡  Extract & Evaluate All", self._run_eval,
                  "#00e5ff", "#0f1117", big=True).pack(pady=10)

        self.eval_status = tk.Label(p, text="", bg="#0f1117", fg="#f0a500",
                                    font=("Courier", 10))
        self.eval_status.pack()

        rf = tk.Frame(p, bg="#1a1d27")
        rf.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        self.result_text = tk.Text(rf, bg="#1a1d27", fg="#ccc", font=("Courier", 10),
                                   relief="flat", wrap="word", state="disabled")
        sb = ttk.Scrollbar(rf, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.result_text.pack(fill="both", expand=True, padx=8, pady=8)

        self._btn(p, "💾  Save Results", self._save_current,
                  "#00c896", "#0f1117").pack(pady=(0, 10))

    def _add_question(self):
        idx = len(self.q_rows) + 1
        row = tk.Frame(self.q_frame_inner, bg="#0f1117")
        row.pack(fill="x", pady=3)

        # Question bit selector (a/b/c)
        tk.Label(row, text=f"Q{idx}:", bg="#0f1117", fg="#00e5ff",
                 font=("Courier", 10, "bold"), width=3).pack(side="left")
        bv = tk.StringVar(value="a")
        bit_menu = ttk.Combobox(row, textvariable=bv, values=["a","b","c"],
                                width=4, state="readonly")
        bit_menu.pack(side="left", padx=4)

        tk.Label(row, text="Marks:", bg="#0f1117", fg="#aaa",
                 font=("Courier", 10)).pack(side="left", padx=(6, 2))
        mv = tk.IntVar(value=5)
        tk.Spinbox(row, from_=1, to=20, textvariable=mv, width=4,
                   bg="#1a1d27", fg="#fff", buttonbackground="#1a1d27",
                   font=("Courier", 10), relief="flat").pack(side="left", padx=4)

        iv = tk.StringVar()
        il = tk.Label(row, text="No image selected", bg="#0f1117", fg="#555",
                      font=("Courier", 9), width=28, anchor="w")
        il.pack(side="left", padx=4)

        def pick(i=iv, l=il):
            path = filedialog.askopenfilename(
                filetypes=[("Images", "*.jpg *.jpeg *.png")])
            if path:
                i.set(path)
                l.config(text=os.path.basename(path), fg="#00e5ff")

        self._btn(row, "📷 Pick Image", pick, "#222", "#00e5ff", small=True).pack(side="left")
        self.q_rows.append((bv, mv, iv))

    def _remove_question(self):
        if len(self.q_rows) > 1:
            self.q_rows.pop()
            children = self.q_frame_inner.winfo_children()
            if children: children[-1].destroy()

    def _run_eval(self):
        if not self.student_name.get().strip():
            messagebox.showwarning("Missing", "Enter student name."); return
        for i, (bv, mv, iv) in enumerate(self.q_rows):
            if not iv.get():
                messagebox.showwarning("Missing", f"Select image for Q{i+1}."); return
        self.eval_status.config(text="⏳ Processing...")
        self._set_result("Running OCR and evaluation...\n")
        threading.Thread(target=self._eval_thread, daemon=True).start()

    def _eval_thread(self):
        student     = self.student_name.get().strip()
        total_marks = 0
        total_max   = 0
        lines = [f"Student : {student}",
                 f"Date    : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 "=" * 55]
        records = []

        for i, (bv, mv, iv) in enumerate(self.q_rows):
            q         = f"Q{i+1}"
            bit       = bv.get()
            max_marks = mv.get()
            img       = iv.get()
            model_ans = answer_keys[BIT_MAP[bit]]

            self.after(0, lambda q=q, bit=bit:
                       self.eval_status.config(text=f"⏳ {q} (part {bit.upper()})..."))
            try:
                extracted = extract_text(img)
                ev = evaluate_answer(extracted, model_ans, max_marks)
                total_marks += ev["marks"]
                total_max   += max_marks

                lines += [
                    f"\n{q} (Part {bit.upper()}) — {os.path.basename(img)}",
                    f"  Extracted  : {extracted[:100]}{'...' if len(extracted)>100 else ''}",
                    f"  Similarity : {ev['similarity']}%",
                    f"  Marks      : {ev['marks']} / {max_marks}",
                    f"  Grade      : {ev['grade']}",
                ]
                records.append({
                    "student": student, "question": q, "bit": bit,
                    "img_path": img, "extracted": extracted,
                    "model_answer": model_ans,
                    "similarity": ev["similarity"],
                    "marks": ev["marks"], "max_marks": max_marks,
                    "grade": ev["grade"],
                    "timestamp": datetime.now().isoformat()
                })
            except requests.exceptions.ConnectionError:
                lines.append(f"\n{q} ERROR: Core Runtime not ready. Please run setup.")
            except Exception as e:
                lines.append(f"\n{q} ERROR: {e}")

        pct = round(total_marks / total_max * 100, 1) if total_max else 0
        lines += [
            "", "=" * 55,
            f"TOTAL : {total_marks} / {total_max}  ({pct}%)",
            f"GRADE : {'Excellent' if pct>=80 else 'Good' if pct>=60 else 'Average' if pct>=40 else 'Poor'}"
        ]

        self._pending = records
        self.after(0, lambda: self._set_result("\n".join(lines)))
        self.after(0, lambda: self.eval_status.config(text="✅ Done!"))

    def _save_current(self):
        if not self._pending:
            messagebox.showwarning("Nothing", "Run evaluation first."); return
        self.results.extend(self._pending)
        save_results(self.results)
        self._refresh_results()
        messagebox.showinfo("Saved", f"{len(self._pending)} records saved.")
        self._pending = []

    # ── BATCH TAB ────────────────────────────────────────────
    def _build_batch_tab(self):
        p = self.tab_batch

        tk.Label(p, text="Batch Mode — Process entire folder automatically",
                 bg="#0f1117", fg="#aaa", font=("Courier", 11)).pack(pady=(15, 5))

        ak = tk.LabelFrame(p, text=" Question Setup (part + max marks) ",
                           bg="#0f1117", fg="#00e5ff",
                           font=("Courier", 10, "bold"), bd=1, relief="solid")
        ak.pack(fill="x", padx=15, pady=8)

        self._bq_inner = tk.Frame(ak, bg="#0f1117")
        self._bq_inner.pack(fill="x", padx=5, pady=5)

        brow = tk.Frame(ak, bg="#0f1117")
        brow.pack(fill="x", padx=5, pady=(0, 8))
        self._btn(brow, "+ Add Question", self._batch_add_q, "#00e5ff", "#0f1117").pack(side="left", padx=4)
        self._batch_add_q()

        ff = tk.Frame(p, bg="#0f1117")
        ff.pack(fill="x", padx=15, pady=5)
        self.batch_folder = tk.StringVar()
        tk.Label(ff, text="Image Folder:", bg="#0f1117", fg="#aaa",
                 font=("Courier", 10)).pack(side="left")
        tk.Entry(ff, textvariable=self.batch_folder, bg="#1a1d27", fg="#fff",
                 font=("Courier", 10), relief="flat", width=45).pack(side="left", padx=6)
        self._btn(ff, "Browse", self._pick_folder, "#333", "#00e5ff", small=True).pack(side="left")

        tk.Label(p, text="Images are matched to questions in sorted filename order.",
                 bg="#0f1117", fg="#555", font=("Courier", 9)).pack(pady=2)

        self._btn(p, "⚡  Run Batch", self._run_batch,
                  "#00e5ff", "#0f1117", big=True).pack(pady=10)

        self.batch_status = tk.Label(p, text="", bg="#0f1117", fg="#f0a500",
                                     font=("Courier", 10))
        self.batch_status.pack()
        self.batch_progress = ttk.Progressbar(p, length=600, mode="determinate")
        self.batch_progress.pack(pady=5)

        lf = tk.Frame(p, bg="#1a1d27")
        lf.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        self.batch_log = tk.Text(lf, bg="#1a1d27", fg="#ccc", font=("Courier", 9),
                                 relief="flat", wrap="word", state="disabled")
        sb = ttk.Scrollbar(lf, command=self.batch_log.yview)
        self.batch_log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.batch_log.pack(fill="both", expand=True, padx=8, pady=8)

    def _batch_add_q(self):
        idx = len(self.batch_q_rows) + 1
        row = tk.Frame(self._bq_inner, bg="#0f1117")
        row.pack(fill="x", pady=2)
        tk.Label(row, text=f"Q{idx}:", bg="#0f1117", fg="#00e5ff",
                 font=("Courier", 10, "bold"), width=3).pack(side="left")
        bv = tk.StringVar(value="a")
        ttk.Combobox(row, textvariable=bv, values=["a","b","c"],
                     width=4, state="readonly").pack(side="left", padx=4)
        tk.Label(row, text="Marks:", bg="#0f1117", fg="#aaa",
                 font=("Courier", 10)).pack(side="left", padx=(6, 2))
        mv = tk.IntVar(value=5)
        tk.Spinbox(row, from_=1, to=20, textvariable=mv, width=4,
                   bg="#1a1d27", fg="#fff", buttonbackground="#1a1d27",
                   font=("Courier", 10), relief="flat").pack(side="left")
        self.batch_q_rows.append((bv, mv))

    def _pick_folder(self):
        f = filedialog.askdirectory()
        if f: self.batch_folder.set(f)

    def _run_batch(self):
        folder = self.batch_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No Folder", "Select a valid folder."); return
        self.batch_status.config(text="⏳ Starting...")
        threading.Thread(target=self._batch_thread, daemon=True).start()

    def _batch_thread(self):
        folder  = self.batch_folder.get().strip()
        qcount  = len(self.batch_q_rows)
        exts    = ('.jpg', '.jpeg', '.png')
        images  = sorted([f for f in os.listdir(folder) if f.lower().endswith(exts)])

        if not images:
            self.after(0, lambda: self.batch_status.config(text="No images found.")); return

        total   = len(images)
        records = []
        self.after(0, lambda: self.batch_progress.configure(maximum=total, value=0))

        for i, fname in enumerate(images):
            img_path  = os.path.join(folder, fname)
            q_idx     = i % qcount
            bv, mv    = self.batch_q_rows[q_idx]
            bit       = bv.get()
            max_marks = mv.get()
            model_ans = answer_keys[BIT_MAP[bit]]
            student   = f"Student_{(i // qcount) + 1}"
            q_label   = f"Q{q_idx + 1}"

            self.after(0, lambda s=student, f=fname:
                       self.batch_status.config(text=f"⏳ {s} — {f}"))
            try:
                extracted = extract_text(img_path)
                ev = evaluate_answer(extracted, model_ans, max_marks)
                line = (f"[{student}] {q_label}({bit.upper()}) | {fname} | "
                        f"Marks: {ev['marks']}/{max_marks} | "
                        f"Grade: {ev['grade']} | Similarity: {ev['similarity']}%\n")
                self.after(0, lambda l=line: self._blog(l))
                records.append({
                    "student": student, "question": q_label, "bit": bit,
                    "img_path": img_path, "extracted": extracted,
                    "model_answer": model_ans, "similarity": ev["similarity"],
                    "marks": ev["marks"], "max_marks": max_marks,
                    "grade": ev["grade"], "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.after(0, lambda f=fname, e=e: self._blog(f"ERROR {f}: {e}\n"))

            self.after(0, lambda v=i+1: self.batch_progress.configure(value=v))

        self.results.extend(records)
        save_results(self.results)
        self._refresh_results()
        self.after(0, lambda: self.batch_status.config(
            text=f"✅ Done! {len(records)} images processed."))

    def _blog(self, text):
        self.batch_log.configure(state="normal")
        self.batch_log.insert("end", text)
        self.batch_log.see("end")
        self.batch_log.configure(state="disabled")

    # ── RESULTS TAB ──────────────────────────────────────────
    def _build_results_tab(self):
        p = self.tab_results
        ctrl = tk.Frame(p, bg="#0f1117")
        ctrl.pack(fill="x", padx=15, pady=10)
        self._btn(ctrl, "🔄 Refresh",    self._refresh_results, "#333",    "#00e5ff", small=True).pack(side="left", padx=4)
        self._btn(ctrl, "📊 Export CSV", self._export_csv,      "#00c896", "#0f1117", small=True).pack(side="left", padx=4)
        self._btn(ctrl, "🗑 Clear All",  self._clear_results,   "#ff4d6d", "#fff",    small=True).pack(side="left", padx=4)

        self.stats_label = tk.Label(p, text="", bg="#0f1117", fg="#aaa",
                                    font=("Courier", 10))
        self.stats_label.pack(pady=4)

        cols = ("Student", "Question", "Part", "File", "Marks", "Max", "Grade", "Similarity%", "Date")
        self.tree = ttk.Treeview(p, columns=cols, show="headings")

        style = ttk.Style()
        style.configure("Treeview", background="#1a1d27", foreground="#ccc",
                        fieldbackground="#1a1d27", font=("Courier", 9), rowheight=22)
        style.configure("Treeview.Heading", background="#0f1117", foreground="#00e5ff",
                        font=("Courier", 9, "bold"))
        style.map("Treeview", background=[("selected", "#00e5ff")],
                  foreground=[("selected", "#0f1117")])

        for col, w in zip(cols, [120, 70, 50, 160, 55, 45, 80, 90, 130]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(p, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(p, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill="both", expand=True, padx=15, pady=(5, 0))
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._refresh_results()

    def _refresh_results(self):
        self.results = load_results()
        for r in self.tree.get_children():
            self.tree.delete(r)
        for r in self.results:
            self.tree.insert("", "end", values=(
                r.get("student", ""), r.get("question", ""),
                r.get("bit", "").upper(),
                os.path.basename(r.get("img_path", "")),
                r.get("marks", ""), r.get("max_marks", ""),
                r.get("grade", ""), f"{r.get('similarity', 0)}%",
                r.get("timestamp", "")[:16]))
        if self.results:
            avg = round(sum(r.get("similarity", 0) for r in self.results) / len(self.results), 1)
            self.stats_label.config(
                text=f"Total: {len(self.results)} records  |  Avg Similarity: {avg}%")

    def _export_csv(self):
        if not self.results:
            messagebox.showinfo("Empty", "No results."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")])
        if not path: return
        import csv
        keys = ["student", "question", "bit", "img_path", "extracted",
                "model_answer", "similarity", "marks", "max_marks", "grade", "timestamp"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.results)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def _clear_results(self):
        if messagebox.askyesno("Confirm", "Delete all results?"):
            self.results = []
            save_results(self.results)
            self._refresh_results()

    # ── HELPERS ──────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg, fg, big=False, small=False):
        size = 13 if big else (9 if small else 11)
        pad  = (14, 10) if big else (8, 4)
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                         font=("Courier", size, "bold"), relief="flat",
                         activebackground=fg, activeforeground=bg,
                         padx=pad[0], pady=pad[1], cursor="hand2")

    def _set_result(self, text):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

if __name__ == "__main__":
    App().mainloop()
