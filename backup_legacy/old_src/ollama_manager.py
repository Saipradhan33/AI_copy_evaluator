import os, subprocess, time, requests

OLLAMA_EXE = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
OLLAMA_URL = "http://localhost:11434"
MODEL      = "minicpm-v"

def is_running():
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).status_code == 200
    except:
        return False

def is_model_ready():
    try:
        models = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).json().get("models", [])
        return any(MODEL in m["name"] for m in models)
    except:
        return False

def start_ollama():
    if not os.path.exists(OLLAMA_EXE):
        raise FileNotFoundError("Ollama not installed. Run setup.py first.")
    subprocess.Popen([OLLAMA_EXE, "serve"],
                     creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(20):
        time.sleep(1)
        if is_running():
            return
    raise TimeoutError("Ollama failed to start.")

def ensure_ready(log=None):
    def say(msg):
        if log: log(msg)

    if not is_running():
        say("Starting Ollama...")
        start_ollama()
        say("Ollama started.")
    else:
        say("Ollama ready.")

    if not is_model_ready():
        say(f"Loading {MODEL} model...")
        subprocess.run([OLLAMA_EXE, "pull", MODEL],
                       creationflags=subprocess.CREATE_NO_WINDOW)
    say("Model ready.")
