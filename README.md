# Domestic Gold Price Monitor (Au99.99)

A real-time dashboard for monitoring **Shanghai Gold Exchange (SGE) Au99.99** prices, featuring profit calculation, price alerts, and data visualization.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Vue](https://img.shields.io/badge/vue-3.x-green)

## ✨ Features

*   **Real-time Monitoring**: Fetches live Au99.99 prices every 5 seconds from reliable sources (Eastmoney/Sina).
*   **Robust Data Source**: Auto-switching mechanism (Eastmoney -> Sina -> Backup) ensures high availability.
*   **Profit Calculator**:
    *   Set your **Buy Price** to track real-time profit/loss.
    *   Auto-calculates sell targets for 5%, 10%, 20% profit margins (accounting for 0.5% fee).
*   **Visual Feedback**:
    *   **Red for Rise / Green for Fall** (Localized for CN market).
    *   Dynamic "heartbeat" animations when price updates.
    *   Interactive charts powered by Chart.js.
*   **Price Recording**: Manually record price snapshots with notes for future reference.

## 🚀 Quick Start

### Prerequisites

*   Python 3.8+
*   Pip

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/gold-price-monitor.git
    cd gold-price-monitor
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

1.  **Start the Server**:
    *   **Windows**: Double-click `start.bat` (if configured for your env) or run:
        ```bash
        python app.py
        ```
    *   **Linux/Mac**:
        ```bash
        python3 app.py
        ```

2.  **Access the Dashboard**:
    Open your browser and visit: `http://localhost:5000`

## 🛠 Tech Stack

*   **Backend**: Flask (Python)
*   **Frontend**: Vue 3, Tailwind CSS, Chart.js
*   **Data Source**: Eastmoney API, Sina Finance API

## 📝 Configuration

You can adjust the configuration in `app.py`:

*   `DATA_SOURCES`: Add or remove data providers.
*   `MAX_HISTORY_SIZE`: Change the amount of historical data kept in memory.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](LICENSE)
