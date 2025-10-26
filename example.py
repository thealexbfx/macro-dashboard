import pandas as pd
from io import StringIO

# Paste your raw data here (including the header)
raw_data = """
Date
Price
Open
High
Low
Change %
Oct 24, 2025	4.4310	4.4120	4.4480	4.3910	+0.29%
Oct 23, 2025	4.4180	4.4260	4.4460	4.4030	+0.07%
Oct 22, 2025	4.4150	4.4210	4.4420	4.3700	-1.36%
Oct 21, 2025	4.4760	4.4850	4.5230	4.4650	-0.62%
Oct 20, 2025	4.5040	4.5340	4.5430	4.5010	-0.64%
Oct 17, 2025	4.5330	4.4650	4.5550	4.4520	+1.21%
Oct 16, 2025	4.4790	4.5380	4.5590	4.4720	-1.58%
Oct 15, 2025	4.5510	4.5530	4.5620	4.5240	-0.50%
Oct 14, 2025	4.5740	4.6300	4.6300	4.5710	-1.68%
Oct 13, 2025	4.6520	4.6750	4.6980	4.6440	-0.45%
Oct 10, 2025	4.6730	4.7240	4.7350	4.6590	-1.54%
Oct 09, 2025	4.7460	4.7170	4.7600	4.7060	+0.89%
Oct 08, 2025	4.7040	4.7120	4.7280	4.6940	-0.36%
Oct 07, 2025	4.7210	4.7430	4.7680	4.7150	-0.30%
Oct 06, 2025	4.7350	4.7230	4.7610	4.7160	+0.83%
Oct 03, 2025	4.6960	4.7070	4.7120	4.6810	+0.09%
Oct 02, 2025	4.6920	4.6960	4.7490	4.6910	-0.06%
Oct 01, 2025	4.6950	4.7330	4.7460	4.6770	-0.06%
"""

# Clean and process the data
# Skip the first 6 header lines
data_lines = "\n".join(raw_data.strip().split("\n")[6:])
df = pd.read_csv(StringIO(data_lines), sep="\t", header=None, names=['Date', 'Price', 'Open', 'High', 'Low', 'Change'])

# Keep only Date and Price
df = df[['Date', 'Price']]

# Convert Date to MM/DD/YYYY format
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%m/%d/%Y')

# Output the result
print(df.to_csv(sep='\t', index=False))
