import os, subprocess, urllib.request, time, tkinter as tk
from tkinter import ttk
from threading import Thread

OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_EXE = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")

class Setup(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Copy Evaluator — First Time Setup")
        self.geometry("480x260")
        self.resizable(False, False)
        self.configure(bg="#0f1117")
        tk.Label(self, text="Setting up AI Copy Evaluator",
                 font=("Courier", 15, "bold"), bg="#0f1117", fg="#00e5ff").pack(pady=(30,5))
        tk.Label(self, text="This runs once. Please wait...",
                 font=("Courier", 10), bg="#0f1117", fg="#aaa").pack()
        self.status = tk.Label(self, text="", font=("Courier", 10),
                               bg="#0f1117", fg="#f0a500")
        self.status.pack(pady=10)
        self.bar = ttk.Progressbar(self, length=400, mode="indeterminate")
        self.bar.pack()
        self.bar.start()
        Thread(target=self._run, daemon=True).start()

    def _log(self, msg):
        self.status.config(text=msg)
        self.update()

    def _run(self):
        try:
            if not os.path.exists(OLLAMA_EXE):
                self._log("Downloading Ollama...")
                tmp = os.path.join(os.environ["TEMP"], "OllamaSetup.exe")
                urllib.request.urlretrieve(OLLAMA_URL, tmp)
                self._log("Installing Ollama silently...")
                subprocess.run([tmp, "/S"], check=True)
                time.sleep(5)

            self._log("Starting Ollama...")
            subprocess.Popen([OLLAMA_EXE, "serve"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(4)

            self._log("Downloading minicpm-v model (~5GB)...")
            subprocess.run([OLLAMA_EXE, "pull", "minicpm-v"],
                           creationflags=subprocess.CREATE_NO_WINDOW)

            # Register auto-start on Windows boot
            startup = os.path.expanduser(
                r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")
            with open(os.path.join(startup, "ollama_service.bat"), "w") as f:
                f.write(f'@echo off\nstart "" /min "{OLLAMA_EXE}" serve\n')

            self.bar.stop()
            self._log("Setup complete! Run dashboard.py to start.")
        except Exception as e:
            self.bar.stop()
            self._log(f"Error: {e}")

if __name__ == "__main__":
    Setup().mainloop()
