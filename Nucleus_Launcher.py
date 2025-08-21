import os
import requests
from zipfile import ZipFile
import threading
import subprocess
import shutil
import customtkinter as ctk

# --- URLs ---
VERSION_URL = "https://nucleus.rip/info"
BASE_URL = "https://setup-aws.rbxcdn.com/version-{}-{}"

# --- Directories ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "NucleusRobloxVersion")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
INSTALLED_FILE = os.path.join(BASE_DIR, "installed_version.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Extraction Paths (как в rdd) ---
EXTRACT_PATHS = {
    "RobloxApp.zip": "",
    "redist.zip": "",
    "shaders.zip": "shaders/",
    "ssl.zip": "ssl/",
    
    "WebView2.zip": "",
    "WebView2RuntimeInstaller.zip": "WebView2RuntimeInstaller/",
    
    "content-avatar.zip": "content/avatar/",
    "content-configs.zip": "content/configs/",
    "content-fonts.zip": "content/fonts/",
    "content-sky.zip": "content/sky/",
    "content-sounds.zip": "content/sounds/",
    "content-textures2.zip": "content/textures/",
    "content-models.zip": "content/models/",
    
    "content-platform-fonts.zip": "PlatformContent/pc/fonts/",
    "content-platform-dictionaries.zip": "PlatformContent/pc/shared_compression_dictionaries/",
    "content-terrain.zip": "PlatformContent/pc/terrain/",
    "content-textures3.zip": "PlatformContent/pc/textures/",
    
    "extracontent-luapackages.zip": "ExtraContent/LuaPackages/",
    "extracontent-translations.zip": "ExtraContent/translations/",
    "extracontent-models.zip": "ExtraContent/models/",
    "extracontent-textures.zip": "ExtraContent/textures/",
    "extracontent-places.zip": "ExtraContent/places/"
}

# --- Version Handling ---
def get_installed_version():
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, "r") as f:
            return f.read().strip()
    return "N/A"

def set_installed_version(v):
    with open(INSTALLED_FILE, "w") as f:
        f.write(v)
    installed_label.configure(text=f"Installed Version: {v}")

def get_latest_version():
    try:
        resp = requests.get(VERSION_URL, timeout=10)
        resp.raise_for_status()
        latest = resp.json()["Versions"]["Roblox"].replace("version-", "")
        server_label.configure(text=f"Server Version: {latest}")
        return latest
    except:
        server_label.configure(text="Server Version: N/A")
        return None

def parse_manifest(manifest_content):
    """Парсит манифест и возвращает список файлов для загрузки (как в rdd)"""
    files = []
    for line in manifest_content.splitlines():
        if line.strip() and not line.startswith('#'):
            files.append(line.strip())
    return files

