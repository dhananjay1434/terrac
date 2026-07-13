import os
import gradio as gr

def get_files():
    files_to_share = []
    
    # Directories we want to share (ignoring build artifacts and libraries)
    target_dirs = ["backend", "docs", "lib", "test"]
    
    # Allowed extensions to ensure we don't accidentally leak .env files or sqlite databases
    allowed_extensions = {".py", ".md", ".txt", ".yaml", ".yml", ".dart"}
    
    for target_dir in target_dirs:
        for root, dirs, filenames in os.walk(target_dir):
            # Skip caches, python virtual environments, and node modules
            if "__pycache__" in root or "venv" in root or "node_modules" in root or ".pytest_cache" in root:
                continue
                
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in allowed_extensions:
                    files_to_share.append(os.path.join(root, filename))
                    
    return files_to_share

with gr.Blocks(title="dMRV Code Vault") as demo:
    gr.Markdown("# 🌍 dMRV Full Codebase Vault")
    gr.Markdown("This vault contains the Python backend, documentation, and Flutter/Dart application code (`lib/`, `test/`). It explicitly excludes third-party libraries (like `node_modules` or Dart `.pub-cache`), build artifacts, and hidden `.env` secrets or databases for security.")
    
    # Display files so the visitor can download them individually (no zipping)
    gr.File(value=get_files(), file_count="multiple", label="Source Files", interactive=False)

if __name__ == "__main__":
    print("Launching Gradio app... Looking for public URL.")
    # share=True generates the 72-hour public gradio.live link
    demo.launch(share=True, server_name="0.0.0.0", server_port=7860)
