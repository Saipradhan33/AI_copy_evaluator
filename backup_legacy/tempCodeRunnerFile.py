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

        self.bar = ttk.Progressbar(self, length=400, mode="indeterminate")
        self.bar.pack()
        self.bar.start()

        Thread(target=self._run, daemon=True).start()

    def _log(self, msg):
        self.status.config(text=msg[:60])  # limit length for UI
        self.update()

    def _run(self):
        try:
            # ── Step 1: Install engine ───────────────────────
            if not os.path.exists(ENGINE_EXE):
                self._log("Installing Core Engine...")
                tmp = os.path.join(os.environ["TEMP"], "engine_setup.exe")
                urllib.request.urlretrieve(ENGINE_URL, tmp)

                self._log("Setting up runtime...")
                subprocess.run([tmp, "/S"], check=True)
                time.sleep(5)

            # ── Step 2: Start engine ─────────────────────────
            self._log("Starting AI runtime...")
            subprocess.Popen([ENGINE_EXE, "serve"],
                            creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(4)

            # ── Step 3: Download model (WITH PROGRESS UI) ─────
            self._log("Preparing AI model (first run)...")

            self.bar.config(mode="determinate", maximum=100, value=0)

            progress = 0

            process = subprocess.Popen(
                [ENGINE_EXE, "pull", "minicpm-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                text = line.strip()

                # show logs
                self._log(text)

                # fake progress increase (smooth UX)
                if progress < 90:
                    progress += 1
                    self.bar["value"] = progress

                self.update()

            # finish progress
            self.bar["value"] = 100

            # ── Step 4: Auto-start on boot ──────────────────
            startup = os.path.expanduser(
                r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")

            with open(os.path.join(startup, "core_engine_service.bat"), "w") as f:
                f.write(f'@echo off\nstart "" /min "{ENGINE_EXE}" serve\n')

            self.bar.stop()
            self._log("Setup complete! Run dashboard.py")

        except Exception as e:
            self.bar.stop()
            self._log(f"Error: {e}")

if __name__ == "__main__":
    Setup().mainloop()