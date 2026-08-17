import os
import re
import json
import gzip
import hashlib
import base64
import requests
import threading
import time
from flask import Flask, request, Response, redirect, url_for, session, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_cr'

app_data = {"maintenance": False, "connected_ips": set()}

TARGET_BASE_URL = "https://dl.bs.freefiremobile.com/live/ABHotUpdates/"
VER_PHP_URL = "https://version.ggwhitehawk.com/live/ver.php" 
ADMIN_PASS = "Aditya@7457$aditya*7457"
TELEGRAM_LINK = "https://t.me/+aOpyPp0gZyg1YmU1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', 8080))

def keep_alive():
    while True:
        try: requests.get(f"http://localhost:{PORT}/", timeout=5)
        except: pass
        time.sleep(180)

threading.Thread(target=keep_alive, daemon=True).start()

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

def sha1_b64(data): return base64.b64encode(hashlib.sha1(data).digest()).decode()

def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def read_url_config(path_str):
    config = {"HS_NECK": False, "HS_CHEST": False, "ASSET_INDEXER": False}
    parts = path_str.lower().split('/')
    for i in range(len(parts) - 1):
        keyword, value = parts[i], parts[i+1]
        if keyword == 'hs_neck' and value == 'true': config["HS_NECK"] = True
        if keyword == 'hs_chest' and value == 'true': config["HS_CHEST"] = True
        if keyword == 'asset_indexer' and value == 'true': config["ASSET_INDEXER"] = True
    return config

def patch_fileinfo(text, config):
    if not config["HS_NECK"] and not config["HS_CHEST"]: return text
    lines, new_lines = text.splitlines(), []
    for line in lines:
        if line.startswith("cache_res,"):
            file_to_use = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_use = "cache_res"
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_use = "cache_res2"
            if file_to_use:
                try:
                    with open(os.path.join(BASE_DIR, file_to_use), "rb") as f: gz_data = f.read()
                    raw_data = gzip.decompress(gz_data)
                    new_lines.append(f"cache_res,{sha1_b64(raw_data)},{len(raw_data)},0,{sha1_b64(gz_data)},{len(gz_data)},True,0")
                    continue
                except: pass
        new_lines.append(line)
    return "\n".join(new_lines)

def modify_ver(text, config):
    try:
        data = json.loads(text)
        if config["HS_NECK"] or config["HS_CHEST"] or config["ASSET_INDEXER"]:
            my_cdn = f"https://{request.host}/cdn/live/ABHotUpdates/"
            data["cdn_url"] = my_cdn
            data["backup_cdn_url"] = my_cdn
            data["abhotupdate_cdn_url"] = my_cdn
        if ANTI_BAN_OVERRIDES:
            gamevar = data.get("gamevar", "")
            for var_name, val in ANTI_BAN_OVERRIDES.items():
                gamevar += f"\n{var_name},{var_name},{val['var_type']},{val['var_value']},,"
            data["gamevar"] = gamevar
        return json.dumps(data)
    except: return text

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'logged_in' in session: return redirect('/admin/dashboard')
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS: session['logged_in'] = True
        else: error = "ACCESS DENIED"
    if 'logged_in' in session: return redirect('/admin/dashboard')
    with open('login.html', 'r') as f: html = f.read()
    return html.replace("{{ERROR_MSG}}", error if error else "")

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' not in session: return redirect('/admin')
    with open('dashboard.html', 'r') as f: html = f.read()
    final_html = html.replace("TELEGRAM_LINK_HOLDER", TELEGRAM_LINK)
    return final_html.replace("{% if maintenance %}on{% endif %}", "on" if app_data["maintenance"] else "")

@app.route('/admin/api/stats')
def admin_stats():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"devices": len(app_data["connected_ips"])})

@app.route('/admin/api/reset_ips', methods=['POST'])
def admin_reset_ips():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    app_data["connected_ips"].clear()
    return jsonify({"success": True})

