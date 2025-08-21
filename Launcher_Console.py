import os
import requests
from zipfile import ZipFile
import shutil
import re
import sys
import subprocess


VERSION_URL = "https://nucleus.rip/info"
BASE_URL = "https://setup-aws.rbxcdn.com/version-{}-{}"
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "NucleusRobloxVersion")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
INSTALLED_FILE = os.path.join(BASE_DIR, "installed_version.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


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
    "extracontent-places.zip": "ExtraContent/places/",
    "rbxPkgManifest.txt": "",
}

def get_installed_version():
    if os.path.exists(INSTALLED_FILE):
        with open(INSTALLED_FILE, "r") as f:
            return f.read().strip()
    return "N/A"

def set_installed_version(v):
    with open(INSTALLED_FILE, "w") as f:
        f.write(v)

def get_latest_version():
    try:
        resp = requests.get(VERSION_URL, timeout=10)
        resp.raise_for_status()
        latest = resp.json()["Versions"]["Roblox"].replace("version-", "")
        return latest
    except Exception as e:
        print(f"[!] Failed to fetch latest version: {e}")
        return None

def parse_manifest(manifest_content):
    files = []
    lines = manifest_content.splitlines()
    hash_pattern = re.compile(r'^[a-f0-9]{32}$')
    size_pattern = re.compile(r'^\d+$')
    version_pattern = re.compile(r'^v\d+$')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if (hash_pattern.match(line) or 
            size_pattern.match(line) or 
            version_pattern.match(line)):
            continue
        if line.endswith('.xml') or line == 'ClientSettings':
            continue
        if line == "RobloxPlayerInstaller.exe":
            continue
        files.append(line)
    return files

def create_appsettings_xml():
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<Settings>
    <ContentFolder>content</ContentFolder>
    <BaseUrl>http://www.roblox.com</BaseUrl>
</Settings>'''
    path = os.path.join(BASE_DIR, "AppSettings.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def clean_installation_directory():
    if not os.path.exists(BASE_DIR):
        return
    for item in os.listdir(BASE_DIR):
        if item in ["downloads", "installed_version.txt"]:
            continue
        path = os.path.join(BASE_DIR, item)
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except Exception as e:
            print(f"[!] Error removing {path}: {e}")

def download_and_extract():
    latest_version = get_latest_version()
    if not latest_version:
        print("[!] Could not fetch latest Roblox version.")
        return

    installed_version = get_installed_version()
    if installed_version == latest_version:
        print(f"[✓] Roblox is already up to date (v{installed_version})")
    else:
        print("[*] Cleaning installation directory...")
        clean_installation_directory()

        manifest_url = BASE_URL.format(latest_version, "rbxPkgManifest.txt")
        manifest_path = os.path.join(DOWNLOAD_DIR, "rbxPkgManifest.txt")
        try:
            print("[*] Downloading manifest...")
            r = requests.get(manifest_url, stream=True)
            r.raise_for_status()
            with open(manifest_path, "wb") as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk)
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_content = f.read()
            files_to_download = parse_manifest(manifest_content)
        except Exception as e:
            print(f"[!] Failed to download manifest: {e}")
            files_to_download = [
                "rbxPkgManifest.txt", "RobloxApp.zip", "redist.zip", "shaders.zip", "ssl.zip",
                "WebView2.zip", "WebView2RuntimeInstaller.zip",
                "content-avatar.zip", "content-configs.zip", "content-fonts.zip",
                "content-sky.zip", "content-sounds.zip", "content-textures2.zip",
                "content-models.zip", "content-platform-fonts.zip",
                "content-platform-dictionaries.zip", "content-terrain.zip",
                "content-textures3.zip", "extracontent-luapackages.zip",
                "extracontent-translations.zip", "extracontent-models.zip",
                "extracontent-textures.zip", "extracontent-places.zip"
            ]

        total = len(files_to_download)
        for i, file_name in enumerate(files_to_download, 1):
            url = BASE_URL.format(latest_version, file_name)
            local_path = os.path.join(DOWNLOAD_DIR, file_name)
            try:
                print(f"[*] Downloading {file_name} ({i}/{total})...")
                r = requests.get(url, stream=True)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(1024*1024):
                        f.write(chunk)
                relative_path = EXTRACT_PATHS.get(file_name, "")
                dest_folder = os.path.join(BASE_DIR, relative_path)
                os.makedirs(dest_folder, exist_ok=True)
                if file_name.endswith(".zip"):
                    with ZipFile(local_path, 'r') as zip_ref:
                        zip_ref.extractall(dest_folder)
                    os.remove(local_path)
                else:
                    shutil.move(local_path, os.path.join(dest_folder, file_name))
            except Exception as e:
                print(f"[!] Error with {file_name}: {e}")

        print("[*] Creating AppSettings.xml...")
        create_appsettings_xml()
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        set_installed_version(latest_version)
        print(f"[✓] Roblox updated to v{latest_version}")

def launch_roblox():
    exe_path = os.path.join(BASE_DIR, "RobloxPlayerBeta.exe")
    if os.path.exists(exe_path):
        try:
            subprocess.Popen([exe_path])
            print("[✓] Roblox launched.")
        except Exception as e:
            print(f"[!] Failed to launch Roblox: {e}")
    else:
        print("[!] Roblox is not installed. Please run the updater first.")

if __name__ == "__main__":
    download_and_extract()
    launch_roblox()
