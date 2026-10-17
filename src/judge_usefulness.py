# Location: src/judge_usefulness.py
import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_usefulness_assessment():
    dataset_path = 'data_cache/forecast_dataset.pkl'
    if not os.path.exists(dataset_path):
        print("[-] Error: Forecast dataset cache not found. Run section 8.1 first.")
        return
        
    df = pd.read_pickle(dataset_path)
    
    # 1. Re-isolate Chronological Splits
    train_df = df[(df['target_hour'] >= '2026-09-01 00:00:00') & (df['target_hour'] < '2026-09-15 00:00:00')]
    test_df  = df[(df['target_hour'] >= '2026-09-22 00:00:00') & (df['target_hour'] < '2026-09-29 00:00:00')].copy()
    
    feature_cols = ['target_day_of_week', 'target_hour_of_day', 'lag_24h_energy', 'lag_48h_energy']
    
    # Preprocessing scaling context
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(train_df[feature_cols])
    X_test_scaled  = scaler.transform(test_df[feature_cols])
    
    # Train our frozen optimal Config_2 model architecture
    model = LGBMRegressor(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1)
    model.fit(X_train_scaled, train_df['actual_energy_kwh'])
    
    # Generate model predictions over the test split rows
    test_df['pred_baseline'] = test_df['lag_24h_energy']
    test_df['pred_model'] = model.predict(X_test_scaled)
    
    # 2. Regional Analysis Loop
    print("\n" + "="*95)
    print("=== SECTION 8.4: GLOBAL AND REGIONAL METER METRIC PERFORMANCE FORECAST PROFILE ===")
    print("="*95)
    print(f"{'Region Scope':<15}{'Baseline MAE':<15}{'Baseline RMSE':<18}{'Model MAE':<15}{'Model RMSE'}")
    print("-" * 95)
    
    def get_errors(sub_df):
        act = sub_df['actual_energy_kwh'].to_numpy()
        b_p = sub_df['pred_baseline'].to_numpy()
        m_p = sub_df['pred_model'].to_numpy()
        return (np.mean(np.abs(act - b_p)), np.sqrt(np.mean((act - b_p)**2)),
                np.mean(np.abs(act - m_p)), np.sqrt(np.mean((act - m_p)**2)))
                
    g_b_mae, g_b_rmse, g_m_mae, g_m_rmse = get_errors(test_df)
    print(f"{'GLOBAL GRID':<15}{g_b_mae:<15.4f}{g_b_rmse:<18.4f}{g_m_mae:<15.4f}{g_m_rmse:.4f}")
    print("-" * 95)
    
    for r in sorted(test_df['region'].unique()):
        r_df = test_df[test_df['region'] == r]
        b_mae, b_rmse, m_mae, m_rmse = get_errors(r_df)
        print(f"{r:<15}{b_mae:<15.4f}{b_rmse:<18.4f}{m_mae:<15.4f}{m_rmse:.4f}")
    print("="*95)
    
    # 3. Peak-Hour Critical Error Extraction Strategy
    print("\n" + "="*115)
    print("=== CRITICAL VOLUMETRIC PEAK-HOUR DATA INTEGRITY AND ERROR ANALYSIS ===")
    print("="*115)
    print(f"{'Region':<10}{'Peak Hour (CAT)':<22}{'Actual (kWh)':<15}{'Base Pred':<12}{'Base Err':<12}{'Model Pred':<12}{'Model Err'}")
    print("-" * 115)
    
    for r in sorted(test_df['region'].unique()):
        r_df = test_df[test_df['region'] == r]
        # Locate the hour of highest actual load consumption, breaking ties by earliest timestamp
        peak_idx = r_df.sort_values(by=['actual_energy_kwh', 'target_hour'], ascending=[False, True]).index[0]
        peak_row = r_df.loc[peak_idx]
        
        act = peak_row['actual_energy_kwh']
        b_p = peak_row['pred_baseline']
        m_p = peak_row['pred_model']
        
        print(f"{r:<10}{str(peak_row['target_hour']):<22}{act:<15.2f}"
              f"{b_p:<12.2f}{abs(act-b_p):<12.2f}{m_p:<12.2f}{abs(act-m_p):.2f}")
    print("="*115)
    
    # 4. Generate Time-Series Forecast Plot for Region 1
    plot_df = test_df[test_df['region'] == 'Region 1'].sort_values('target_hour')
    
    plt.figure(figsize=(12, 6))
    plt.plot(plot_df['target_hour'], plot_df['actual_energy_kwh'], label='Actual Consumption', color='black', linewidth=2)
    plt.plot(plot_df['target_hour'], plot_df['pred_baseline'], label='Previous-Day Baseline', color='red', linestyle='--', alpha=0.7)
    plt.plot(plot_df['target_hour'], plot_df['pred_model'], label='Advanced LightGBM Model', color='blue', linestyle='-', alpha=0.8)
    
    plt.title('Chronological Forecasting Validation Horizon - Region 1 (Sep 22 - Sep 28, 2026)', fontsize=12, fontweight='bold')
    plt.xlabel('Calendar Date Time (CAT)', fontsize=10)
    plt.ylabel('Energy Consumption Volume (kWh)', fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=10)
    plt.xticks(rotation=15)
    plt.tight_layout()
    
    os.makedirs('evidence', exist_ok=True)
    plt.savefig('evidence/section_8_4_forecast_plot.png', dpi=150)
    plt.close()
    print("\n[+] System multiline time-series visualization saved safely at: evidence/section_8_4_forecast_plot.png")

if __name__ == "__main__":
    run_usefulness_assessment()
