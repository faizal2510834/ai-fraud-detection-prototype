# AI Fraud Detection Prototype

This repository contains the prototype for a multi-layered AI-powered fraud detection system designed for e-commerce return processes.

## Features
- **Layer 1: Visual & Hardware Intelligence:** Uses Google Gemini to instantly verify return photos against expected products and inspects deep hardware EXIF tags to reject software-generated screenshots.
- **Layer 2: Proof of Life Engine:** Traps suspicious users by requiring a live, timed physical photo with a handwritten session code.
- **CE 3.0 Matching Logic:** Simulates a backend Confidence Engine (CE 3.0) that consumes webhook events from payment processors to automatically flag or block accounts based on fraud confidence scores.

## Repository Structure
- `/frontend` - Static HTML, CSS, and JS files for the client-side UI.
- `/backend` - FastAPI Python server, Gemini AI integration, and core logic.
- `/docs` - API documentation (see `docs/API.md` for webhook specifications).
- `/demo` - End-to-end testing scripts.

## Setup Instructions

1. **Environment Variables:**
   Create a `.env` file in the `/backend` folder with your Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```

2. **Install Dependencies:**
   Navigate into the `/backend` folder and install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Backend:**
   Start the FastAPI server:
   ```bash
   python main.py
   ```
   The backend will serve both the APIs on port 8001 and mount the frontend static files.

4. **Access the Application:**
   Open your browser to `http://localhost:8001`

## Testing
- **Unit Tests for CE 3.0:** Run `python backend/test_ce_matching.py`
Try uploading 
- **Simulate Webhook Flow:** Run `python demo/simulate_webhook.py` to test the auto-block mechanics.
