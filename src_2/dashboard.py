import os, base64, json, requests, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from rapidfuzz import fuzz
from datetime import datetime
from answer_key import answer_keys
from ollama_manager import ensure_ready

ENGINE_URL   = "http://localhost:11434/api/generate"
RESULTS_JSON = os.path.join(os.path.dirname(__file__), "results.json")
BIT_MAP      = {"a": 0, "b": 1, "c": 2}

# ── your exact working pipeline ──────────────────────────────
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

def evaluate_answer(extracted_text, model_answer, max_marks=5):
    score = fuzz.token_set_ratio(extracted_text.lower(), model_answer.lower())
    marks = round((score / 100) * max_marks, 1)
    if score >= 80:   grade = "Excellent"
    elif score >= 60: grade = "Good"
    elif score >= 40: grade = "Average"
    else:             grade = "Poor"
    return {"similarity": round(score, 2), "marks": marks,
            "max_marks": max_marks, "grade": grade}

# ── storage ──────────────────────────────────────────────────
def load_results():
    if os.path.exists(RESULTS_JSON):
        with open(RESULTS_JSON) as f:
            return json.load(f)
    return []

def save_results(data):
    with open(RESULTS_JSON, "w") as f:
        json.dump(data, f, indent=2)

# ── splash ───────────────────────────────────────────────────
class Splash(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg="#0f1117")
        w, h = 400, 180
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        tk.Label(self, text="AI Copy Evaluator",
                 font=("Courier", 18, "bold"), bg="#0f1117", fg="#00e5ff").pack(pady=(28,4))
        self.msg = tk.Label(self, text="Starting...",
                            font=("Courier", 10), bg="#0f1117", fg="#f0a500")
        self.msg.pack(pady=4)
        self.bar = ttk.Progressbar(self, length=340, mode="indeterminate")
        self.bar.pack(pady=10)
        self.bar.start()

    def say(self, text):
        self.msg.config(text=text)
        self.update()

    def close(self):
        self.bar.stop()
        self.destroy()

