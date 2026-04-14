import os, base64, json, requests, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime

# ── Optional imports with graceful fallbacks ─────────────────
try:
    from answer_key import answer_keys
except ImportError:
    answer_keys = [
        "Value Education is the process of understanding one's participation in the larger order and ensuring it in living.",
        "Human values include truth, righteousness, peace, love and non-violence which guide ethical conduct.",
        "Harmony in the self means living with clarity of thought, feeling and will aligned with universal values."
    ]

try:
    from core_engine import ensure_ready
except ImportError:
    def ensure_ready(log=print): pass

ENGINE_URL   = "http://localhost:11434/api/generate"
RESULTS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_2.json")
BIT_MAP      = {"a": 0, "b": 1, "c": 2}

# ── Analysis Engine ──────────────────────────────────────────
def encode_image(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_text(img_path):
    image_b64 = encode_image(img_path)
    payload = {
        "model": "minicpm-v",
        "prompt": "Read the handwritten text in this image. Output only what is written, word for word. Do not add anything else.",
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024}
    }
    response = requests.post(ENGINE_URL, json=payload, timeout=600)
    response.raise_for_status()
    return response.json().get("response", "").strip()

def analyze_answer_ai(extracted_text, model_answer, max_marks=5):
    prompt = f"""You are a strict but fair academic evaluator.

Compare the Student Answer with the Model Answer below and return ONLY a valid JSON object.

Model Answer: "{model_answer}"
Student Answer: "{extracted_text}"

Evaluate based on:
1. Conceptual correctness
2. Keywords present vs missing
3. Completeness of explanation

Return ONLY this JSON (no explanation, no markdown, no extra text):
{{
    "score": <integer from 0 to {max_marks}>,
    "missing_keywords": ["keyword1", "keyword2"],
    "missing_concepts": ["concept1", "concept2"],
    "broken_concepts": ["broken1"],
    "reasoning": "One paragraph explaining the score."
}}"""

    payload = {
        "model": "minicpm-v",
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 512}
    }
    try:
        response = requests.post(ENGINE_URL, json=payload, timeout=600)
        response.raise_for_status()
        raw = response.json().get("response", "{}").strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        # Validate score is a number
        result["score"] = float(result.get("score", 0))
        return result
    except Exception as e:
        return {
            "score": 0.0,
            "missing_keywords": ["Could not parse AI response"],
            "missing_concepts": [],
            "broken_concepts": [],
            "reasoning": f"AI engine error: {str(e)}"
        }

