import sys
import os
import pandas as pd

# Ensure Python can locate your 'data' folder if running from different directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from data.eurostat import get_eurostat_series
except ImportError:
    print("❌ Critical Error: Could not import 'get_eurostat_series'.")
    sys.exit(1)

def get_euro_trade_balance_data():
    """
    Fetches Euro Area International Trade Balance using pre-filtered policy tables.
    Uses 'EA19' because Eurostat locks these policy sheets to the core currency bloc.
    """
    print("1/4: Requesting Euro Area Monthly Export Data (teiet010)...")
    df_exports = get_eurostat_series(
        "teiet010",
        {
            "geo": "EA19",  # CHANGED FROM EA20 TO EA19 TO FIX EMPTY DATA
            "freq": "M"
        }
    )
    
    print("2/4: Requesting Euro Area Monthly Import Data (teiet110)...")
    df_imports = get_eurostat_series(
        "teiet110",
        {
            "geo": "EA19",  # CHANGED FROM EA20 TO EA19 TO FIX EMPTY DATA
            "freq": "M"
        }
    )
    
    if df_exports is None or df_exports.empty:
        print("❌ Error: Export table returned empty or None.")
        return None
    if df_imports is None or df_imports.empty:
        print("❌ Error: Import table returned empty or None.")
        return None

    print("3/4: Raw data received successfully. Standardizing shapes...")
    df_exports = df_exports.rename(columns={"value": "exports"})
    df_imports = df_imports.rename(columns={"value": "imports"})
    
    print("4/4: Aligning rows by date and calculating net balance...")
    df_merged = df_exports[["date", "exports"]].merge(
        df_imports[["date", "imports"]], 
        on="date", 
        how="inner"
    )
    
    # Calculate Net Balance (Exports minus Imports)
    df_merged["value"] = df_merged["exports"] - df_merged["imports"]
    
    # Extract only the columns matching your other core dashboard functions
    df_final = df_merged[["date", "value"]].copy()
    return df_final

if __name__ == "__main__":
    print("=== STARTING ISOLATED EUROSTAT TRADE BALANCE TEST ===")
    
    df = get_euro_trade_balance_data()
    
    if df is not None:
        print("\n🎉 TEST PASSED SUCCESSFULLY!")
        print(f"DataFrame structure size: {df.shape} (Rows, Columns)")
        print(f"Target column names matching dashboard: {list(df.columns)}")
        
        print("\n--- Most Recent Available Economic Records (Tail) ---")
        print(df.tail(10))
    else:
        print("\n❌ TEST FAILED: The output DataFrame returned None.")
