# CrowdX — Crowd Crush Prevention System

> Real-time crowd density monitoring and crush prevention using computer vision, 
> multi-person tracking, and predictive trend analysis.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-Live%20Dashboard-teal)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Overview

CrowdX is a real-time crowd safety system designed to detect, monitor, and 
predict dangerous crowd crush situations before they occur. Built using 
YOLOv8 object detection and DeepSORT multi-person tracking, the system 
continuously analyzes live camera feeds, calculates crowd density across 
spatial zones, and fires early warnings when a crush is predicted — not 
just when it has already happened.

Developed as part of a hackathon project focused on public safety at 
large-scale events such as festivals, concerts, and religious gatherings.

---

## Key Features

- **Dual camera support** — simultaneously monitors two live feeds
  (laptop webcam + mobile IP camera)
- **YOLOv8 person detection** — real-time detection with confidence filtering
- **DeepSORT tracking** — assigns unique IDs to track individuals across frames
- **3×3 zone grid analysis** — divides each camera frame into 9 zones and
  classifies each as SAFE / WARNING / CRITICAL
- **Density heatmap** — live color overlay showing crowd concentration
  (blue = sparse → red = dense)
- **Trend engine** — uses linear regression on a 30-second rolling window
  to calculate crowd growth rate and predict count 10 seconds ahead
- **Early warning system** — fires alerts before threshold is crossed,
  not after
- **Live location tracking** — attaches Google Maps link to every alert
- **SMS / WhatsApp alerts** — sends instant notifications via Twilio
  when surge is detected
- **Sound alerts** — local audio alarm on critical events
- **Web dashboard** — dark-themed real-time UI showing both camera feeds,
  zone status, trend chart, prediction bar, and alert log
- **FastAPI backend** — streams MJPEG video and serves live JSON data
  to the browser dashboard

---

## How It Works
Camera Feed
↓
YOLOv8 Detection → Person bounding boxes
↓
DeepSORT Tracker → Unique person IDs across frames
↓
Density Engine → People count per zone
↓
Risk Engine → SAFE / WARNING / CRITICAL per zone
↓
Trend Engine → Growth rate + 10s prediction + crash forecast
↓
Alert System → Sound + SMS + Dashboard update

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/CrowdX.git
cd CrowdX
```

### 2. Install dependencies
```bash
pip install ultralytics opencv-python deep-sort-realtime fastapi uvicorn twilio numpy
```

### 3. Configure settings
Edit `config/settings.py`:
```python
FRAME_WIDTH      = 800
FRAME_HEIGHT     = 600
ROWS             = 3
COLS             = 3
ALERT_THRESHOLD  = 10   # tune to your venue
```

### 4. Run the server
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 5. Open the dashboard
Open `crowdx_dashboard.html` in any browser.
The green dot in the bottom bar confirms the server is connected.

---

## Alert System

When crowd density surges, CrowdX fires a two-stage alert:

**Stage 1 — Early Warning** (before threshold is crossed)
Triggered when the trend engine predicts the crowd will reach dangerous
density within the next 10 seconds. Gives organisers time to redirect
crowd flow before a crush occurs.

**Stage 2 — Overcrowd Alert** (threshold crossed)
Triggered when an actual zone hits critical density. Includes unsafe zone
list and live Google Maps location link.

Both stages send SMS via Twilio and update the live dashboard simultaneously.

---

## Real-World Use Cases

- Music festivals and outdoor concerts
- Religious gatherings and pilgrimages  
- Stadium entry and exit management
- Public transport hubs during peak hours
- Emergency evacuation monitoring

---

## Built At

This project was built during a hackathon focused on public safety 
and AI for social good.

---

## License

MIT License — free to use, modify, and distribute.
