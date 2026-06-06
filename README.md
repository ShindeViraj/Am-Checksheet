# TPM Dashboard & Machine Reports System

This repository contains the source code for an industrial **Total Productive Maintenance (TPM) Dashboard and Machine Reports System**. 

The application is designed to digitally track and display real-time machine equipment monitoring, checklist completion, and daily maintenance metrics. 

## Features

- **Real-Time Dashboard**: Monitor overall maintenance success rates, check completion statuses (OK vs NOK), and dynamically calculated trends over specific time periods (Days, Weeks, Months).
- **Machine-Specific Reports**: Generate detailed, downloadable, and printable maintenance reports per machine.
- **Dynamic Checkpoints Data**: Checkpoint descriptions and required validation parameters are dynamically loaded from JSON files and matched against MySQL database entries.
- **Premium UI/UX**: Built with modern HTML/CSS techniques, featuring glassmorphism elements, CSS-driven transitions, animated hover effects, and a highly responsive Tailwind CSS layout.
- **Chart Visualizations**: Integrated charting components to visually track machine performance trends over time.

## Tech Stack

- **Backend**: Python (Flask)
- **Database**: SQLite / MySQL (configurable)
- **Frontend**: HTML5, Vanilla JavaScript, Custom Premium CSS, TailwindCSS
- **Data Visualizations**: Chart.js

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ShindeViraj/Am-CheckSheet.git
   cd Am-CheckSheet
   ```

2. **Install dependencies:**
   Ensure you have Python installed, then install the required packages:
   ```bash
   pip install flask python-dotenv
   # Add any other required packages, e.g., for MySQL: pip install pymysql cryptography
   ```

3. **Run the Application:**
   ```bash
   python app.py
   ```

4. **View the Dashboard:**
   Open your browser and navigate to `http://127.0.0.1:5000`
