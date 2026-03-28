"""
Chart Pattern Intelligence — Launcher
Starts both the FastAPI backend and Streamlit frontend.
"""

import subprocess
import sys
import os
import time
import signal

def main():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║       📊 Chart Pattern Intelligence v1.0        ║
    ║   Real-time pattern detection for NSE stocks    ║
    ╚══════════════════════════════════════════════════╝
    """)

    api_port = os.getenv("APP_PORT", "8000")
    streamlit_port = os.getenv("STREAMLIT_PORT", "8501")

    processes = []

    try:
        # Start FastAPI backend
        print(f"🚀 Starting API server on port {api_port}...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api.server:app",
             "--host", "0.0.0.0", "--port", api_port, "--reload"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        processes.append(api_proc)
        time.sleep(2)

        # Start Streamlit dashboard
        print(f"🖥️  Starting dashboard on port {streamlit_port}...")
        st_proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "frontend/dashboard.py",
             "--server.port", streamlit_port,
             "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        processes.append(st_proc)

        print(f"""
    ✅ All services started!

    📡 API Server:    http://localhost:{api_port}
       API Docs:      http://localhost:{api_port}/docs
    🖥️  Dashboard:     http://localhost:{streamlit_port}

    Press Ctrl+C to stop all services.
        """)

        # Wait for processes
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait(timeout=5)
        print("✅ All services stopped.")


if __name__ == "__main__":
    main()
