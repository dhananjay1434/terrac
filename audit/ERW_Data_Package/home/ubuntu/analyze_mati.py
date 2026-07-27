import pandas as pd
import numpy as np

# Load the Mati Carbon dataset
file_path = '/home/ubuntu/Dataset_S1.xlsx'
# Read the first sheet or the one named 'Dataset_S1'
try:
    df = pd.read_excel(file_path, sheet_name='Dataset S1')
except Exception as e:
    print(f"Error reading sheet: {e}")
    df = pd.read_excel(file_path)

print("Mati Carbon Dataset Columns:", df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())

# Basic summary
summary = df.describe()
print("\nSummary Statistics:")
print(summary)

# Check for site data
if 'site' in df.columns:
    site_yield = df.groupby('site')['delta_yield_pct'].mean()
    print("\nAverage Delta Yield % by Site:")
    print(site_yield)
else:
    print("\nSite column not found.")
