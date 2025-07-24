import os

def remove_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[CLEANUP] Deleted temporary PDF: {file_path}")
    except Exception as e:
        print(f"[CLEANUP] Error deleting file {file_path}: {str(e)}")