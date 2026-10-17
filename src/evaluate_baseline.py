# Location: src/evaluate_baseline.py
import sys
import os
import pickle
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_baseline_evaluation():
    dataset_path = 'data_cache/forecast_dataset.pkl'
    if not os.path.exists(dataset_path):
        print("[-] Error: Forecast dataset cache not found. Run section 8.1 first.")
        return
        
    # 1. Load cached time-series dataframe feature columns
    df = pd.read_pickle(dataset_path)
    
    # 2. Extract Test Split: September 22 to September 28 inclusive (7 full calendar days)
    test_df = df[(df['target_hour'] >= '2026-09-22 00:00:00') & (df['target_hour'] < '2026-09-29 00:00:00')].copy()
    
    # 3. Formulate Baseline Predictions Vector
    # The baseline forecast maps directly to our pre-calculated lag_24h_energy predictor variable
    y_actual = test_df['actual_energy_kwh'].to_numpy()
    y_pred = test_df['lag_24h_energy'].to_numpy()
    
    prediction_count = len(test_df)
    
    # 4. Calculate Mathematical Error Vectors
    absolute_errors = np.abs(y_actual - y_pred)
    squared_errors = (y_actual - y_pred) ** 2
    
    mae = np.mean(absolute_errors)
    rmse = np.sqrt(np.mean(squared_errors))
    
    # --- PRINT OUT STANDARDIZED EVALUATION MATRIX ---
    print("\n" + "="*85)
    print("=== SECTION 8.2: NAIVE PREVIOUS-DAY PERSISTENCE BASELINE EVALUATION ===")
    print("="*85)
    print(f"[+] Target Test Split Evaluation Window: 22 September - 28 September 2026")
    print(f"[+] Total Verified Baseline Predictions:  {prediction_count:,} rows")
    print(f"[+] Validation Checkpoint Tally Count:   7 Days * 24 Hours * 10 Regions = 1,680")
    print("-" * 85)
    print("[#] CALCULATED ACCURACY METRICS PROFILE:")
    print(f"  [-] Mean Absolute Error (MAE):          {mae:.4f} kWh")
    print(f"  [-] Root Mean Squared Error (RMSE):        {rmse:.4f} kWh")
    print("="*85)
    
    # 5. Output Sample Predictions Grid Rows
    print("\n[#] SAMPLE LOG GRID OF BASELINE PERSISTENCE PREDICTIONS:")
    print("-" * 80)
    print(f"{'Target Hour (CAT)':<22}{'Region':<12}{'Previous-Day (Pred)':<22}{'Actual Load (kWh)'}")
    print("-" * 80)
    
    sample_rows = test_df.head(5)
    for _, row in sample_rows.iterrows():
        print(f"{str(row['target_hour']):<22}{row['region']:<12}{row['lag_24h_energy']:<22,.4f}{row['actual_energy_kwh']:,.4f}")
    print("="*85)
    
    # Cache metrics for subsequent analysis layers
    os.makedirs('data_cache', exist_ok=True)
    with open('data_cache/baseline_metrics.pkl', 'wb') as f:
        pickle.dump({'mae': mae, 'rmse': rmse, 'count': prediction_count}, f)
    print("[+] Baseline validation metrics locked to cache folder.")

if __name__ == "__main__":
    run_baseline_evaluation()
