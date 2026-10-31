"""Servidor independiente FISMA. Conserva la configuración y claves locales."""
import os
from pathlib import Path
import socket
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

def main():
    from app import app, update_template_grid_config, load_settings_config, CONFIG_PATH
    from omr_processor import save_claves_records
    from waitress import serve
    cfg=load_settings_config()
    update_template_grid_config(cfg["num_questions"],cfg["num_alternatives"])
    if not Path(CONFIG_PATH).exists():
        save_claves_records(CONFIG_PATH,[],cfg["num_questions"])
    port=int(os.environ.get("OMR_FISMA_PORT","5026"))
    try:
        hostname=socket.gethostbyname(socket.gethostname())
    except OSError:
        hostname="127.0.0.1"
    print(f"OMR FISMA A5: http://127.0.0.1:{port}/",flush=True)
    print(f"Red local: http://{hostname}:{port}/",flush=True)
    if os.environ.get("OMR_NO_BROWSER")!="1":
        threading.Timer(1.2,lambda:webbrowser.open(f"http://127.0.0.1:{port}/")).start()
    serve(app,host="0.0.0.0",port=port,threads=4)

if __name__=="__main__": main()
