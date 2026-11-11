"""
Execute all Jupyter Notebooks in-place to pre-compute and store all cell outputs.
"""

import os
import sys
import glob
import nbformat
from nbclient import NotebookClient

NOTEBOOK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notebooks")

def execute_all():
    notebook_files = sorted(glob.glob(os.path.join(NOTEBOOK_DIR, "*.ipynb")))
    print(f"Executing {len(notebook_files)} notebooks in {NOTEBOOK_DIR}...")
    
    for nb_path in notebook_files:
        nb_name = os.path.basename(nb_path)
        print(f"--> Running {nb_name}...")
        try:
            with open(nb_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
                
            client = NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": NOTEBOOK_DIR}})
            client.execute()
            
            with open(nb_path, "w", encoding="utf-8") as f:
                nbformat.write(nb, f)
            print(f"    [SUCCESS] {nb_name} executed and outputs saved.")
        except Exception as e:
            print(f"    [ERROR] Failed executing {nb_name}: {e}")

if __name__ == "__main__":
    execute_all()

