# Robotic Sorting System

A full-stack automated robotic sorting platform that integrates computer vision, hardware control, and a modern web interface to efficiently scan, inspect, and sort objects.

## 🌟 Features

- **Computer Vision Pipeline**: Real-time damage and defect detection using Caffe models, plus QR code scanning.
- **Hardware Control**: Integrated control for conveyor belts and robotic arms via serial communication.
- **Modern Dashboard**: Real-time metrics, live camera feed, and control panel built with React, Vite, and TailwindCSS.
- **FastAPI Backend**: High-performance asynchronous API and WebSocket support.

---

## 🏗 System Architecture

- **Frontend**: React.js, TypeScript, Vite, TailwindCSS (Managed with Bun)
- **Backend**: Python, FastAPI, SQLite
- **Vision**: OpenCV, PyZbar (for QR detection), DNN Modules

---

## 📋 Prerequisites

Before setting up the project, ensure you have the following installed:

1. **Python 3.9+** (For the backend AI and API)
2. **Bun** or **Node.js** (For the frontend dependencies)
3. A connected webcam or IP camera for the vision engine.
4. *(Windows Users)* Visual C++ Redistributable (Required for OpenCV and PyZbar).

---

## 🚀 Complete Setup Guide

### 1. Backend Setup (FastAPI & Vision)

Open a terminal and set up the Python environment:

\\ash
# Navigate to project root
cd backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\\Scripts\\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt

# Start the backend server
python run.py
# Alternatively, use the provided scripts:
# .\\run_with_camera.bat (Windows)
\\n
The backend will run on \http://localhost:8000\.

### 2. Frontend Setup (React & Vite)

Open a **new** terminal window:

\\ash
# Navigate to the frontend directory
cd frontend

# Install dependencies using Bun (recommended) or npm
bun install

# Start the development server
bun run dev
\\n
The frontend will run on \http://localhost:5173\.

---

## 🔧 Hardware & Vision Engine Notes

- **Vision Models**: The required \.caffemodel\ and \.prototxt\ files are pre-located in \ackend/app/vision/models/\.
- **Camera Troubleshooting**: If the camera fails to open, verify your USB connections, update driver permissions, and modify the camera index in \ackend/app/core/config.py\ if necessary.
- **Serial Connection**: Ensure your Arduino or robotic controller is connected to the correct COM port. You can configure this in the backend environment variables or config files.

---

## 🤝 Contribution & Usage

1. Ensure the code passes backend validations.
2. Add your tests inside \ackend/tests/\ or \rontend/test/\.
3. Create feature branches for new integrations!
