import os

def clean_server():
    with open('server.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx1 = -1
    end_idx1 = -1
    for i, line in enumerate(lines):
        if line.startswith('@asynccontextmanager'):
            start_idx1 = i
        if line.startswith('UPLOAD_DIR.mkdir'):
            end_idx1 = i
            
    if start_idx1 != -1 and end_idx1 != -1:
        new_lines = lines[:start_idx1] + [
            'from app_factory import app, create_app, lifespan, UPLOAD_DIR  # noqa: F401  (R9 facade)\n',
            '_ALLOWED_ORIGIN = os.environ.get("DMRV_ALLOWED_ORIGIN", "")\n'
        ] + lines[end_idx1+1:]
        lines = new_lines
        
    start_idx2 = -1
    for i, line in enumerate(lines):
        if line.startswith('# ---------------------------------------------------------------------------') and 'P2.0 — Lab & Verifier portal seam.' in lines[i+1]:
            start_idx2 = i
            break
            
    if start_idx2 != -1:
        # Delete everything from start_idx2 to the end of file
        lines = lines[:start_idx2]
        
    with open('server.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

if __name__ == '__main__':
    clean_server()
