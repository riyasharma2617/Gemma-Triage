import json
import re
import os

def clean_json(file_path):
    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        print(f"Error: {file_path} is empty. Please save your file in the editor first!")
        return

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        # Python's json.load automatically resolves duplicate keys by keeping the last one!
        # This will automatically fix the duplicate 'expected_code' and 'reasoning' issue.
        data = json.load(f)

    for i, item in enumerate(data, start=1):
        # 1. Fix IDs to be sequential starting from T001
        item['id'] = f"T{i:03d}"
        
        # 2. Fix source to be "curated"
        # Check if 'Source' (capital S) exists and replace with 'source'
        if 'Source' in item:
            del item['Source']
        item['source'] = 'curated'
        
        # 3. Clean up the reasoning text (remove [1, 3] style references)
        if 'reasoning' in item:
            item['reasoning'] = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', item['reasoning']).strip()

    # Save the organized file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    print(f"Successfully cleaned and organized {len(data)} items in {file_path}")

if __name__ == "__main__":
    target_file = r"s:\Gemma-Triage-Advanced\01_data\curated\curated.json"
    if os.path.exists(target_file):
        clean_json(target_file)
    else:
        print(f"Error: Could not find {target_file}")
