import os
import re
import json
import gzip
import hashlib
import base64
import requests
import threading
import time
from flask import Flask, request, Response
from datetime import datetime

app = Flask(__name__)

# ==================== CONFIGURATION ====================
TARGET_BASE_URL = "https://dl.bs.freefiremobile.com/live/ABHotUpdates/"
VER_PHP_URL = "https://version.ggwhitehawk.com/live/ver.php"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', 10000))

# ==================== KEEP ALIVE ====================
def keep_alive():
    while True:
        try:
            requests.get(f"http://localhost:{PORT}/", timeout=5)
        except:
            pass
        time.sleep(180)

threading.Thread(target=keep_alive, daemon=True).start()

# ==================== MOD OVERRIDES (ONLY REQUIRED) ====================
ANTI_BAN_OVERRIDES = {
    "CleanFFAntiState": {"var_type": "bool", "var_value": "true"},
    "FFAntihackDefenceLevel": {"var_type": "string", "var_value": "0"},
    "FFAntihackLightInitOnThread": {"var_type": "bool", "var_value": "false"},
    "EnablePlatformCheck": {"var_type": "bool", "var_value": "false"},
    "EnableIceWallHacker": {"var_type": "bool", "var_value": "false"},
    "EnableSendHackStoreLog": {"var_type": "bool", "var_value": "false"},
    "KickUserInMatchGame": {"var_type": "bool", "var_value": "false"},
    "EnableCheckFileStates": {"var_type": "bool", "var_value": "false"},
    "NeedProcessAH": {"var_type": "bool", "var_value": "true"},
}

# ==================== CORE LOGIC ====================
def sha1_b64(data):
    return base64.b64encode(hashlib.sha1(data).digest()).decode()

def read_url_config(path_str):
    """URL se sirf 3 cheezein check karega."""
    config = {"HS_NECK": False, "HS_CHEST": False, "ASSET_INDEXER": False}
    parts = path_str.lower().split('/')
    
    for i in range(len(parts) - 1):
        keyword = parts[i]
        value = parts[i+1]
        if keyword == 'hs_neck' and value == 'true': config["HS_NECK"] = True
        if keyword == 'hs_chest' and value == 'true': config["HS_CHEST"] = True
        if keyword == 'asset_indexer' and value == 'true': config["ASSET_INDEXER"] = True
            
    return config

def patch_fileinfo(text, config):
    if not config["HS_NECK"] and not config["HS_CHEST"]:
        return text
        
    lines = text.splitlines()
    new_lines = []
    
    for line in lines:
        if line.startswith("cache_res,"):
            file_to_use = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")):
                file_to_use = "cache_res"
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")):
                file_to_use = "cache_res2"
                
            if file_to_use:
                try:
                    with open(os.path.join(BASE_DIR, file_to_use), "rb") as f:
                        gz_data = f.read()
                    raw_data = gzip.decompress(gz_data)
                    new_line = f"cache_res,{sha1_b64(raw_data)},{len(raw_data)},0,{sha1_b64(gz_data)},{len(gz_data)},True,0"
                    new_lines.append(new_line)
                    continue
                except Exception as e:
                    print(f"Error reading file: {e}")
        new_lines.append(line)
    return "\n".join(new_lines)

def modify_ver(text, config):
    try:
        data = json.loads(text)
        my_cdn = f"https://{request.host}/cdn/live/ABHotUpdates/"
        data["cdn_url"] = my_cdn
        data["backup_cdn_url"] = my_cdn
        data["abhotupdate_cdn_url"] = my_cdn
        
        # Sirf Anti-ban inject hoga
        overrides = ANTI_BAN_OVERRIDES
        
        if overrides:
            gamevar = data.get("gamevar", "")
            for var_name, val in overrides.items():
                gamevar += f"\n{var_name},{var_name},{val['var_type']},{val['var_value']},,"
            data["gamevar"] = gamevar
            
        return json.dumps(data)
    except Exception as e:
        return text

# ==================== ROUTES ====================

@app.route('/')
def home():
    return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        print(f"[{datetime.now()}] Connection | Status: {config}")
        
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            modified_data = modify_ver(resp.text, config)
            return Response(modified_data, status=200, content_type="application/json")
        except Exception as e:
            return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        # CDN ke liye default false
        config = {"HS_NECK": False, "HS_CHEST": False, "ASSET_INDEXER": False}

        if "assetindexer" in file_path_str:
            if config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
                with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f:
                    return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")):
                file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")):
                file_to_read = os.path.join(BASE_DIR, "cache_res2")
                
            if file_to_read:
                with open(file_to_read, "rb") as f:
                    return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            target_url = TARGET_BASE_URL + file_path_str
            try:
                resp = requests.get(target_url, timeout=30)
                patched_text = patch_fileinfo(resp.text, config)
                return Response(patched_text.encode(), content_type="binary/octet-stream")
            except Exception as e:
                return Response(f"Error: {e}", status=502)
                
        target_url = TARGET_BASE_URL + file_path_str
        try:
            resp = requests.get(target_url, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e:
            return Response(f"Error: {e}", status=502)

    return Response("Invalid Endpoint", status=404)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ULTRA FAST PROXY (3 FEATURES ONLY)")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)