import pandas as pd
import sqlite3
import json
import re
import os

# Paths
FILES = [
    {"path": "NextGen Innvovators Project Hub-hindu clg.xlsx", "college": "Hindu College"},
    {"path": "NextGen Innovators Project Hub -  St.Joseph Kovur.xlsx", "college": "St. Joseph College, Kovur"}
]
DB_PATH = "backend/data/talentatlas.db"

def clean_link(val):
    if not val or pd.isna(val): return ""
    val = str(val).strip()
    v_low = val.lower()
    
    # Strictly for identifying non-links (not for URLs that happen to contain these letters)
    exact_no_link = ['nil', 'na', 'none', 'no', '-', 'nil ', 'n/a', 'nan']
    if v_low in exact_no_link:
        return ""
        
    # Phrases that indicate no link
    no_link_phrases = ['in-hand project', 'yet to start', 'in progress', 'will update', 'not yet', 'still working']
    if any(phrase in v_low for phrase in no_link_phrases):
        return ""

    if len(val) < 5: return ""
    
    # Check if it's a URL
    if "http" in v_low or "www." in v_low:
        match = re.search(r'(https?://[^\s"]+)', val)
        if match: return match.group(1)
        return val
    return ""

def get_domain(dept):
    dept = str(dept).lower()
    if 'data' in dept or 'statistics' in dept: return 'data'
    if 'ai' in dept or 'artificial' in dept: return 'ai'
    if 'iot' in dept or 'electronics' in dept: return 'iot'
    if 'web' in dept or 'computer' in dept or 'b.c.a' in dept or 'bca' in dept: return 'web'
    return 'other'

def run_import():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Clear existing students as requested
    print("Clearing existing students and shortlists...")
    cur.execute("DELETE FROM shortlist")
    cur.execute("DELETE FROM students")
    conn.commit()
    
    total_inserted = 0
    
    # 2. Iterate through files
    for entry in FILES:
        f_path = entry['path']
        college_name = entry['college']
        
        if not os.path.exists(f_path):
            print(f"Skipping {f_path}: file not found.")
            continue
            
        print(f"Reading {f_path}...")
        try:
            df = pd.read_excel(f_path).fillna('')
        except Exception as e:
            print(f"Error reading {f_path}: {e}")
            continue
            
        demo_col = 'Project Demo / Portfolio Link(if any)  '
        # Handle cases where column names might slightly differ (e.g. trailing spaces)
        if demo_col not in df.columns:
            matches = [c for c in df.columns if 'Project Demo' in c]
            if matches: demo_col = matches[0]
            else:
                print(f"Could not find demo column in {f_path}. Skipping.")
                continue

        inserted = 0
        skipped_no_link = 0
        skipped_form = 0
        
        for _, row in df.iterrows():
            raw_demo = row.get(demo_col, "")
            demo_link = clean_link(raw_demo)
            
            # Stricter Filter for "full working link"
            if not demo_link:
                skipped_no_link += 1
                continue
            if 'forms.gle' in demo_link.lower() or 'google.com/forms' in demo_link.lower():
                skipped_form += 1
                continue
                
            name = str(row.get("Full Name", "")).strip()
            if not name or name.lower() == 'nan' or len(name) < 2: continue
            
            email = str(row.get("Email address", "")).strip()
            phone = str(row.get("Mobile Number", "")).replace(".0", "").strip()
            degree = str(row.get("Department", "")).strip()
            year = str(row.get("Year of Study", "")).strip()
            
            ptitle = str(row.get("Project Title", "")).strip()
            pdesc_short = str(row.get("One-Line Project Description", "")).strip()
            pdesc_full = str(row.get("Problem Statement", "")) + " - " + str(row.get("Your Solution", ""))
            pdesc = pdesc_short if len(pdesc_short) > 20 else pdesc_full[:500]
            impact = str(row.get("Real-World Impact", "")).strip()
            
            skills_raw = row.get("Tools & Software Used", "")
            skills_list = []
            if isinstance(skills_raw, str):
                parts = re.split(r'[,/]', skills_raw)
                for p in parts:
                    s = p.strip()
                    if s and len(s) > 1: skills_list.append(s)
            
            skills_json = json.dumps(skills_list)
            linkedin_link = clean_link(row.get("LinkedIn Profile URL (Optional)", ""))
            domain = get_domain(degree)
            
            try:
                cur.execute("""
                INSERT INTO students (name, email, phone, college, degree, year, linkedin, domain, ptitle, pdesc, impact, skills, demo, is_new)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (name, email, phone, college_name, degree, year, linkedin_link, domain, ptitle, pdesc, impact, skills_json, demo_link))
                inserted += 1
            except Exception as e:
                print(f"Error inserting {name}: {e}")
                
        total_inserted += inserted
        print(f"Finished {college_name}: Inserted {inserted}, Skipped (no link) {skipped_no_link}, Skipped (forms) {skipped_form}")
        
    conn.commit()
    conn.close()
    print(f"\nFresh Import Complete! Total students in Directory: {total_inserted}")

if __name__ == "__main__":
    run_import()
