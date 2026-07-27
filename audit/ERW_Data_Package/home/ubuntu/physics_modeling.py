import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load processed data
df = pd.read_csv('/home/ubuntu/carbdown_processed.csv')
df['Date'] = pd.to_datetime(df['Date'])

# 1. Steady-state Calcium Export
# Compare treatments to baseline 000
baseline = df[df['Treatment'] == '000'].set_index('Date')
results = []

for treatment in ['100', '200', '400', 'FINE']:
    t_df = df[df['Treatment'] == treatment].set_index('Date')
    merged = t_df.join(baseline, lsuffix='_t', rsuffix='_b')
    merged['Ca_diff'] = merged['Ca_export_umol_t'] - merged['Ca_export_umol_b']
    
    total_excess_ca = merged['Ca_diff'].sum()
    mean_excess_ca = merged['Ca_diff'].mean()
    
    results.append({
        'Treatment': treatment,
        'Total_Excess_Ca_umol': total_excess_ca,
        'Mean_Excess_Ca_umol': mean_excess_ca
    })

results_df = pd.DataFrame(results)
print("Excess Calcium Export relative to Control:")
print(results_df)

# 2. Linearity Check for 100 t/ha and 400 t/ha
ca_100 = results_df[results_df['Treatment'] == '100']['Total_Excess_Ca_umol'].values[0]
ca_400 = results_df[results_df['Treatment'] == '400']['Total_Excess_Ca_umol'].values[0]

print(f"\n100 t/ha Excess Ca: {ca_100:.2e} umol")
print(f"400 t/ha Excess Ca: {ca_400:.2e} umol")
if ca_100 > 0:
    ratio = ca_400 / ca_100
    print(f"Ratio 400/100: {ratio:.2f} (Expected 4.0 for linear scaling)")
else:
    print("Excess Ca for 100 t/ha is not positive, cannot calculate ratio.")

# 3. FINE Treatment Analysis
ca_fine = results_df[results_df['Treatment'] == 'FINE']['Total_Excess_Ca_umol'].values[0]
print(f"\nFINE (200 t/ha) Excess Ca: {ca_fine:.2e} umol")
ca_200 = results_df[results_df['Treatment'] == '200']['Total_Excess_Ca_umol'].values[0]
print(f"Standard 200 t/ha Excess Ca: {ca_200:.2e} umol")

# 4. Visualization of the "Secret Sauce" - checking for passivation/reversion
plt.figure(figsize=(12, 6))
for treatment in ['000', '400', 'FINE']:
    subset = df[df['Treatment'] == treatment]
    plt.plot(subset['Date'], subset['Ca_export_umol'], label=treatment)

plt.title('Calcium Export Trends: Control vs 400 t/ha vs FINE')
plt.xlabel('Date')
plt.ylabel('Ca Export (umol)')
plt.legend()
plt.savefig('/home/ubuntu/physics_trends.png')

# 5. Check for "Baseline Reversion"
# Does the difference between 400 and 000 decrease over time?
df_400 = df[df['Treatment'] == '400'].set_index('Date')
merged_400 = df_400.join(baseline, lsuffix='_400', rsuffix='_000')
merged_400['Diff'] = merged_400['Ca_export_umol_400'] - merged_400['Ca_export_umol_000']

plt.figure(figsize=(12, 6))
plt.plot(merged_400.index, merged_400['Diff'], marker='o')
plt.axhline(0, color='red', linestyle='--')
plt.title('Difference in Ca Export (400 t/ha - Control) Over Time')
plt.ylabel('Delta Ca Export (umol)')
plt.savefig('/home/ubuntu/passivation_check.png')
