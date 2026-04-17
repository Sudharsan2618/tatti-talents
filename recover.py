import os
import json
import shutil
from pathlib import Path

history_dir = Path(os.environ["APPDATA"]) / "Code" / "User" / "History"
target_base = Path(r"C:\Users\thirs\Downloads\thirshi (1)\thirshi")
recovery_dir = Path(r"C:\Users\thirs\Downloads\thirshi (1)\recovery")

recovery_dir.mkdir(exist_ok=True)

files_to_recover = {
    "StudentDashboard.jsx": "frontend/src/pages/StudentDashboard.jsx",
    "Home.jsx": "frontend/src/pages/Home.jsx",
    "Dashboard.jsx": "frontend/src/pages/Dashboard.jsx",
    "run.py": "backend/run.py",
    "auth.py": "backend/app/routes/auth.py",
    "jobs.py": "backend/app/routes/jobs.py"
}

print("Searching VS Code Local History...")

for folder in history_dir.iterdir():
    if not folder.is_dir():
        continue
    entries_file = folder / "entries.json"
    if not entries_file.exists():
        continue
    try:
        with open(entries_file, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        resource = data.get("resource", "")
        # Convert path separators for safe checking
        res_normalized = resource.replace("\\", "/")
        
        for fname, dest in files_to_recover.items():
            if res_normalized.endswith(fname):
                entries = data.get("entries", [])
                if not entries:
                    continue
                
                # Sort entries by timestamp descending
                entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                
                # We will copy the last 3 versions so you can pick the correct one
                file_rec_dir = recovery_dir / fname
                file_rec_dir.mkdir(exist_ok=True)
                
                found_count = 0
                for entry in entries:
                    if found_count >= 3:
                        break
                    latest_id = entry["id"]
                    source_file = folder / latest_id
                    if source_file.exists():
                        dest_path = file_rec_dir / f"v{found_count}_{latest_id}_{fname}"
                        shutil.copy2(source_file, dest_path)
                        found_count += 1
                        
                print(f"Recovered {found_count} versions of {fname} from history.")
    except Exception as e:
        pass

print("Recovery complete! Look in the 'recovery' folder.")

# Let's also restore the most recent version that is at least 15 minutes old (before I wiped it), or just let me do it.