# ── main app ─────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("AI Copy Evaluator")
        self.geometry("1100x760")
        self.minsize(900, 620)
        self.configure(bg="#0f1117")
        self.results      = load_results()
        self.student_name = tk.StringVar()
        self.q_rows       = []
        self.batch_q_rows = []
        self._pending     = []

        splash = Splash(self)
        threading.Thread(target=self._boot, args=(splash,), daemon=True).start()

    def _boot(self, splash):
        try:
            ensure_ready(log=lambda m: self.after(0, lambda msg=m: splash.say(msg)))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Startup Error", f"{e}\n\nRun setup.py first."))
            self.after(0, self.destroy)
            return
        self.after(0, splash.close)
        self.after(0, self._launch)

    def _launch(self):
        self._build_ui()
        self.deiconify()

    # ── ui ───────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg="#0f1117")
        hdr.pack(fill="x", padx=20, pady=(14,4))
        tk.Label(hdr, text="AI Copy Evaluator",
                 font=("Courier", 20, "bold"), bg="#0f1117", fg="#00e5ff").pack(side="left")
        tk.Label(hdr, text="  offline · core-engine · optimized",
                 font=("Courier", 9), bg="#0f1117", fg="#444").pack(side="left")

        st = ttk.Style(self)
        st.theme_use("default")
        st.configure("TNotebook",     background="#0f1117", borderwidth=0)
        st.configure("TNotebook.Tab", background="#1a1d27", foreground="#777",
                     font=("Courier", 10, "bold"), padding=[14,6])
        st.map("TNotebook.Tab",
               background=[("selected","#00e5ff")],
               foreground=[("selected","#0f1117")])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=4)
        self.te = tk.Frame(nb, bg="#0f1117")
        self.tb = tk.Frame(nb, bg="#0f1117")
        self.tr = tk.Frame(nb, bg="#0f1117")
        nb.add(self.te, text="  Evaluate  ")
        nb.add(self.tb, text="  Batch  ")
        nb.add(self.tr, text="  Results  ")
        self._eval_tab()
        self._batch_tab()
        self._results_tab()

    # ── evaluate tab ─────────────────────────────────────────
    def _eval_tab(self):
        p = self.te
        r0 = tk.Frame(p, bg="#0f1117"); r0.pack(fill="x", padx=15, pady=(10,5))
        tk.Label(r0, text="Student name:", bg="#0f1117", fg="#aaa",
                 font=("Courier",10)).pack(side="left")
        tk.Entry(r0, textvariable=self.student_name, bg="#1a1d27", fg="#fff",
                 font=("Courier",11), insertbackground="#fff",
                 relief="flat", width=28).pack(side="left", padx=8)

        qf = tk.LabelFrame(p, text=" Questions ",
                           bg="#0f1117", fg="#00e5ff",
                           font=("Courier",10,"bold"), bd=1, relief="solid")
        qf.pack(fill="x", padx=15, pady=5)
        self._qfi = tk.Frame(qf, bg="#0f1117")
        self._qfi.pack(fill="x", padx=5, pady=5)
        bf = tk.Frame(qf, bg="#0f1117"); bf.pack(fill="x", padx=5, pady=(0,8))
        self._btn(bf, "+ Add",    self._add_q,    "#00e5ff","#0f1117").pack(side="left",padx=4)
        self._btn(bf, "- Remove", self._rem_q,    "#ff4d6d","#fff"   ).pack(side="left",padx=4)
        self._add_q()

        self._btn(p, "⚡  Extract & Evaluate", self._run_eval,
                  "#00e5ff","#0f1117", big=True).pack(pady=8)
        self.estatus = tk.Label(p, text="", bg="#0f1117", fg="#f0a500",
                                font=("Courier",10))
        self.estatus.pack()

        rf = tk.Frame(p, bg="#1a1d27"); rf.pack(fill="both", expand=True, padx=15, pady=(4,10))
        self.rtext = tk.Text(rf, bg="#1a1d27", fg="#ccc", font=("Courier",10),
                             relief="flat", wrap="word", state="disabled")
        sb = ttk.Scrollbar(rf, command=self.rtext.yview)
        self.rtext.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.rtext.pack(fill="both", expand=True, padx=8, pady=8)
        self._btn(p, "💾  Save", self._save, "#00c896","#0f1117").pack(pady=(0,10))

    def _add_q(self):
        idx = len(self.q_rows)+1
        row = tk.Frame(self._qfi, bg="#0f1117"); row.pack(fill="x", pady=3)
        tk.Label(row, text=f"Q{idx}:", bg="#0f1117", fg="#00e5ff",
                 font=("Courier",10,"bold"), width=3).pack(side="left")
        bv = tk.StringVar(value="a")
        ttk.Combobox(row, textvariable=bv, values=["a","b","c"],
                     width=4, state="readonly").pack(side="left", padx=4)
        tk.Label(row, text="Marks:", bg="#0f1117", fg="#aaa",
                 font=("Courier",10)).pack(side="left", padx=(8,2))
        mv = tk.IntVar(value=5)
        tk.Spinbox(row, from_=1, to=20, textvariable=mv, width=4,
                   bg="#1a1d27", fg="#fff", buttonbackground="#1a1d27",
                   font=("Courier",10), relief="flat").pack(side="left", padx=4)
        iv = tk.StringVar()
        il = tk.Label(row, text="No image", bg="#0f1117", fg="#555",
                      font=("Courier",9), width=24, anchor="w")
        il.pack(side="left", padx=4)
        def pick(i=iv, l=il):
            path = filedialog.askopenfilename(
                filetypes=[("Images","*.jpg *.jpeg *.png")])
            if path: i.set(path); l.config(text=os.path.basename(path), fg="#00e5ff")
        self._btn(row, "📷 Pick", pick, "#222","#00e5ff", small=True).pack(side="left")
        self.q_rows.append((bv, mv, iv))

    def _rem_q(self):
        if len(self.q_rows) > 1:
            self.q_rows.pop()
            ch = self._qfi.winfo_children()
            if ch: ch[-1].destroy()

    def _run_eval(self):
        if not self.student_name.get().strip():
            messagebox.showwarning("Missing","Enter student name."); return
        for i,(bv,mv,iv) in enumerate(self.q_rows):
            if not iv.get():
                messagebox.showwarning("Missing",f"Pick image for Q{i+1}."); return
        self.estatus.config(text="⏳ Processing...")
        self._set_r("Running...\n")
        threading.Thread(target=self._eval_thread, daemon=True).start()

    def _eval_thread(self):
        student = self.student_name.get().strip()
        total_m, total_mx = 0, 0
        lines = [f"Student : {student}",
                 f"Date    : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 "="*54]
        records = []
        for i,(bv,mv,iv) in enumerate(self.q_rows):
            q, bit, mx, img = f"Q{i+1}", bv.get(), mv.get(), iv.get()
            model_ans = answer_keys[BIT_MAP[bit]]
            self.after(0, lambda q=q,b=bit:
                       self.estatus.config(text=f"⏳ {q} part {b.upper()}..."))
            try:
                extracted = extract_text(img)
                ev = evaluate_answer(extracted, model_ans, mx)
                total_m += ev["marks"]; total_mx += mx
                lines += [
                    f"\n{q} (Part {bit.upper()}) — {os.path.basename(img)}",
                    f"  Extracted  : {extracted[:110]}{'...' if len(extracted)>110 else ''}",
                    f"  Similarity : {ev['similarity']}%",
                    f"  Marks      : {ev['marks']} / {mx}",
                    f"  Grade      : {ev['grade']}",
                ]
                records.append({
                    "student":student,"question":q,"bit":bit,
                    "img_path":img,"extracted":extracted,
                    "model_answer":model_ans,
                    "similarity":ev["similarity"],
                    "marks":ev["marks"],"max_marks":mx,
                    "grade":ev["grade"],
                    "timestamp":datetime.now().isoformat()
                })
            except requests.exceptions.ConnectionError:
                lines.append(f"\n{q} ERROR: Core Engine not active.")
            except Exception as e:
                lines.append(f"\n{q} ERROR: {e}")

        pct = round(total_m/total_mx*100,1) if total_mx else 0
        lines += ["","="*54,
                  f"TOTAL : {total_m} / {total_mx}  ({pct}%)",
                  f"GRADE : {'Excellent' if pct>=80 else 'Good' if pct>=60 else 'Average' if pct>=40 else 'Poor'}"]
        self._pending = records
        self.after(0, lambda: self._set_r("\n".join(lines)))
        self.after(0, lambda: self.estatus.config(text="✅ Done!"))

    def _save(self):
        if not self._pending:
            messagebox.showwarning("Nothing","Run evaluation first."); return
        self.results.extend(self._pending)
        save_results(self.results)
        self._refresh()
        messagebox.showinfo("Saved",f"{len(self._pending)} records saved.")
        self._pending = []

    # ── batch tab ────────────────────────────────────────────
    def _batch_tab(self):
        p = self.tb
        tk.Label(p, text="Process entire folder of images at once",
                 bg="#0f1117", fg="#aaa", font=("Courier",11)).pack(pady=(14,5))

        qf = tk.LabelFrame(p, text=" Questions (part + marks) ",
                           bg="#0f1117", fg="#00e5ff",
                           font=("Courier",10,"bold"), bd=1, relief="solid")
        qf.pack(fill="x", padx=15, pady=6)
        self._bqi = tk.Frame(qf, bg="#0f1117"); self._bqi.pack(fill="x", padx=5, pady=5)
        bf = tk.Frame(qf, bg="#0f1117"); bf.pack(fill="x", padx=5, pady=(0,8))
        self._btn(bf, "+ Add Question", self._batch_add_q, "#00e5ff","#0f1117").pack(side="left",padx=4)
        self._batch_add_q()

        ff = tk.Frame(p, bg="#0f1117"); ff.pack(fill="x", padx=15, pady=5)
        self.bfolder = tk.StringVar()
        tk.Label(ff, text="Folder:", bg="#0f1117", fg="#aaa",
                 font=("Courier",10)).pack(side="left")
        tk.Entry(ff, textvariable=self.bfolder, bg="#1a1d27", fg="#fff",
                 font=("Courier",10), relief="flat", width=48).pack(side="left", padx=6)
        self._btn(ff, "Browse", self._pick_folder, "#333","#00e5ff", small=True).pack(side="left")

        tk.Label(p, text="Images matched to questions by sorted filename order.",
                 bg="#0f1117", fg="#555", font=("Courier",9)).pack(pady=2)
        self._btn(p, "⚡  Run Batch", self._run_batch,
                  "#00e5ff","#0f1117", big=True).pack(pady=8)
        self.bstatus = tk.Label(p, text="", bg="#0f1117", fg="#f0a500",
                                font=("Courier",10))
        self.bstatus.pack()
        self.bprog = ttk.Progressbar(p, length=580, mode="determinate")
        self.bprog.pack(pady=4)

        lf = tk.Frame(p, bg="#1a1d27"); lf.pack(fill="both", expand=True, padx=15, pady=(4,10))
        self.blog = tk.Text(lf, bg="#1a1d27", fg="#ccc", font=("Courier",9),
                            relief="flat", wrap="word", state="disabled")
        sb = ttk.Scrollbar(lf, command=self.blog.yview)
        self.blog.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.blog.pack(fill="both", expand=True, padx=8, pady=8)

    def _batch_add_q(self):
        idx = len(self.batch_q_rows)+1
        row = tk.Frame(self._bqi, bg="#0f1117"); row.pack(fill="x", pady=2)
        tk.Label(row, text=f"Q{idx}:", bg="#0f1117", fg="#00e5ff",
                 font=("Courier",10,"bold"), width=3).pack(side="left")
        bv = tk.StringVar(value="a")
        ttk.Combobox(row, textvariable=bv, values=["a","b","c"],
                     width=4, state="readonly").pack(side="left", padx=4)
        tk.Label(row, text="Marks:", bg="#0f1117", fg="#aaa",
                 font=("Courier",10)).pack(side="left", padx=(8,2))
        mv = tk.IntVar(value=5)
        tk.Spinbox(row, from_=1, to=20, textvariable=mv, width=4,
                   bg="#1a1d27", fg="#fff", buttonbackground="#1a1d27",
                   font=("Courier",10), relief="flat").pack(side="left")
        self.batch_q_rows.append((bv, mv))

    def _pick_folder(self):
        f = filedialog.askdirectory()
        if f: self.bfolder.set(f)

    def _run_batch(self):
        folder = self.bfolder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No Folder","Select a valid folder."); return
        self.bstatus.config(text="⏳ Starting...")
        threading.Thread(target=self._batch_thread, daemon=True).start()

    def _batch_thread(self):
        folder  = self.bfolder.get().strip()
        qcount  = len(self.batch_q_rows)
        exts    = ('.jpg','.jpeg','.png')
        images  = sorted([f for f in os.listdir(folder) if f.lower().endswith(exts)])
        if not images:
            self.after(0, lambda: self.bstatus.config(text="No images found.")); return
        total   = len(images)
        records = []
        self.after(0, lambda: self.bprog.configure(maximum=total, value=0))
        for i, fname in enumerate(images):
            img_path  = os.path.join(folder, fname)
            q_idx     = i % qcount
            bv, mv    = self.batch_q_rows[q_idx]
            bit       = bv.get()
            mx        = mv.get()
            model_ans = answer_keys[BIT_MAP[bit]]
            student   = f"Student_{(i//qcount)+1}"
            ql        = f"Q{q_idx+1}"
            self.after(0, lambda s=student,f=fname:
                       self.bstatus.config(text=f"⏳ {s} — {f}"))
            try:
                extracted = extract_text(img_path)
                ev = evaluate_answer(extracted, model_ans, mx)
                line = (f"[{student}] {ql}({bit.upper()}) | {fname} | "
                        f"Marks:{ev['marks']}/{mx} | {ev['grade']} | {ev['similarity']}%\n")
                self.after(0, lambda l=line: self._blog_append(l))
                records.append({
                    "student":student,"question":ql,"bit":bit,
                    "img_path":img_path,"extracted":extracted,
                    "model_answer":model_ans,"similarity":ev["similarity"],
                    "marks":ev["marks"],"max_marks":mx,
                    "grade":ev["grade"],"timestamp":datetime.now().isoformat()
                })
            except Exception as e:
                self.after(0, lambda f=fname,e=e: self._blog_append(f"ERROR {f}: {e}\n"))
            self.after(0, lambda v=i+1: self.bprog.configure(value=v))
        self.results.extend(records)
        save_results(self.results)
        self._refresh()
        self.after(0, lambda: self.bstatus.config(
            text=f"✅ Done! {len(records)} images processed."))

    def _blog_append(self, text):
        self.blog.configure(state="normal")
        self.blog.insert("end", text)
        self.blog.see("end")
        self.blog.configure(state="disabled")

    # ── results tab ──────────────────────────────────────────
    def _results_tab(self):
        p = self.tr
        ctrl = tk.Frame(p, bg="#0f1117"); ctrl.pack(fill="x", padx=15, pady=10)
        self._btn(ctrl,"🔄 Refresh",   self._refresh,       "#333",   "#00e5ff",small=True).pack(side="left",padx=4)
        self._btn(ctrl,"📊 Export CSV",self._export_csv,    "#00c896","#0f1117", small=True).pack(side="left",padx=4)
        self._btn(ctrl,"🗑 Clear All", self._clear_results, "#ff4d6d","#fff",    small=True).pack(side="left",padx=4)
        self.stats = tk.Label(p, text="", bg="#0f1117", fg="#aaa", font=("Courier",10))
        self.stats.pack(pady=3)

        cols = ("Student","Q","Part","File","Marks","Max","Grade","Similarity%","Date")
        self.tree = ttk.Treeview(p, columns=cols, show="headings")
        st = ttk.Style()
        st.configure("Treeview", background="#1a1d27", foreground="#ccc",
                     fieldbackground="#1a1d27", font=("Courier",9), rowheight=22)
        st.configure("Treeview.Heading", background="#0f1117", foreground="#00e5ff",
                     font=("Courier",9,"bold"))
        st.map("Treeview", background=[("selected","#00e5ff")],
               foreground=[("selected","#0f1117")])
        for col,w in zip(cols,[120,45,45,160,55,45,80,90,130]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        vsb = ttk.Scrollbar(p, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(p, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill="both", expand=True, padx=15, pady=(4,0))
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._refresh()

    def _refresh(self):
        self.results = load_results()
        for r in self.tree.get_children(): self.tree.delete(r)
        for r in self.results:
            self.tree.insert("","end", values=(
                r.get("student",""), r.get("question",""),
                r.get("bit","").upper(),
                os.path.basename(r.get("img_path","")),
                r.get("marks",""), r.get("max_marks",""),
                r.get("grade",""), f"{r.get('similarity',0)}%",
                r.get("timestamp","")[:16]))
        if self.results:
            avg = round(sum(r.get("similarity",0) for r in self.results)/len(self.results),1)
            self.stats.config(text=f"Total: {len(self.results)} records  |  Avg similarity: {avg}%")

    def _export_csv(self):
        if not self.results:
            messagebox.showinfo("Empty","No results."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV","*.csv")])
        if not path: return
        import csv
        keys = ["student","question","bit","img_path","extracted",
                "model_answer","similarity","marks","max_marks","grade","timestamp"]
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader(); w.writerows(self.results)
        messagebox.showinfo("Exported",f"Saved to {path}")

    def _clear_results(self):
        if messagebox.askyesno("Confirm","Delete all results?"):
            self.results = []
            save_results(self.results)
            self._refresh()

    # ── helpers ──────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg, fg, big=False, small=False):
        size = 13 if big else (9 if small else 11)
        pad  = (14,10) if big else (8,4)
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                         font=("Courier",size,"bold"), relief="flat",
                         activebackground=fg, activeforeground=bg,
                         padx=pad[0], pady=pad[1], cursor="hand2")

    def _set_r(self, text):
        self.rtext.configure(state="normal")
        self.rtext.delete("1.0","end")
        self.rtext.insert("1.0", text)
        self.rtext.configure(state="disabled")

if __name__ == "__main__":
    App().mainloop()
