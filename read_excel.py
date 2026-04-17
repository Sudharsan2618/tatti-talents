import pandas as pd
import sys

file_path = "d:/thirshi/NextGen Innovators Project Hub -  St.Joseph Kovur.xlsx"

try:
    import json
    df = pd.read_excel(file_path).fillna('')
    if 'Timestamp' in df.columns:
        df = df.drop(columns=['Timestamp'])
    data = {
        "columns": list(df.columns),
        "rows": df.to_dict(orient='records')
    }
    with open('d:/thirshi/temp.json', 'w') as f:
        json.dump(data, f)
    print("Dumped to d:/thirshi/temp.json")
except Exception as e:
    print("Error:", e)
