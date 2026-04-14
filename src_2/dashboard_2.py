import os, base64, json, requests, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from answer_key import answer_keys
from ollama_manager import ensure_ready

ENGINE_URL   = "http://localhost:11434/api/generate"
RESULTS_JSON = os.path.join(os.path.dirname(__file__), "results_2.json")
BIT_MAP      = {"a": 0, "b": 1, "c": 2}

# ── Analysis Engine ──────────────────────────────────────────
def encode_image(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_text(img_path):
    image_b64 = encode_image(img_path)
    payload = {
        "model": "minicpm-v",
        "prompt": "Read the handwritten text in this image. Output only what is written. Do not add anything.",
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024}
    }
    response = requests.post(ENGINE_URL, json=payload, timeout=600)
    return response.json().get("response", "").strip()

def analyze_answer_ai(extracted_text, model_answer, max_marks=5):
    prompt = f"""
    Compare the Student Answer with the Model Answer. Provide a detailed analysis.
    
    Model Answer: "{model_answer}"
    Student Answer: "{extracted_text}"
    
    Analyze for:
    1. Score out of {max_marks}.
    2. Missing keywords.
    3. Missing concepts.
    4. Broken or incorrect concepts.
    
    Output the result in valid JSON format ONLY:
    {{
        "score": <numeric_score>,
        "missing_keywords": ["kw1", "kw2"],
        "missing_concepts": ["concept1"],
        "broken_concepts": ["broken1"],
        "reasoning": "summary"
    }}
    """
    payload = {
        "model": "minicpm-v",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(ENGINE_URL, json=payload, timeout=600)
        return json.loads(response.json().get("response", "{}"))
    except:
        return {
            "score": 0,
            "missing_keywords": ["Error processing analysis"],
            "missing_concepts": [],
            "broken_concepts": [],
            "reasoning": "Could not connect to AI engine."
        }

# ── Storage ──────────────────────────────────────────────────
def load_results():
    if os.path.exists(RESULTS_JSON):
        try:
            with open(RESULTS_JSON) as f:
                return json.load(f)
        except: return []
    return []

def save_results(data):
    with open(RESULTS_JSON, "w") as f:
        json.dump(data, f, indent=2)

# ── Login Screen ─────────────────────────────────────────────
class LoginScreen(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.title("Teacher Login")
        self.geometry("400x300")
        self.configure(bg="#0f1117")
        self.center_window()
        
        tk.Label(self, text="Teacher Login", font=("Courier", 18, "bold"), 
                 bg="#0f1117", fg="#00e5ff").pack(pady=30)
        
        f = tk.Frame(self, bg="#0f1117")
        f.pack(pady=10)
        
        tk.Label(f, text="Username:", bg="#0f1117", fg="#aaa").grid(row=0, column=0, sticky="e", pady=5)
        self.user_ent = tk.Entry(f, bg="#1a1d27", fg="#fff", insertbackground="#fff", relief="flat")
        self.user_ent.grid(row=0, column=1, padx=10, pady=5)
        self.user_ent.insert(0, "teacher")
        
        tk.Label(f, text="Password:", bg="#0f1117", fg="#aaa").grid(row=1, column=0, sticky="e", pady=5)
        self.pass_ent = tk.Entry(f, show="*", bg="#1a1d27", fg="#fff", insertbackground="#fff", relief="flat")
        self.pass_ent.grid(row=1, column=1, padx=10, pady=5)
        self.pass_ent.insert(0, "admin")
        
        tk.Button(self, text="LOGIN", command=self.do_login, bg="#00e5ff", fg="#0f1117",
                  font=("Courier", 12, "bold"), relief="flat", padx=20).pack(pady=20)
        
        self.protocol("WM_DELETE_WINDOW", self.parent.destroy)

    def center_window(self):
        self.update_idletasks()
        w, h = 400, 300
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def do_login(self):
        u = self.user_ent.get()
        p = self.pass_ent.get()
        if u == "teacher" and p == "admin":
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error", "Invalid Credentials")

# ── Main Application ─────────────────────────────────────────
class App2(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("AI Copy Evaluator Pro - Dashboard 2")
        self.geometry("1400x850")
        self.configure(bg="#0f1117")
        
        # State
        self.results = load_results()
        self.current_img_path = None
        self.current_analysis = {}
        
        # Admin provided Metadata
        self.student_name = tk.StringVar(value="John Doe")
        self.roll_no = tk.StringVar(value="2021CSE001")
        self.semester = tk.StringVar(value="4th")
        self.subject = tk.StringVar(value="Universal Human Values")
        self.current_q_mark = tk.DoubleVar(value=5.0)
        
        LoginScreen(self, self._launch)

    def _launch(self):
        self.deiconify()
        self._build_ui()

    def _build_ui(self):
        # ── Top Bar (Admin Settings) ──
        top_bar = tk.Frame(self, bg="#1a1d27", height=80)
        top_bar.pack(fill="x", side="top", padx=10, pady=10)
        
        info_frame = tk.Frame(top_bar, bg="#1a1d27")
        info_frame.pack(side="left", padx=20)
        
        def add_info(label, var):
            f = tk.Frame(info_frame, bg="#1a1d27")
            f.pack(side="left", padx=15)
            tk.Label(f, text=label, font=("Courier", 9), bg="#1a1d27", fg="#555").pack(anchor="w")
            tk.Entry(f, textvariable=var, font=("Courier", 12, "bold"), bg="#1a1d27", 
                     fg="#00e5ff", relief="flat", width=15).pack()

        add_info("STUDENT NAME", self.student_name)
        add_info("ROLL NO", self.roll_no)
        add_info("SEM.", self.semester)
        
        # Subject needs more width for "Universal Human Values"
        fs = tk.Frame(info_frame, bg="#1a1d27")
        fs.pack(side="left", padx=15)
        tk.Label(fs, text="SUBJECT", font=("Courier", 9), bg="#1a1d27", fg="#555").pack(anchor="w")
        tk.Entry(fs, textvariable=self.subject, font=("Courier", 12, "bold"), bg="#1a1d27", 
                 fg="#00e5ff", relief="flat", width=25).pack()

        tk.Button(top_bar, text="📁 LOAD ANSWER", command=self._pick_image, bg="#00e5ff", 
                  fg="#0f1117", font=("Courier", 10, "bold"), relief="flat", padx=15).pack(side="right", padx=20)

        # ── Main Body (Split View) ──
        main_body = tk.Frame(self, bg="#0f1117")
        main_body.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Right Side: Analysis & Manual Controls (Packed first to ensure visibility)
        right_side = tk.Frame(main_body, bg="#0f1117", width=500)
        right_side.pack(side="right", fill="both", padx=10)
        right_side.pack_propagate(False)

        # Left Side: Image Viewer (Takes remaining space)
        left_side = tk.LabelFrame(main_body, text=" STUDENT COPY ", bg="#0f1117", fg="#00e5ff",
                                 font=("Courier", 10, "bold"), bd=1, relief="solid")
        left_side.pack(side="left", fill="both", expand=True, padx=5)
        
        self.img_label = tk.Label(left_side, bg="#0f1117", text="No image loaded")
        self.img_label.pack(fill="both", expand=True)

        # Extracted Text (Editable)
        tk.Label(right_side, text="EXTRACTED TEXT (Teacher can edit if OCR is bad)", 
                 bg="#0f1117", fg="#aaa", font=("Courier", 9)).pack(anchor="w", pady=(5,0))
        self.extracted_text_box = tk.Text(right_side, bg="#1a1d27", fg="#fff", font=("Courier", 10),
                                         height=10, relief="solid", bd=1, highlightthickness=1,
                                         highlightbackground="#333", insertbackground="#fff", wrap="word")
        self.extracted_text_box.pack(fill="x", pady=5)

        # Question Selection for Reference
        q_ref_frame = tk.Frame(right_side, bg="#0f1117")
        q_ref_frame.pack(fill="x", pady=5)
        tk.Label(q_ref_frame, text="Expected Answer For:", bg="#0f1117", fg="#aaa").pack(side="left")
        self.q_var = tk.StringVar(value="a")
        q_cb = ttk.Combobox(q_ref_frame, textvariable=self.q_var, values=["a", "b", "c"], width=5)
        q_cb.pack(side="left", padx=5)
        
        tk.Button(right_side, text="⚡ START EVALUATION", command=self._run_full_eval, 
                  bg="#f0a500", fg="#000", font=("Courier", 11, "bold"), relief="flat").pack(fill="x", pady=10)

        # Analysis Result
        self.analysis_frame = tk.LabelFrame(right_side, text=" AI ANALYSIS (Teacher can edit) ", bg="#0f1117", fg="#00e5ff",
                                           font=("Courier", 10, "bold"), bd=1, relief="solid")
        self.analysis_frame.pack(fill="both", expand=True, pady=5)
        
        self.analysis_text = tk.Text(self.analysis_frame, bg="#0f1117", fg="#ccc", font=("Courier", 10),
                                    relief="flat", wrap="word", insertbackground="#fff")
        self.analysis_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Manual Feedback/Override (Improved Layout to avoid "Squeezing")
        override_frame = tk.Frame(right_side, bg="#1a1d27", pady=15, bd=1, relief="ridge")
        override_frame.pack(fill="x", side="bottom", padx=5, pady=5)
        
        # Marks entry section
        m_frame = tk.Frame(override_frame, bg="#1a1d27", pady=5)
        m_frame.pack(fill="x", padx=15)
        
        tk.Label(m_frame, text="FINAL SCORE (OUT OF 5)", bg="#1a1d27", fg="#aaa", 
                 font=("Courier", 9)).pack(side="left")
        self.marks_ent = tk.Entry(m_frame, textvariable=self.current_q_mark, width=6, 
                                 font=("Courier", 18, "bold"), bg="#1a1d27", fg="#f0a500", 
                                 relief="solid", bd=1, justify="center", insertbackground="#fff")
        self.marks_ent.pack(side="right")
        
        # Save button (Full width for better interaction)
        tk.Button(override_frame, text="💾 SAVE VERIFIED EVALUATION", command=self._save_record, 
                  bg="#00c896", fg="#0f1117", font=("Courier", 11, "bold"), 
                  relief="flat", pady=8).pack(fill="x", padx=15, pady=(10,0))

        # Indicator Frame
        ind_frame = tk.Frame(self, bg="#0f1117")
        ind_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        self.status_lbl = tk.Label(ind_frame, text="Ready", bg="#0f1117", fg="#00e5ff", font=("Courier", 10, "bold"))
        self.status_lbl.pack(side="left")
        
        self.prog = ttk.Progressbar(ind_frame, mode="indeterminate", length=300)
        self.prog.pack(side="right", padx=10)
        
        st = ttk.Style()
        st.configure("TProgressbar", thickness=10, troughcolor="#1a1d27", background="#00e5ff")

    def _pick_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            self.current_img_path = path
            self._display_image(path)
            self.status_lbl.config(text=f"Loaded: {os.path.basename(path)}")
            # Auto start text extraction in background
            threading.Thread(target=self._auto_extract, args=(path,), daemon=True).start()

    def _display_image(self, path):
        img = Image.open(path)
        # Resize to fit frame
        w_box, h_box = 800, 700
        w, h = img.size
        ratio = min(w_box/w, h_box/h)
        new_w, new_h = int(w*ratio), int(h*ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=photo, text="")
        self.img_label.image = photo

    def _auto_extract(self, path):
        self.after(0, lambda: self.status_lbl.config(text="⏳ Extracting text..."))
        self.after(0, self.prog.start)
        try:
            text = extract_text(path)
            self.after(0, lambda: self._set_extracted(text))
            self.after(0, lambda: self.status_lbl.config(text="✅ Image Loaded."))
            self.after(0, self.prog.stop)
        except Exception as e:
            self.after(0, self.prog.stop)
            self.after(0, lambda: messagebox.showerror("OCR Error", str(e)))

    def _set_extracted(self, text):
        self.extracted_text_box.delete("1.0", "end")
        self.extracted_text_box.insert("1.0", text)

    def _run_full_eval(self):
        if not self.current_img_path:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        
        # Get potentially edited text
        final_text = self.extracted_text_box.get("1.0", "end-1c").strip()
        model_ans = answer_keys[BIT_MAP[self.q_var.get()]]
        
        self.status_lbl.config(text="⚡ AI is Analysing... please wait.")
        self.prog.start()
        threading.Thread(target=self._eval_thread, args=(final_text, model_ans), daemon=True).start()

    def _eval_thread(self, text, model_ans):
        try:
            analysis = analyze_answer_ai(text, model_ans)
            self.current_analysis = analysis
            self.after(0, lambda: self._update_analysis_ui(analysis))
            self.after(0, lambda: self.current_q_mark.set(analysis.get("score", 0)))
            self.after(0, lambda: self.status_lbl.config(text="✅ Analysis complete."))
            self.after(0, self.prog.stop)
        except Exception as e:
            self.after(0, self.prog.stop)
            self.after(0, lambda: messagebox.showerror("Analysis Error", str(e)))

    def _update_analysis_ui(self, data):
        self.analysis_text.delete("1.0", "end")
        
        def add(label, content):
            self.analysis_text.insert("end", f"{label}\n", ("bold",))
            if isinstance(content, list):
                for item in content:
                    self.analysis_text.insert("end", f" • {item}\n")
            else:
                self.analysis_text.insert("end", f" {content}\n")
            self.analysis_text.insert("end", "\n")

        self.analysis_text.tag_configure("bold", font=("Courier", 10, "bold"), foreground="#00e5ff")
        self.analysis_text.tag_configure("score", font=("Courier", 14, "bold"), foreground="#f0a500")
        
        # Make the score VERY visible in the analysis box
        self.analysis_text.insert("end", "AI SUGGESTED SCORE: ", ("bold",))
        self.analysis_text.insert("end", f"{data.get('score', 0)} / 5\n\n", ("score",))
        add("MISSING KEYWORDS", data.get("missing_keywords", []))
        add("MISSING CONCEPTS", data.get("missing_concepts", []))
        add("BROKEN CONCEPTS", data.get("broken_concepts", []))
        add("AI REASONING", data.get("reasoning", "N/A"))

    def _save_record(self):
        if not self.current_img_path: return
        
        # Grab updated content from text boxes (in case teacher edited them)
        final_ocr_text = self.extracted_text_box.get("1.0", "end-1c").strip()
        final_analysis_text = self.analysis_text.get("1.0", "end-1c").strip()
        
        record = {
            "student": self.student_name.get(),
            "roll_no": self.roll_no.get(),
            "semester": self.semester.get(),
            "subject": self.subject.get(),
            "question": self.q_var.get(),
            "marks_given": self.current_q_mark.get(),
            "verified_extracted_text": final_ocr_text,
            "verified_analysis": final_analysis_text, # Saves what the teacher actually sees/edits
            "original_ai_raw": self.current_analysis, # Keep for auditing
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(record)
        save_results(self.results)
        messagebox.showinfo("Success", "Evaluation saved successfully!")

if __name__ == "__main__":
    # Standard boot check
    try:
        # We don't want the splash from App1, just a simple check
        ensure_ready(log=print)
    except:
        pass
    
    app = App2()
    app.mainloop()
