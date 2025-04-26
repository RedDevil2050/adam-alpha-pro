import os
import subprocess
import sys
import time

RESTART_FLAG = os.path.join(os.path.dirname(__file__), ".restart")

def check_restart():
    if os.path.exists(RESTART_FLAG):
        os.remove(RESTART_FLAG)
        return True
    return False

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    while True:
        if len(sys.argv) > 1 and sys.argv[1] == "--direct":
            import app
            app.main()
            if not check_restart():
                break
        else:
            subprocess.run(["streamlit", "run", app_path])
            if not check_restart():
                break
        time.sleep(1)  # Small delay before restart