@app.route('/admin/api/toggle_maintenance', methods=['POST'])
def api_toggle_maintenance():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    app_data["maintenance"] = not app_data["maintenance"]
    return jsonify({"success": True, "maintenance": app_data["maintenance"]})

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect('/admin')

@app.route('/')
def home(): return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if full_path.startswith('admin'): return Response("Invalid", status=404)
    app_data["connected_ips"].add(get_client_ip())
    
    if app_data["maintenance"]:
        return Response(json.dumps({"maint": "true", "url": TELEGRAM_LINK}), status=503, content_type="application/json")

    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        
        # === GOD MODE HEADERS (Tumhare dusre source se liya gaya) ===
        # Game ke original headers ko replace karke premium spoof headers bhej rahe hain
        headers = {
            "User-Agent": "Garena/1.0 (Android; OB54)",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "X-Client-Version": "OB54",
            "X-Game-Version": "1.0.0",
            "X-Platform": "Android",
            "X-Device-Model": "SM-G998B",
            "X-Device-Brand": "samsung",
            "X-Device-Android": "12",
            "X-Device-RAM": "8GB",
            "X-Device-Storage": "128GB",
            "X-Network-Type": "WiFi",
            "X-Carrier": "T-Mobile",
            "Connection": "keep-alive"
        }
        
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            response = Response(modify_ver(resp.text, config), status=200, content_type="application/json")
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e: return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        config = read_url_config(full_path)
        
        if "assetindexer" in file_path_str and config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
            with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_read = os.path.join(BASE_DIR, "cache_res2")
            if file_to_read:
                with open(file_to_read, "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            try:
                resp = requests.get(TARGET_BASE_URL + file_path_str, timeout=30)
                return Response(patch_fileinfo(resp.text, config).encode(), content_type="binary/octet-stream")
            except Exception as e: return Response(f"Error: {e}", status=502)
                
        try:
            resp = requests.get(TARGET_BASE_URL + file_path_str, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e: return Response(f"Error: {e}", status=502)

    return Response("Invalid", status=404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)    with open('dashboard.html', 'r') as f: html = f.read()
    final_html = html.replace("TELEGRAM_LINK_HOLDER", TELEGRAM_LINK)
    return final_html.replace("{% if maintenance %}on{% endif %}", "on" if app_data["maintenance"] else "")

@app.route('/admin/api/stats')
def admin_stats():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"devices": len(app_data["connected_ips"])})

@app.route('/admin/api/reset_ips', methods=['POST'])
def admin_reset_ips():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    app_data["connected_ips"].clear()
    return jsonify({"success": True})

@app.route('/admin/api/toggle_maintenance', methods=['POST'])
def api_toggle_maintenance():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    app_data["maintenance"] = not app_data["maintenance"]
    return jsonify({"success": True, "maintenance": app_data["maintenance"]})

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect('/admin')

@app.route('/')
def home(): return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if full_path.startswith('admin'): return Response("Invalid", status=404)
    app_data["connected_ips"].add(get_client_ip())
    
    if app_data["maintenance"]:
        return Response(json.dumps({"maint": "true", "url": TELEGRAM_LINK}), status=503, content_type="application/json")

    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; SM-G991B Build/SP1A.210812.016)", "Accept-Encoding": "gzip"}
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            response = Response(modify_ver(resp.text, config), status=200, content_type="application/json")
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e: return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        config = read_url_config(full_path)
        
        if "assetindexer" in file_path_str and config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
            with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_read = os.path.join(BASE_DIR, "cache_res2")
            if file_to_read:
                with open(file_to_read, "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            try:
                resp = requests.get(TARGET_BASE_URL + file_path_str, timeout=30)
                return Response(patch_fileinfo(resp.text, config).encode(), content_type="binary/octet-stream")
            except Exception as e: return Response(f"Error: {e}", status=502)
                
        try:
            resp = requests.get(TARGET_BASE_URL + file_path_str, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e: return Response(f"Error: {e}", status=502)

    return Response("Invalid", status=404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
