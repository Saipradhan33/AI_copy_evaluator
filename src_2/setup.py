import os, subprocess, urllib.request, time, tkinter as tk
from tkinter import ttk
from threading import Thread

ENGINE_URL = "https://ollama.com/download/OllamaSetup.exe"
ENGINE_EXE = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")

class Setup(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Copy Evaluator — First Time Setup")
        self.geometry("480x260")
        self.resizable(False, False)
        self.configure(bg="#0f1117")

        tk.Label(self, text="Initializing AI System",
                 font=("Courier", 15, "bold"),
                 bg="#0f1117", fg="#00e5ff").pack(pady=(30,5))

        tk.Label(self, text="This runs once. Please wait...",
                 font=("Courier", 10),
                 bg="#0f1117", fg="#aaa").pack()

        self.status = tk.Label(self, text="",
                               font=("Courier", 10),
                               bg="#0f1117", fg="#f0a500")
        self.status.pack(pady=10)

        self.bar = ttk.Progressbar(self, length=400, mode="determinate")
        self.bar.pack()

        Thread(target=self._run, daemon=True).start()

    def _log(self, msg):
        self.status.config(text=msg[:60])
        self.update()

    # ✅ Download with real progress
    def download_with_progress(self, url, path):
        def report(block_num, block_size, total_size):
            if total_size > 0:
                percent = int(block_num * block_size * 100 / total_size)
                self.bar["value"] = percent
                self._log(f"Installing Core Engine... {percent}%")
                self.update()
        urllib.request.urlretrieve(url, path, reporthook=report)

    def _run(self):
        try:
            # ── Step 1: Install engine ───────────────────────
            if not os.path.exists(ENGINE_EXE):
                tmp = os.path.join(os.environ["TEMP"], "engine_setup.exe")

                self.bar["value"] = 0
                self.download_with_progress(ENGINE_URL, tmp)

                self._log("Setting up runtime...")
                subprocess.run([tmp, "/S"], check=True)
                time.sleep(5)

            # ── Step 2: Start engine ─────────────────────────
            self._log("Starting AI runtime...")
            subprocess.Popen([ENGINE_EXE, "serve"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(4)

            # ── Step 3: Model download ───────────────────────
            self._log("Preparing AI model (first run)...")
            self.bar["value"] = 0

            process = subprocess.Popen(
                [ENGINE_EXE, "pull", "minicpm-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            progress = 0
            for line in process.stdout:
                self._log(line.strip())

                if progress < 95:
                    progress += 1
                    self.bar["value"] = progress

                self.update()

            self.bar["value"] = 100

            # ── Step 4: Auto-start ──────────────────────────
            startup = os.path.expanduser(
                r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")

            with open(os.path.join(startup, "core_engine_service.bat"), "w") as f:
                f.write(f'@echo off\nstart "" /min "{ENGINE_EXE}" serve\n')

            self._log("Setup complete! Run dashboard.py")

        except Exception as e:
            self._log(f"Error: {e}")

if __name__ == "__main__":
    Setup().mainloop()