# ── Storage ──────────────────────────────────────────────────
def load_results():
    if os.path.exists(RESULTS_JSON):
        try:
            with open(RESULTS_JSON, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_results(data):
    with open(RESULTS_JSON, "w") as f:
        json.dump(data, f, indent=2)

# ── Colour Palette ────────────────────────────────────────────
BG       = "#0d0f18"
PANEL    = "#12151f"
CARD     = "#1a1e2e"
ACCENT   = "#00e5ff"
GOLD     = "#f5a623"
GREEN    = "#00c896"
RED      = "#ff4d6d"
TEXT     = "#e2e8f0"
MUTED    = "#64748b"
BORDER   = "#2a2f45"

# ── Login Screen ─────────────────────────────────────────────
class LoginScreen(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent    = parent
        self.on_success = on_success
        self.title("Teacher Login")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._center(360, 320)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.parent.destroy)
        self.grab_set()

    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        tk.Label(self, text="◈  EVALUATOR PRO", font=("Courier", 20, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(30, 4))
        tk.Label(self, text="Teacher Access Only", font=("Courier", 10),
                 bg=BG, fg=MUTED).pack(pady=(0, 25))

        form = tk.Frame(self, bg=BG)
        form.pack(padx=40, fill="x")

        for row, (lbl, attr, show) in enumerate([
            ("USERNAME", "user_ent", ""),
            ("PASSWORD", "pass_ent", "●"),
        ]):
            tk.Label(form, text=lbl, font=("Courier", 8), bg=BG, fg=MUTED
                     ).grid(row=row*2, column=0, sticky="w", pady=(8,2))
            ent = tk.Entry(form, show=show, bg=CARD, fg=TEXT, insertbackground=ACCENT,
                           relief="flat", font=("Courier", 12), bd=0,
                           highlightthickness=1, highlightbackground=BORDER,
                           highlightcolor=ACCENT)
            ent.grid(row=row*2+1, column=0, sticky="ew", ipady=6)
            setattr(self, attr, ent)

        form.columnconfigure(0, weight=1)
        self.user_ent.insert(0, "teacher")
        self.pass_ent.insert(0, "admin")
        self.pass_ent.bind("<Return>", lambda e: self.do_login())

        tk.Button(self, text="LOGIN  →", command=self.do_login,
                  bg=ACCENT, fg=BG, font=("Courier", 11, "bold"),
                  relief="flat", cursor="hand2", pady=8
                  ).pack(padx=40, pady=20, fill="x")

    def do_login(self):
        if self.user_ent.get() == "teacher" and self.pass_ent.get() == "admin":
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Access Denied", "Invalid credentials.", parent=self)

# ── Main Application ─────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("AI Copy Evaluator Pro")
        self.geometry("1440x860")
        self.minsize(1200, 700)
        self.configure(bg=BG)

        self.results          = load_results()
        self.current_img_path = None
        self.current_analysis = {}
        self.ai_score         = tk.DoubleVar(value=0.0)

        # Metadata vars
        self.student_name = tk.StringVar(value="John Doe")
        self.roll_no      = tk.StringVar(value="2021CSE001")
        self.semester     = tk.StringVar(value="4th")
        self.subject      = tk.StringVar(value="Universal Human Values")
        # Teacher can override marks in this var
        self.teacher_marks = tk.StringVar(value="—")
        self.teacher_marks.trace_add("write", self._update_final_badge)

        LoginScreen(self, self._launch)

    # ── Launch ────────────────────────────────────────────────
    def _launch(self):
        self.deiconify()
        self._build_ui()

    # ── UI Builder ───────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()
        self._build_body()
        self._build_statusbar()

    def _build_topbar(self):
        bar = tk.Frame(self, bg=PANEL, height=72)
        bar.pack(fill="x", padx=10, pady=(10, 0))
        bar.pack_propagate(False)

        # Left: logo
        tk.Label(bar, text="◈", font=("Courier", 22, "bold"), bg=PANEL, fg=ACCENT
                 ).pack(side="left", padx=(18, 6), pady=12)
        tk.Label(bar, text="AI COPY EVALUATOR PRO", font=("Courier", 14, "bold"),
                 bg=PANEL, fg=TEXT).pack(side="left", pady=12)

        # Right: Load button + score badge
        tk.Button(bar, text="📁  LOAD ANSWER SHEET",
                  command=self._pick_image,
                  bg=ACCENT, fg=BG, font=("Courier", 10, "bold"),
                  relief="flat", cursor="hand2", padx=14, pady=6
                  ).pack(side="right", padx=18, pady=12)

        self.final_badge = tk.Label(bar, text="FINAL  —  / 5",
                                    font=("Courier", 13, "bold"),
                                    bg=PANEL, fg=GOLD)
        self.final_badge.pack(side="right", padx=10)

        # Metadata fields
        meta = tk.Frame(bar, bg=PANEL)
        meta.pack(side="left", padx=30)

        def meta_field(parent, label, var, w=14):
            f = tk.Frame(parent, bg=PANEL)
            f.pack(side="left", padx=10)
            tk.Label(f, text=label, font=("Courier", 7), bg=PANEL, fg=MUTED
                     ).pack(anchor="w")
            tk.Entry(f, textvariable=var, font=("Courier", 11, "bold"),
                     bg=PANEL, fg=ACCENT, relief="flat", width=w,
                     insertbackground=ACCENT
                     ).pack()

        meta_field(meta, "STUDENT NAME", self.student_name, 16)
        meta_field(meta, "ROLL NO",      self.roll_no,      12)
        meta_field(meta, "SEM.",         self.semester,      5)
        meta_field(meta, "SUBJECT",      self.subject,      22)

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # ── LEFT: Image viewer ────────────────────────────────
        left = tk.LabelFrame(body, text="  STUDENT COPY  ",
                             bg=BG, fg=ACCENT,
                             font=("Courier", 9, "bold"),
                             bd=1, relief="solid",
                             highlightbackground=BORDER)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.img_label = tk.Label(left, bg=BG,
                                  text="No image loaded.\nClick  📁 LOAD ANSWER SHEET  to begin.",
                                  fg=MUTED, font=("Courier", 11))
        self.img_label.pack(fill="both", expand=True)

        # ── RIGHT: Controls panel ─────────────────────────────
        right = tk.Frame(body, bg=BG, width=480)
        right.pack(side="right", fill="both", padx=(6, 0))
        right.pack_propagate(False)

        # ── Extracted text (READ-ONLY display) ───────────────
        tk.Label(right, text="EXTRACTED TEXT  (Auto OCR — editable if OCR fails)",
                 bg=BG, fg=MUTED, font=("Courier", 8)
                 ).pack(anchor="w", pady=(0, 2))

        ocr_frame = tk.Frame(right, bg=CARD, bd=1, relief="solid",
                             highlightthickness=1, highlightbackground=BORDER)
        ocr_frame.pack(fill="x")

        self.ocr_scroll = tk.Scrollbar(ocr_frame, bg=CARD, troughcolor=CARD,
                                        relief="flat", width=8)
        self.ocr_scroll.pack(side="right", fill="y")

        # EDITABLE — if OCR fails, teacher can type the answer manually
        self.ocr_box = tk.Text(ocr_frame, bg=CARD, fg=TEXT,
                               font=("Courier", 10), height=9,
                               relief="flat", bd=0, wrap="word",
                               yscrollcommand=self.ocr_scroll.set,
                               insertbackground=ACCENT,
                               state="normal",
                               cursor="xterm")
        self.ocr_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.ocr_scroll.config(command=self.ocr_box.yview)
        # Placeholder hint
        self.ocr_box.insert("1.0", "OCR will auto-fill here. If blank, type the student's answer manually.")
        self.ocr_box.config(fg=MUTED)
        self.ocr_box.bind("<FocusIn>",  self._ocr_focus_in)
        self.ocr_box.bind("<FocusOut>", self._ocr_focus_out)
        self._ocr_placeholder_active = True

        # ── Question selector + Evaluate ─────────────────────
        qrow = tk.Frame(right, bg=BG)
        qrow.pack(fill="x", pady=(8, 0))

        tk.Label(qrow, text="QUESTION SET:", bg=BG, fg=MUTED,
                 font=("Courier", 9)).pack(side="left")

        self.q_var = tk.StringVar(value="a")
        q_cb = ttk.Combobox(qrow, textvariable=self.q_var,
                             values=["a", "b", "c"], width=6,
                             state="readonly", font=("Courier", 11))
        q_cb.pack(side="left", padx=8)

        # Style combobox
        style = ttk.Style()
        style.configure("TCombobox",
                         fieldbackground=CARD,
                         background=CARD,
                         foreground=TEXT,
                         selectbackground=ACCENT,
                         selectforeground=BG)

        tk.Button(right, text="⚡   START EVALUATION",
                  command=self._run_eval,
                  bg=GOLD, fg=BG,
                  font=("Courier", 12, "bold"),
                  relief="flat", cursor="hand2", pady=9
                  ).pack(fill="x", pady=8)

        # ── Override + Save bar (Packed to bottom first to ensure visibility) ──
        save_bar = tk.Frame(right, bg=CARD, bd=1, relief="solid")
        save_bar.pack(fill="x", pady=(0, 0), side="bottom")

        tk.Label(save_bar,
                 text="Review OCR, AI analysis and adjust marks before saving",
                 bg=CARD, fg=MUTED,
                 font=("Courier", 9)
        ).pack(anchor="w", padx=14, pady=(6, 0))

        tk.Label(save_bar, text="TEACHER MARKS:",
                 bg=CARD, fg=ACCENT, font=("Courier", 10, "bold")
                 ).pack(side="left", padx=(14, 6), pady=10)

        # Spinbox so teacher can click up/down or type a value
        self.marks_spin = tk.Spinbox(
            save_bar,
            from_=0.0, to=5.0, increment=0.5,
            textvariable=self.teacher_marks,
            width=5,
            font=("Courier", 14, "bold"),
            bg=BG, fg=GOLD,
            buttonbackground=CARD,
            relief="flat",
            justify="center",
            insertbackground=GOLD
        )
        self.marks_spin.pack(side="left", padx=4, pady=10)

        tk.Label(save_bar, text="/ 5", bg=CARD, fg=MUTED,
                 font=("Courier", 11)).pack(side="left")

        tk.Button(save_bar, text="💾  REVIEW & SAVE",
                  command=self._save_record,
                  bg=GREEN, fg=BG,
                  font=("Courier", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=20, pady=8
                  ).pack(side="right", padx=14, pady=10)

        # ── AI Analysis box (Grows to fill remaining space) ───────────────
        af = tk.LabelFrame(right, text="  AI ANALYSIS  ",
                           bg=BG, fg=ACCENT,
                           font=("Courier", 9, "bold"),
                           bd=1, relief="solid")
        af.pack(fill="both", expand=True, pady=(0, 6))

        ai_scroll = tk.Scrollbar(af, bg=BG, troughcolor=BG,
                                  relief="flat", width=8)
        ai_scroll.pack(side="right", fill="y")

        self.ai_box = tk.Text(af, bg=BG, fg=TEXT,
                              font=("Courier", 10), relief="flat",
                              bd=0, wrap="word",
                              yscrollcommand=ai_scroll.set,
                              insertbackground=ACCENT,
                              state="disabled",            # READ-ONLY
                              cursor="arrow")
        self.ai_box.pack(fill="both", expand=True, padx=6, pady=6)
        ai_scroll.config(command=self.ai_box.yview)

        # Configure text tags for rich display
        self.ai_box.tag_configure("section",  font=("Courier", 9, "bold"),  foreground=ACCENT)
        self.ai_box.tag_configure("score_lbl",font=("Courier", 11, "bold"), foreground=TEXT)
        self.ai_box.tag_configure("score_val",font=("Courier", 16, "bold"), foreground=GOLD)
        self.ai_box.tag_configure("item",     font=("Courier", 10),         foreground=TEXT)
        self.ai_box.tag_configure("reason",   font=("Courier", 10),         foreground="#94a3b8")
        self.ai_box.tag_configure("none_tag", font=("Courier", 10),         foreground=MUTED)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=PANEL, height=36)
        bar.pack(fill="x", padx=10, pady=(0, 8))
        bar.pack_propagate(False)

        self.status_lbl = tk.Label(bar, text="● Ready",
                                   bg=PANEL, fg=GREEN,
                                   font=("Courier", 9, "bold"))
        self.status_lbl.pack(side="left", padx=14, pady=8)

        self.prog = ttk.Progressbar(bar, mode="indeterminate", length=260)
        self.prog.pack(side="right", padx=14, pady=10)

        st = ttk.Style()
        st.configure("TProgressbar", thickness=6,
                      troughcolor=PANEL, background=ACCENT)

    # ── Image Loading ─────────────────────────────────────────
    def _pick_image(self):
        path = filedialog.askopenfilename(
            title="Select Answer Sheet",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if not path:
            return
        self.current_img_path = path
        self._display_image(path)
        self._set_status(f"Loaded: {os.path.basename(path)}", GREEN)
        # Clear previous results
        self._ocr_placeholder_active = False
        self._write_ocr("")
        self._ocr_placeholder_active = False
        self._write_readonly(self.ai_box, "")
        self.teacher_marks.set("—")
        self.final_badge.config(text="FINAL  —  / 5")
        # Auto-extract in background
        threading.Thread(target=self._bg_extract, args=(path,), daemon=True).start()

    def _display_image(self, path):
        img = Image.open(path)
        # Get the actual label dimensions after packing
        self.update_idletasks()
        w_box = max(self.img_label.winfo_width(),  600)
        h_box = max(self.img_label.winfo_height(), 680)
        w, h  = img.size
        ratio = min(w_box / w, h_box / h, 1.0)
        img   = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=photo, text="")
        self.img_label.image = photo   # keep reference

    def _bg_extract(self, path):
        self.after(0, lambda: self._set_status("⏳ Extracting handwritten text via OCR...", ACCENT))
        self.after(0, self.prog.start)
        try:
            text = extract_text(path)
            if not text:
                self.after(0, lambda: self._set_status("⚠ OCR weak — review or edit before evaluation", GOLD))
            else:
                self.after(0, lambda: self._set_status("✅ OCR complete — click START EVALUATION", GREEN))
            self.after(0, lambda: self._write_ocr(text or ""))
        except Exception as e:
            self.after(0, lambda: self._write_ocr(
                f"OCR failed: {e}\n\nOllama may not be running. Type the student answer manually above."
            ))
            self.after(0, lambda: self._set_status("⚠ OCR failed — type answer manually", GOLD))
        finally:
            self.after(0, self.prog.stop)

    # ── Evaluation ───────────────────────────────────────────
    def _run_eval(self):
        if not self.current_img_path:
            messagebox.showwarning("No Image", "Please load an answer sheet image first.")
            return

        extracted = self._read_ocr()
        if not extracted:
            extracted = "(No readable answer — evaluated based on empty response)"

        model_ans = answer_keys[BIT_MAP[self.q_var.get()]]
        self._set_status("⚡ AI evaluating answer...", GOLD)
        self.prog.start()
        threading.Thread(
            target=self._bg_eval,
            args=(extracted, model_ans),
            daemon=True
        ).start()

    def _bg_eval(self, text, model_ans):
        try:
            analysis = analyze_answer_ai(text, model_ans)
            self.current_analysis = analysis
            score = analysis.get("score", 0.0)
            self.after(0, lambda: self._render_analysis(analysis))
            self.after(0, lambda: self.teacher_marks.set(str(score)))
            self.after(0, lambda: self.final_badge.config(
                text=f"FINAL  {score}  / 5"
            ))
            self.after(0, lambda: self._set_status("✅ Evaluation complete — review and save", GREEN))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"❌ Evaluation error: {e}", RED))
        finally:
            self.after(0, self.prog.stop)

    def _render_analysis(self, data):
        score = data.get("score", 0.0)

        # Determine score colour
        if score >= 4:
            score_col = GREEN
        elif score >= 2.5:
            score_col = GOLD
        else:
            score_col = RED

        self.ai_box.tag_configure("score_val",
                                   font=("Courier", 18, "bold"),
                                   foreground=score_col)

        def write(box, text, tag=None):
            """Helper — temporarily enable, write, disable."""
            box.config(state="normal")
            if tag:
                box.insert("end", text, tag)
            else:
                box.insert("end", text)
            box.config(state="disabled")

        self.ai_box.config(state="normal")
        self.ai_box.delete("1.0", "end")
        self.ai_box.config(state="disabled")

        # Score line
        write(self.ai_box, "AI SUGGESTED SCORE:  ", "score_lbl")
        write(self.ai_box, f"{score}", "score_val")
        write(self.ai_box, f"  / 5\n\n")

        sections = [
            ("MISSING KEYWORDS",  data.get("missing_keywords",  [])),
            ("MISSING CONCEPTS",  data.get("missing_concepts",  [])),
            ("BROKEN CONCEPTS",   data.get("broken_concepts",   [])),
        ]
        for title, items in sections:
            write(self.ai_box, f"{title}\n", "section")
            if items:
                for item in items:
                    write(self.ai_box, f"  •  {item}\n", "item")
            else:
                write(self.ai_box, "  •  None\n", "none_tag")
            write(self.ai_box, "\n")

        write(self.ai_box, "AI REASONING\n", "section")
        write(self.ai_box, f"  {data.get('reasoning', 'N/A')}\n", "reason")

    # ── Save Record ──────────────────────────────────────────
    def _save_record(self):
        if not self.current_img_path:
            messagebox.showwarning("Nothing to Save", "Load and evaluate an answer sheet first.")
            return

        marks_raw = self.teacher_marks.get().strip()
        try:
            marks_val = float(marks_raw)
        except ValueError:
            messagebox.showerror("Invalid Marks",
                                 "Please enter a valid numeric mark (e.g. 3 or 3.5) before saving.")
            return

        if not (0.0 <= marks_val <= 5.0):
            messagebox.showerror("Out of Range", "Marks must be between 0 and 5.")
            return

        record = {
            "student":                self.student_name.get(),
            "roll_no":                self.roll_no.get(),
            "semester":               self.semester.get(),
            "subject":                self.subject.get(),
            "question":               self.q_var.get(),
            "marks_given":            marks_val,
            "verified_extracted_text": self._read_ocr(),
            "original_ai_raw":        self.current_analysis,
            "timestamp":              datetime.now().isoformat()
        }

        self.results.append(record)
        save_results(self.results)

        # Update badge with final teacher mark
        self.final_badge.config(text=f"FINAL  {marks_val}  / 5")
        self._set_status(f"✅ Saved — {record['student']} | Q{record['question'].upper()} | {marks_val}/5", GREEN)
        messagebox.showinfo("Saved",
                            f"Evaluation saved!\n\nStudent : {record['student']}\n"
                            f"Roll No : {record['roll_no']}\nMarks   : {marks_val} / 5")

        # ── Reset UI for next student ──────────────────────────
        self.current_img_path = None
        self.img_label.config(image="", text="Load next answer sheet.\nClick  📁 LOAD ANSWER SHEET  to begin.")
        self._ocr_placeholder_active = True
        self.ocr_box.delete("1.0", "end")
        self.ocr_box.insert("1.0", "OCR will auto-fill here. If blank, type the student's answer manually.")
        self.ocr_box.config(fg=MUTED)
        self._write_readonly(self.ai_box, "")
        self.teacher_marks.set("—")
        self.final_badge.config(text="FINAL  —  / 5")

    # ── Helpers ──────────────────────────────────────────────
    def _write_readonly(self, box, text):
        """Write to a Text widget (works for both editable and disabled)."""
        box.config(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.config(state="disabled")

    def _write_ocr(self, text):
        """Write OCR result into the editable OCR box, clear placeholder."""
        self._ocr_placeholder_active = False
        self.ocr_box.config(fg=TEXT)
        self.ocr_box.delete("1.0", "end")
        self.ocr_box.insert("1.0", text)

    def _read_ocr(self):
        """Read OCR box, return empty string if placeholder is still active."""
        if self._ocr_placeholder_active:
            return ""
        return self.ocr_box.get("1.0", "end-1c").strip()

    def _ocr_focus_in(self, event):
        if self._ocr_placeholder_active:
            self.ocr_box.delete("1.0", "end")
            self.ocr_box.config(fg=TEXT)
            self._ocr_placeholder_active = False

    def _ocr_focus_out(self, event):
        content = self.ocr_box.get("1.0", "end-1c").strip()
        if not content:
            self.ocr_box.insert("1.0", "OCR will auto-fill here. If blank, type the student's answer manually.")
            self.ocr_box.config(fg=MUTED)
            self._ocr_placeholder_active = True

    def _read_text(self, box):
        """Read from a (possibly disabled) Text widget."""
        box.config(state="normal")
        content = box.get("1.0", "end-1c")
        box.config(state="disabled")
        return content

    def _set_status(self, msg, colour=TEXT):
        self.status_lbl.config(text=msg, fg=colour)

    def _update_final_badge(self, *args):
        """Called automatically whenever teacher_marks changes."""
        try:
            val = float(self.teacher_marks.get())
            self.final_badge.config(text=f"FINAL  {val}  / 5")
        except ValueError:
            # Non-numeric (e.g. the initial "—") — show dash
            self.final_badge.config(text="FINAL  —  / 5")


# ── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    try:
        ensure_ready(log=print)
    except Exception:
        pass

    app = App()
    app.mainloop()