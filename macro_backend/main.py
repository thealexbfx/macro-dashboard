from fastapi import FastAPI
import pandas as pd

app = FastAPI()

def get_japan_cpi_yoy_data():
    # For now, example static data, replace with your actual data loading logic
    data = {
        "date": ["2023-01-01", "2023-02-01", "2023-03-01"],
        "value": [0.5, 0.7, 0.9]
    }
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

@app.get("/api/japan/cpi")
async def japan_cpi():
    df = get_japan_cpi_yoy_data()
    # Convert df to dict/list of dicts for JSON response
    json_data = df.to_dict(orient="records")
    # Format date as string (ISO)
    for row in json_data:
        row["date"] = row["date"].strftime("%Y-%m-%d")
    return {"data": json_data}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend running on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your routes...
@app.get("/api/japan/cpi")
async def get_japan_cpi():
    return {
        "data": [
            {"date": "2023-01-01", "value": 0.5},
            {"date": "2023-02-01", "value": 0.7},
            {"date": "2023-03-01", "value": 0.9}
        ]
    }
