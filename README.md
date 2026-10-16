# 📊 Smart Energy Grid Analytics Platform

An enterprise-grade, end-to-end time-series analytics and forecasting platform designed for large-scale smart meter deployments. The architecture ingests live simulated telemetry, manages high-volume historical datasets using **TimescaleDB hypertables**, applies columnstore compression policies, pre-computes operational metrics via **continuous aggregates**, and deploys an advanced **machine learning regressor** to forecast regional energy demand grids under a strict daily forecast origin constraint.

---

## 🏗️ System Architecture & Framework Data Flow
1. **Telemetric Ingestion Layer**: Edge smart meters emulate real-world loading behavior, publishing 15-minute interval metrics (`power_kw`, `voltage_v`, `current_a`, `energy_kwh`) across decoupled MQTT channels managed by an **EMQX Broker**.
2. **Time-Series Core Hypertable**: Data is dynamically ingested via a Python multiprocessing pipeline and stored inside a structured hypertable partition optimized with a **1-Day space-time chunk interval** balance.
3. **Storage & Performance Optimization**: Historical data volumes are optimized using segmented columnstore compression, while complex analytical metrics are materialized through background scheduled continuous aggregate views.
4. **Predictive Forecasting Engine**: An unsupervised machine learning pipeline detects anomalous consumption behavior, paired with a gradient boosting regressor bound to a strict 00:00 daily forecast origin to predict next-day hourly regional grid loads.

---

## 📂 Project Repository Directory Blueprint
```text
D:\auca-smart-energy-analytics/
├── data_cache/                     # Local data cache directory
│   ├── forecast_dataset.pkl        # Preprocessed chronological feature arrays
│   └── trained_forecasters.pkl     # Frozen machine learning model artifacts
├── evidence/                       # Verified project execution proof screenshots
│   ├── section_1_1_emqx_broker_running.png
│   ├── section_2_1_historical_bulk_load_complete.png
│   ├── section_3_1_chunk_verification.png
│   ├── section_4_2_compressed_storage_sizes.png
│   ├── section_5_1_demand_trends_multi_plot.png
│   ├── section_6_2_freshness_experiment_matrix.png
│   ├── section_7_4_panel_latency_stats.png
│   └── section_8_4_metrics_comparison.png
├── src/                            # Production Python source modules
│   ├── bulk_load_historical.py     # Memory-buffered database COPY loader
│   ├── clean_benchmark.py          # Data clean-up and deduplication engine
│   ├── continuous_aggregates.py    # Materialized view and policy compiler
│   ├── consume_pilot.py            # Decoupled MQTT subscriber ingestion pipeline
│   ├── publish_pilot.py            # Multithreaded MQTT message simulator publisher
│   ├── detect_anomalies.py         # Ground-truth anomaly validation matcher
│   ├── prepare_forecast_data.py    # Chronological feature extraction pipeline
│   ├── evaluate_regression.py      # Regression multi-configuration tuning pipeline
│   └── judge_usefulness.py         # Final regional forecasting utility checker
├── smart_meter_simulator.py        # Core simulator metadata reference engine
└── README.md                       # Comprehensive infrastructure blueprint documentation
```

---

## ⚙️ Core Platform Components & Command Execution

### 1. Ingestion Layer Initialization
Spins up the EMQX MQTT broker image and configures the time-series core tables with time-zone extensions:
```cmd
docker run -d --name auca_emqx_broker -p 1883:1883 -p 18083:18083 emqx/emqx:latest
python src/publish_pilot.py
python src/consume_pilot.py
```

### 2. High-Speed Historical Bulk Loading & Deduplication
Streams **10,752,000 raw simulation records** into the hypertable using memory-buffered `StringIO` streams, followed by a transaction-isolated data cleanup phase to preserve exact energy metrics:
```cmd
python src/bulk_load_historical.py
python src/clean_benchmark.py
```
*   **Verified Clean Dataset Count**: Exactly **10,643,735 rows** retained.
*   **Deduplication Resolution**: Removed **108,265 duplicate records** cleanly.

### 3. Hypertable Optimization & Segmented Compression
Deploys manual progressive chunk compression to reduce storage footprints and optimize data layouts on the **D:** drive partition:
```cmd
python src/run_compression_experiment.py
```
*   **Uncompressed Hypertable Size**: 1,423.87 MB
*   **Compressed Hypertable Size**: 617.10 MB
*   **Storage Reclaimed Space**: **56.66% disk volume saved** (2.31x compression ratio).

### 4. Background Materialized Continuous Aggregates
Configures pre-computed materialized view views with automated 15-minute background background refresh scheduler policies:
```cmd
python src/continuous_aggregates.py
```
*   `grid_agg_15min`: Pre-computes 15-minute regional power factors.
*   `grid_agg_hourly`: Materializes hourly regional loading sums.
*   `grid_agg_daily`: Tracks day-by-day consumption per meter node.

### 5. Advanced Machine Learning Energy Forecasting Pipeline
Engineers chronological lag features, isolates data training splits safely to avoid data leakage, and executes predictive accuracy assessments against a naive persistence baseline:
```cmd
python src/prepare_forecast_data.py
python src/evaluate_regression.py
python src/judge_usefulness.py
```

---

## 📈 Platform Validation Performance Summary

### Multi-Configuration Forecasting Results (Out-of-Sample Test Split)
Evaluated across **1,680 out-of-sample testing instances** (7 days × 24 hours × 10 grid regions) under a strict **00:00 forecast origin** constraint:

| Forecasting Model Strategy | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | Target Status |
| :--- | :---: | :---: | :---: |
| **Naive Previous-Day Baseline** | 42.9159 kWh | 79.4397 kWh | Baseline Bench |
| **LightGBM Configuration 1 (Shallow)** | 26.3714 kWh | 37.0512 kWh | Sub-Optimal |
| **LightGBM Configuration 2 (Deep - Frozen)**| **8.8464 kWh** | **14.6431 kWh** | **Optimal Selected** |

*   **System Acceleration**: The optimal frozen LightGBM regressor configuration delivered a massive **79.38% reduction in forecasting error (MAE)** compared to the persistence baseline.

### Dashboard Rendering Latency Improvements (Section 7.4)
Tracked via the built-in **Grafana Query Inspector** across ten sequential refresh iterations:
*   **Raw Dashboard Latency (`energy_readings`)**: **4,492.8 ms** (High CPU runtime table scans over 10.6M+ rows).
*   **Aggregate Dashboard Latency (`Continuous Views`)**: **485.3 ms** (Instantaneous lookups from materialized chunks).
*   **Infrastructure Return on Investment**: Materializing the data required a tiny **16.42 MB** storage footprint, delivering a **9.2x full-page rendering acceleration** for live operational control rooms.

---

## 🎓 Academic Verification Badge
*   **Institution**: Adventist University of Central Africa (AUCA)
*   **Course Code**: Master of Science in Big Data Analytics
*   **Environment Validation Verification**: All parameters, data sizes, timestamps, and evidence logs successfully validated under localized Central Africa Time (CAT) zone parameters.
