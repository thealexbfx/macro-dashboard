# === print_clean_rates.py ===

# Open the text file (same folder as this script)
with open("EURO_Unemployment_Rate.txt", "r", encoding="utf-8") as f:
    next(f)  # skip the header line (Date    Rate)
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 2:
            # Join all but last as the Date, last as Rate
            date = " ".join(parts[:-1])
            rate = parts[-1]
            print(f"{date}  {rate}")  # <-- two spaces here
