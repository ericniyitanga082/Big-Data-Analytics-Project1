# Location: src/evaluate_regression.py
import sys
import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_regression_pipeline():
    dataset_path = 'data_cache/forecast_dataset.pkl'
    if not os.path.exists(dataset_path):
        print("[-] Error: Forecast dataset cache not found. Run section 8.1 first.")
        return
        
    df = pd.read_pickle(dataset_path)
    
    # 1. Chronological Split Isolations [8.1]
    train_df = df[(df['target_hour'] >= '2026-09-01 00:00:00') & (df['target_hour'] < '2026-09-15 00:00:00')]
    val_df   = df[(df['target_hour'] >= '2026-09-15 00:00:00') & (df['target_hour'] < '2026-09-22 00:00:00')]
    test_df  = df[(df['target_hour'] >= '2026-09-22 00:00:00') & (df['target_hour'] < '2026-09-29 00:00:00')].copy()
    
    # Shared predictor column names definitions
    feature_cols = ['target_day_of_week', 'target_hour_of_day', 'lag_24h_energy', 'lag_48h_energy']
    target_col = 'actual_energy_kwh'
    
    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_val, y_val     = val_df[feature_cols], val_df[target_col]
    X_test, y_test   = test_df[feature_cols], test_df[target_col]
    
    # 2. Freeze Preprocessing Rules to Prevent Leakage [8.1]
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled   = scaler.transform(X_val)
    X_test_scaled  = scaler.transform(X_test)
    
    train_rows = len(X_train)
    val_rows = len(X_val)
    
    # 3. Define and Train the Two Separate Configurations
    configs = {
        "Config_1 (Shallow)": LGBMRegressor(n_estimators=50, max_depth=3, learning_rate=0.05, random_state=42, verbose=-1),
        "Config_2 (Deep)": LGBMRegressor(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1)
    }
    
    results = {}
    
    print("[*] Commencing multi-configuration validation training loops...")
    for cfg_id, model in configs.items():
        model.fit(X_train_scaled, y_train)
        preds_val = model.predict(X_val_scaled)
        
        # Calculate validation absolute and squared metric vectors
        mae_val = np.mean(np.abs(y_val - preds_val))
        rmse_val = np.sqrt(np.mean((y_val - preds_val) ** 2))
        
        results[cfg_id] = {'model': model, 'mae': mae_val, 'rmse': rmse_val, 'settings': str(model.get_params())}
        
    # --- PRINT OUT VALIDATION REPORT DATA FRAME ---
    print("\n" + "="*110)
    print("=== SECTION 8.3: REGRESSION CONFIGURATIONS EXPERIMENTAL VALIDATION MATRIX ===")
    print("="*110)
    print(f"{'Config ID':<20}{'Model Tuning Settings':<35}{'Train Rows':<12}{'Val Rows':<10}{'Val MAE':<12}{'Val RMSE'}")
    print("-" * 110)
    print(f"{'Config_1 (Shallow)':<20}{'n_estimators=50, max_depth=3':<35}{train_rows:<12}{val_rows:<10}{results['Config_1 (Shallow)']['mae']:<12.4f}{results['Config_1 (Shallow)']['rmse']:.4f}")
    print(f"{'Config_2 (Deep)':<20}{'n_estimators=150, max_depth=6':<35}{train_rows:<12}{val_rows:<10}{results['Config_2 (Deep)']['mae']:<12.4f}{results['Config_2 (Deep)']['rmse']:.4f}")
    print("="*110)
    print(f"[+] Shared Predictors Ingested: {feature_cols}")
    
    # 4. Select the Optimal Configuration with Lowest Validation MAE
    best_cfg = "Config_1 (Shallow)" if results["Config_1 (Shallow)"]["mae"] < results["Config_2 (Deep)"]["mae"] else "Config_2 (Deep)"
    print(f"[+] Freezing Optimal Model Pipeline: Selection -> {best_cfg}")
    
    frozen_model = results[best_cfg]['model']
    
    # 5. Generate Test Split Predictions using the Frozen Pipeline
    y_pred_test = frozen_model.predict(X_test_scaled)
    test_mae = np.mean(np.abs(y_test - y_pred_test))
    test_rmse = np.sqrt(np.mean((y_test - y_pred_test) ** 2))
    
    print("\n" + "="*85)
    print("=== FINAL OUT-OF-SAMPLE TEST PERFORMANCE PERFORMANCE ===")
    print("="*85)
    print(f"[+] Total Verified Test Predictions Generated: {len(y_pred_test):,} rows")
    print(f"[+] Test Mean Absolute Error (MAE):             {test_mae:.4f} kWh")
    print(f"[+] Test Root Mean Squared Error (RMSE):         {test_rmse:.4f} kWh")
    print("="*85)
    
    # Print sample test predictions for verification
    print("\n[#] SAMPLE LOG GRID OF TEST PREDICTIONS AND ERROR VARIANCE:")
    print("-" * 85)
    print(f"{'Target Hour (CAT)':<22}{'Region':<12}{'Actual Load (kWh)':<22}{'Model Forecast (Pred)'}")
    print("-" * 85)
    for i in range(3):
        print(f"{str(test_df['target_hour'].iloc[i]):<22}{test_df['region'].iloc[i]:<12}{y_test.iloc[i]:<22,.4f}{y_pred_test[i]:,.4f}")
    print("="*85)

if __name__ == "__main__":
    run_regression_pipeline()