# --- Download & Extract ---
def download_and_extract():
    start_btn.configure(state="disabled")
    latest_version = get_latest_version()
    if not latest_version:
        log_text.configure(state="normal")
        log_text.insert(ctk.END, "Failed to fetch latest version.\n")
        log_text.configure(state="disabled")
        start_btn.configure(state="normal")
        return

    installed_version = get_installed_version()
    if installed_version == latest_version:
        log_text.configure(state="normal")
        log_text.insert(ctk.END, f"Roblox is up to date (v{installed_version})\n")
        log_text.configure(state="disabled")
    else:
        progress.set(0.0)
        log_text.configure(state="normal")
        log_text.delete("1.0", ctk.END)

        # Сначала скачиваем манифест (как в rdd)
        manifest_url = BASE_URL.format(latest_version, "rbxPkgManifest.txt")
        manifest_path = os.path.join(DOWNLOAD_DIR, "rbxPkgManifest.txt")
        
        try:
            log_text.insert(ctk.END, "Downloading manifest...\n")
            log_text.see(ctk.END)
            r = requests.get(manifest_url, stream=True)
            r.raise_for_status()
            with open(manifest_path, "wb") as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk)
            
            # Читаем и парсим манифест
            with open(manifest_path, 'r') as f:
                manifest_content = f.read()
            files_to_download = parse_manifest(manifest_content)
            
        except Exception as e:
            log_text.insert(ctk.END, f"Error downloading manifest: {e}\n")
            log_text.see(ctk.END)
            # Fallback на жесткий список если манифест недоступен
            files_to_download = [
                "RobloxApp.zip", "redist.zip", "shaders.zip", "ssl.zip",
                "WebView2.zip", "WebView2RuntimeInstaller.zip",
                "content-avatar.zip", "content-configs.zip", "content-fonts.zip",
                "content-sky.zip", "content-sounds.zip", "content-textures2.zip",
                "content-models.zip", "content-platform-fonts.zip",
                "content-platform-dictionaries.zip", "content-terrain.zip",
                "content-textures3.zip", "extracontent-luapackages.zip",
                "extracontent-translations.zip", "extracontent-models.zip",
                "extracontent-textures.zip", "extracontent-places.zip"
            ]

        # Скачиваем и распаковываем файлы из манифеста
        for i, file_name in enumerate(files_to_download, 1):
            url = BASE_URL.format(latest_version, file_name)
            local_path = os.path.join(DOWNLOAD_DIR, file_name)
            try:
                log_text.insert(ctk.END, f"Downloading {file_name}...\n")
                log_text.see(ctk.END)
                r = requests.get(url, stream=True)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(1024*1024):
                        f.write(chunk)
                
                if local_path.endswith(".zip"):
                    # Получаем путь для распаковки (как в rdd)
                    relative_path = EXTRACT_PATHS.get(file_name, "")
                    dest_folder = os.path.join(BASE_DIR, relative_path)
                    os.makedirs(dest_folder, exist_ok=True)
                    
                    log_text.insert(ctk.END, f"Extracting {file_name} to {dest_folder}...\n")
                    log_text.see(ctk.END)
                    with ZipFile(local_path, 'r') as zip_ref:
                        zip_ref.extractall(dest_folder)
                
                # Удаляем скачанный файл после распаковки
                if os.path.exists(local_path):
                    os.remove(local_path)
                    
            except Exception as e:
                log_text.insert(ctk.END, f"Error with {file_name}: {e}\n")
                log_text.see(ctk.END)
            
            progress.set(i / len(files_to_download))

        # Очищаем папку загрузок
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        set_installed_version(latest_version)
        log_text.insert(ctk.END, f"Roblox updated to v{latest_version}\n")
        log_text.see(ctk.END)
        log_text.configure(state="disabled")

    start_btn.configure(state="normal")

def start_download_thread():
    threading.Thread(target=download_and_extract, daemon=True).start()

# --- Launch Roblox ---
def launch_roblox():
    exe_path = os.path.join(BASE_DIR, "RobloxPlayerBeta.exe")
    if os.path.exists(exe_path):
        try:
            subprocess.Popen(exe_path)
        except Exception as e:
            log_text.configure(state="normal")
            log_text.insert(ctk.END, f"Failed to launch Roblox: {e}\n")
            log_text.configure(state="disabled")
    else:
        log_text.configure(state="normal")
        log_text.insert(ctk.END, "Roblox is not installed. Please install it first.\n")
        log_text.configure(state="disabled")

# --- GUI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
root = ctk.CTk()
root.title("Nucleus Launcher")
root.geometry("700x520")
root.resizable(False, False)

title_label = ctk.CTkLabel(root, text="Nucleus Launcher", font=ctk.CTkFont(size=24, weight="bold"))
title_label.pack(pady=(15,5))

installed_label = ctk.CTkLabel(root, text=f"Installed Version: {get_installed_version()}", font=ctk.CTkFont(size=12))
installed_label.pack()
server_label = ctk.CTkLabel(root, text="Server Version: fetching...", font=ctk.CTkFont(size=12))
server_label.pack(pady=(0,10))

btn_frame = ctk.CTkFrame(root)
btn_frame.pack(pady=10, fill="x", padx=20)

start_btn = ctk.CTkButton(btn_frame, text="Install / Update Roblox", command=start_download_thread, width=300)
start_btn.grid(row=0, column=0, padx=10, pady=10)

launch_btn = ctk.CTkButton(btn_frame, text="Launch Roblox", command=launch_roblox, width=300)
launch_btn.grid(row=0, column=1, padx=10, pady=10)

progress = ctk.CTkProgressBar(root, width=650)
progress.pack(pady=15)
progress.set(0.0)

log_text = ctk.CTkTextbox(root, width=650, height=250)
log_text.pack(pady=10)
log_text.configure(state="disabled")

# Получаем версию при запуске
def init_version_check():
    threading.Thread(target=get_latest_version, daemon=True).start()

root.after(100, init_version_check)
root.mainloop()