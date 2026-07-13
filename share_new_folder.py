import os
import gradio as gr

def get_files():
    files_to_share = []
    
    # Target exactly the 'New folder' directory requested by the user
    target_dir = r"C:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv\New folder"
    
    for root, dirs, filenames in os.walk(target_dir):
        # Modify dirs in-place to prevent os.walk from descending into heavy directories
        skip_dirs = {".git", "node_modules", "build", "__pycache__", ".dart_tool", "venv", ".pub-cache", "android", "ios"}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for filename in filenames:
            # Skip sqlite db files for security, just in case
            if not filename.endswith('.db') and not filename.endswith('.sqlite'):
                files_to_share.append(os.path.join(root, filename))
                    
    return files_to_share

with gr.Blocks(title="dMRV Shared Folder") as demo:
    gr.Markdown("# 📁 Shared Folder: 'New folder'")
    gr.Markdown("Downloading individual files without zipping. Excludes heavy build artifacts (`.git`, `build/`, `node_modules`, etc.).")
    
    gr.File(value=get_files(), file_count="multiple", label="Source Files", interactive=False)

if __name__ == "__main__":
    print("Launching Gradio app... Looking for public URL.", flush=True)
    # Using port 7861 in case 7860 is still held by a zombie process from before the server restart
    demo.launch(share=True, server_name="0.0.0.0", server_port=7861)
