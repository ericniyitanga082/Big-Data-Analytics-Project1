# Location: src/demand_patterns.py
import sys
import os
import psycopg2
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def run_grid_demand_analysis():
    print("[*] Connecting to database on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 1. Calculate Daily Energy Totals
    daily_query = """
        SELECT event_time::date AS cat_day, SUM(energy_kwh) AS total_kwh
        FROM energy_readings
        GROUP BY cat_day
        ORDER BY cat_day ASC;
    """
    cursor.execute(daily_query)
    daily_data = cursor.fetchall()
    
    # 2. Calculate Four 7-Day Period Energy Totals
    weekly_query = """
        SELECT period_label, SUM(energy_kwh) AS total_kwh
        FROM (
            SELECT 
                CASE 
                    WHEN event_time >= '2026-09-01 00:00:00+02' AND event_time < '2026-09-08 00:00:00+02' THEN 'Period 1 (Sep 01-07)'
                    WHEN event_time >= '2026-09-08 00:00:00+02' AND event_time < '2026-09-15 00:00:00+02' THEN 'Period 2 (Sep 08-14)'
                    WHEN event_time >= '2026-09-15 00:00:00+02' AND event_time < '2026-09-22 00:00:00+02' THEN 'Period 3 (Sep 15-21)'
                    WHEN event_time >= '2026-09-22 00:00:00+02' AND event_time < '2026-09-29 00:00:00+02' THEN 'Period 4 (Sep 22-28)'
                END AS period_label,
                energy_kwh
            FROM energy_readings
        ) AS sub_readings
        WHERE period_label IS NOT NULL
        GROUP BY period_label
        ORDER BY period_label ASC;
    """
    cursor.execute(weekly_query)
    weekly_data = cursor.fetchall()
    
    # 3. Isolate the Three Highest 15-Minute Network Power Spikes
    peaks_query = """
        SELECT event_time, SUM(power_kw) AS network_kw_demand
        FROM energy_readings
        GROUP BY event_time
        ORDER BY network_kw_demand DESC
        LIMIT 3;
    """
    cursor.execute(peaks_query)
    top_peaks = cursor.fetchall()
    
    # --- PRINT OUT CONSOLE REPORT ---
    print("\n" + "="*75)
    print("=== SECTION 5.1: GRID NETWORK DEMAND PATTERNS METRICS REPORT ===")
    print("="*75)
    print("\n[#] FOUR SEVEN-DAY METRIC SUMMARY CONFIGURATIONS:")
    print("-" * 65)
    for row in weekly_data:
        print(f"  [-] {row[0]}: {row[1]:,.4f} kWh")
        
    print("\n[#] TOP 3 CRITICAL 15-MINUTE SYSTEM POWER PEAK SPHERES:")
    print("-" * 65)
    for rank, row in enumerate(top_peaks, start=1):
        print(f"  Rank #{rank} | Timestamp: {row[0]} | Coincident Peak: {row[1]:,.3f} kW")
    print("="*75)
    
    # 4. Generate Combined Visualizations Subplot Layout
    days = [str(r[0]) for r in daily_data]
    kwh_vals = [float(r[1]) for r in daily_data]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))
    
    # Subplot 1: Daily Total Energy Trend Line
    ax1.plot(days, kwh_vals, marker='o', color='#1f77b4', linewidth=2, label='Daily Grid Consumption')
    ax1.set_title('Daily Total Grid Energy Load Profile (September 2026)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Calendar Date (CAT)', fontsize=10)
    ax1.set_ylabel('Energy Volume (kWh)', fontsize=10)
    ax1.set_xticklabels(days, rotation=45, ha='right')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    
    # Subplot 2: Top 3 Critical Peak Demand Intervals
    peak_times = [str(p[0]) for p in top_peaks]
    peak_kw = [float(p[1]) for p in top_peaks]
    
    bars = ax2.bar(peak_times, peak_kw, color=['#d62728', '#ff7f0e', '#2ca02c'], width=0.4)
    ax2.set_title('Top 3 Coincident 15-Minute Peak Power Demand (kW Infrastructure Strain)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Event Time Interval (CAT)', fontsize=10)
    ax2.set_ylabel('System Capacity Peak (kW)', fontsize=10)
    ax2.grid(True, linestyle=':', alpha=0.5, axis='y')
    
    # Add data value labels on top of the bars
    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:,.2f} kW',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')
                    
    plt.tight_layout()
    os.makedirs('evidence', exist_ok=True)
    plt.savefig('evidence/section_5_1_demand_trends_multi_plot.png', dpi=150)
    plt.close()
    print("[+] Complete multi-panel chart layout successfully saved to: evidence/section_5_1_demand_trends_multi_plot.png")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_grid_demand_analysis()
