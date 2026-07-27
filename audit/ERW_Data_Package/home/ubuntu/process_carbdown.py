import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Load the main dataset
csv_path = '/home/ubuntu/carbdown_data/CDI Raw Data/Carbdown XXL Lysimeter Data 2022-2024 (Corrected with data until 2024).csv'
df = pd.read_csv(csv_path)

# Convert Date to datetime
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

# Basic cleaning: handle missing values represented by '#'
df = df.replace('#', np.nan)
# Convert numeric columns to float
numeric_cols = df.columns[4:]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Filter for relevant treatments
# Treatments: 000 (Control), 100, 200, 400 (Coarse), 200F (Fine)
# Let's check the unique treatments
print("Unique treatments:", df['Treatment'].unique())

# Aggregate by Treatment and Date
agg_df = df.groupby(['Treatment', 'Date']).agg({
    'Ca2+_umol': 'mean',
    'Mg2+_umol': 'mean',
    'Volume in l': 'mean',
    'conduct_uS_per_cm_in_field': 'mean'
}).reset_index()

# Calculate Export (Concentration * Volume)
# Concentration is in umol/L, Volume in L, so Export is in umol
agg_df['Ca_export_umol'] = agg_df['Ca2+_umol'] * agg_df['Volume in l']
agg_df['Mg_export_umol'] = agg_df['Mg2+_umol'] * agg_df['Volume in l']

# Save processed data
agg_df.to_csv('/home/ubuntu/carbdown_processed.csv', index=False)

# Plotting Ca export over time
plt.figure(figsize=(12, 6))
sns.lineplot(data=agg_df, x='Date', y='Ca_export_umol', hue='Treatment')
plt.title('Calcium Export (umol) Over Time by Treatment')
plt.ylabel('Ca Export (umol)')
plt.savefig('/home/ubuntu/ca_export_plot.png')

# Summary stats for physics modeling
summary = agg_df.groupby('Treatment').agg({
    'Ca_export_umol': ['sum', 'mean'],
    'Mg_export_umol': ['sum', 'mean']
}).reset_index()
summary.columns = ['Treatment', 'Ca_sum', 'Ca_mean', 'Mg_sum', 'Mg_mean']
print(summary)
