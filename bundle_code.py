import os

output_file = "FinMem-LLM-StockTrading-AllCode.txt"

include_extensions = {".py", ".sql", ".toml", ".sh", ".md", ".json"}
exclude_dirs = {".git", "data", "figures", "__pycache__", ".devcontainer", "env", "venv"}

with open(output_file, "w", encoding="utf-8") as outfile:
    for root, dirs, files in os.walk("."):
        # filter dirs
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in include_extensions and file != output_file and file != "bundle_code.py":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    outfile.write(f"{'='*80}\n")
                    outfile.write(f"FILE: {file_path}\n")
                    outfile.write(f"{'='*80}\n\n")
                    outfile.write(content)
                    outfile.write("\n\n")
                except Exception as e:
                    print(f"Failed to read {file_path}: {e}")

print(f"Successfully created {output_file}")
