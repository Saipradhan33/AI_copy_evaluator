# ============================================================
# engine_manager.py — Auto-starts Neural Engine if not running
# Imported by the main app
# ============================================================
import os, subprocess, time, requests

ENGINE_EXE  = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
ENGINE_URL  = "http://localhost:11434"
MODEL_NAME  = "minicpm-v"

def is_engine_running():
    try:
        r = requests.get(f"{ENGINE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False

def is_model_available():
    try:
        r = requests.get(f"{ENGINE_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(MODEL_NAME in m for m in models)
    except:
        return False

def start_engine():
    if not os.path.exists(ENGINE_EXE):
        raise FileNotFoundError(
            "Neural Engine not found. Please run system setup first.")

    subprocess.Popen([ENGINE_EXE, "serve"],
                     creationflags=subprocess.CREATE_NO_WINDOW)

    # Wait up to 15 seconds for it to start
    for _ in range(15):
        time.sleep(1)
        if is_engine_running():
            return True
    raise TimeoutError("Neural Engine failed to start in time.")

def ensure_ready(status_callback=None):
    """
    Call this at app startup.
    status_callback(msg) updates UI with progress messages.
    """
    def log(msg):
        if status_callback:
            status_callback(msg)
        print(msg)

    if not is_ollama_running():
        log("Starting Neural Engine...")
        start_ollama()
        log("Neural Engine active.")
    else:
        log("Neural Engine already active.")

    if not is_model_available():
        log(f"Fetching Data package (first time only)...")
        subprocess.run([ENGINE_EXE, "pull", MODEL_NAME],
                       creationflags=subprocess.CREATE_NO_WINDOW)
        log("Data package ready.")
    else:
        log("System state: READY.")
