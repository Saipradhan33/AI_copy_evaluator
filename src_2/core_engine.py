import os, subprocess, time, requests

ENGINE_EXE = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
ENGINE_URL = "http://localhost:11434"
MODEL      = "minicpm-v"

def is_running():
    try:
        return requests.get(f"{ENGINE_URL}/api/tags", timeout=2).status_code == 200
    except:
        return False

def is_model_ready():
    try:
        models = requests.get(f"{ENGINE_URL}/api/tags", timeout=2).json().get("models", [])
        return any(MODEL in m["name"] for m in models)
    except:
        return False

def start_engine():
    if not os.path.exists(ENGINE_EXE):
        raise FileNotFoundError("Core Engine not installed. Run setup first.")

    subprocess.Popen([ENGINE_EXE, "serve"],
                     creationflags=subprocess.CREATE_NO_WINDOW)

    for _ in range(20):
        time.sleep(1)
        if is_running():
            return
    raise TimeoutError("Core Engine failed to start.")

def ensure_ready(log=None):
    def say(msg):
        if log: log(msg)

    if not is_running():
        say("Starting Core Engine...")
        start_engine()
        say("Core Engine active.")
    else:
        say("Core Engine already running.")

    if not is_model_ready():
        say("Preparing AI model (first run)...")
        subprocess.run([ENGINE_EXE, "pull", MODEL],
                       creationflags=subprocess.CREATE_NO_WINDOW)
    say("System READY.")