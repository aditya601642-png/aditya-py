import os
import re
import json
import gzip
import hashlib
import base64
import requests
import threading
import time
from flask import Flask, request, Response, redirect, url_for, session, render_template_string, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session_cr'

# ==================== CONFIGURATION ====================
TARGET_BASE_URL = "https://dl.bs.freefiremobile.com/live/ABHotUpdates/"
VER_PHP_URL = "https://version.ggwhitehawk.com/live/ver.php"
ADMIN_PASS = "Aditya@7457$aditya*7457"
TELEGRAM_LINK = "https://t.me/reach_panel_official"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', 8080))

# ==================== IN-MEMORY DATA (CRASH PROOF FOR RAILWAY) ====================
# Ab files nahi banegi, sab RAM mein rahega. Server restart hone par reset ho jayega.
app_data = {
    "maintenance": False,
    "connected_ips": set()
}

# ==================== KEEP ALIVE ====================
def keep_alive():
    while True:
        try: requests.get(f"http://localhost:{PORT}/", timeout=5)
        except: pass
        time.sleep(180)

threading.Thread(target=keep_alive, daemon=True).start()

# ==================== MOD OVERRIDES ====================
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
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("cache_res,"):
            file_to_use = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_use = "cache_res"
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_use = "cache_res2"
            if file_to_use:
                try:
                    with open(os.path.join(BASE_DIR, file_to_use), "rb") as f: gz_data = f.read()
                    raw_data = gzip.decompress(gz_data)
                    new_line = f"cache_res,{sha1_b64(raw_data)},{len(raw_data)},0,{sha1_b64(gz_data)},{len(gz_data)},True,0"
                    new_lines.append(new_line); continue
                except Exception as e: print(f"Error: {e}")
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
        overrides = ANTI_BAN_OVERRIDES
        if overrides:
            gamevar = data.get("gamevar", "")
            for var_name, val in overrides.items():
                gamevar += f"\n{var_name},{var_name},{val['var_type']},{val['var_value']},,"
            data["gamevar"] = gamevar
        return json.dumps(data)
    except: return text

# ==================== BLUE NEON HTML UI ====================
LOGIN_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Secure Access</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;min-height:100vh;display:flex;justify-content:center;align-items:center;color:#8892b0}
.box{background:#112240;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #233554;box-shadow:0 20px 60px -15px rgba(2,12,27,0.7), 0 0 20px rgba(0,212,255,0.1)}
h2{text-align:center;font-size:24px;color:#ccd6f6;margin-bottom:5px;letter-spacing:2px;text-shadow: 0 0 10px rgba(0,212,255,0.5)}
h2 span{color:#64ffda;text-shadow: 0 0 10px rgba(100,255,218,0.7)}
p.sub{text-align:center;font-size:11px;color:#495670;margin-bottom:30px;letter-spacing:1px}
input{width:100%;padding:15px;background:#020c1b;border:1px solid #233554;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;outline:none;transition:0.3s}
input:focus{border-color:#64ffda;box-shadow:0 0 10px rgba(100,255,218,0.2)}
button{width:100%;padding:15px;background:transparent;border:1px solid #64ffda;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;font-weight:bold;cursor:pointer;letter-spacing:2px;transition:0.3s;margin-top:10px}
button:hover{background:rgba(100,255,218,0.1);box-shadow:0 0 20px rgba(100,255,218,0.3);transform:translateY(-2px)}
.msg{color:#ff6b6b;text-align:center;margin-top:15px;font-size:12px;text-shadow:0 0 5px rgba(255,107,107,0.5)}
</style></head><body>
<div class="box">
    <h2>ADMIN <span>ACCESS</span></h2>
    <p class="sub">PROXY TERMINAL v2.0</p>
    <form method="POST">
        <input type="password" name="password" placeholder="ENTER ACCESS KEY" required>
        <button type="submit">AUTHENTICATE</button>
    </form>
    {% if error %}<div class="msg">{{ error }}</div>{% endif %}
</div>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Terminal Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;color:#8892b0;min-height:100vh;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px;padding-bottom:15px;border-bottom:1px solid #233554}
.brand{font-size:18px;color:#ccd6f6;letter-spacing:2px}.brand span{color:#64ffda}
.logout{color:#8892b0;text-decoration:none;font-size:11px;border:1px solid #233554;padding:8px 14px;border-radius:6px;transition:0.3s}
.logout:hover{color:#ff6b6b;border-color:#ff6b6b;box-shadow:0 0 10px rgba(255,107,107,0.2)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px}
.card{background:#112240;padding:20px;border-radius:12px;border:1px solid #233554;box-shadow:0 10px 30px -15px rgba(2,12,27,0.7)}
.card h3{font-size:10px;color:#495670;text-transform:uppercase;letter-spacing:3px;margin-bottom:15px}
.stat-number{font-size:48px;font-weight:bold;color:#00d4ff;text-shadow:0 0 20px rgba(0,212,255,0.6);line-height:1}
.stat-label{font-size:12px;color:#64ffda;margin-top:8px;letter-spacing:1px}
.toggle-row{display:flex;justify-content:space-between;align-items:center;background:#0a192f;padding:15px;border-radius:8px;border:1px solid #233554}
.info h4{font-size:14px;color:#ccd6f6;margin-bottom:4px}.info p{font-size:10px;color:#495670}
.sw{width:50px;height:26px;background:#233554;border-radius:15px;cursor:pointer;position:relative;transition:0.3s;border:1px solid #495670}
.sw .dot{width:20px;height:20px;background:#8892b0;border-radius:50%;position:absolute;top:2px;left:2px;transition:0.3s}
.sw.on{background:rgba(255,0,64,0.2);border-color:#ff0040;box-shadow:0 0 15px rgba(255,0,64,0.4)}
.sw.on .dot{left:26px;background:#ff0040;box-shadow:0 0 10px rgba(255,0,64,0.8)}
.btn-row{display:flex;gap:10px;margin-top:10px}
.btn-reset{flex:1;padding:12px;background:transparent;border:1px solid #233554;border-radius:8px;color:#8892b0;font-size:11px;font-family:inherit;cursor:pointer;transition:0.3s;text-align:center}
.btn-reset:hover{border-color:#00d4ff;color:#00d4ff;box-shadow:0 0 15px rgba(0,212,255,0.2)}
.tg-btn{display:block;width:100%;padding:14px;background:rgba(0,136,204,0.1);border:1px solid #0088cc;border-radius:8px;color:#00d4ff;font-size:12px;font-family:inherit;font-weight:bold;text-align:center;text-decoration:none;transition:0.3s;letter-spacing:1px}
.tg-btn:hover{background:rgba(0,136,204,0.2);box-shadow:0 0 20px rgba(0,212,255,0.3)}
</style></head><body>
<div class="header">
    <div class="brand">PROXY <span>TERMINAL</span></div>
    <a href="/admin/logout" class="logout">[ DISCONNECT ]</a>
</div>
<div class="grid">
    <div class="card">
        <h3>// Active Connections</h3>
        <div class="stat-number" id="deviceCount">0</div>
        <div class="stat-label">DEVICES CONNECTED</div>
        <div class="btn-row">
            <button class="btn-reset" onclick="resetCounter()">[ RESET COUNTER ]</button>
        </div>
    </div>
    <div class="card">
        <h3>// System Status</h3>
        <div class="toggle-row">
            <div class="info">
                <h4>Maintenance Mode</h4>
                <p>Block access / Show TG</p>
            </div>
            <div class="sw {% if maintenance %}on{% endif %}" id="maintToggle" onclick="toggleMaint()">
                <div class="dot"></div>
            </div>
        </div>
    </div>
</div>
<div class="card" style="margin-top:0">
    <h3>// Network Links</h3>
    <a href="TELEGRAM_LINK_HOLDER" target="_blank" class="tg-btn">[ CONNECT TO TELEGRAM ]</a>
</div>
<script>
function loadStats(){fetch('/admin/api/stats').then(r=>r.json()).then(d=>{document.getElementById('deviceCount').innerText=d.devices;});}
function toggleMaint(){const sw=document.getElementById('maintToggle');fetch('/admin/api/toggle_maintenance',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success)sw.classList.toggle('on');});}
function resetCounter(){if(confirm('Reset device counter to 0?')){fetch('/admin/api/reset_ips',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success)loadStats();});}}
loadStats();setInterval(loadStats, 5000);
</script>
</body></html>
"""

# ==================== ADMIN ROUTES ====================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'logged_in' in session: return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else: error = "ACCESS DENIED: INVALID KEY"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' not in session: return redirect(url_for('admin_login'))
    final_html = DASHBOARD_HTML.replace("TELEGRAM_LINK_HOLDER", TELEGRAM_LINK)
    return render_template_string(final_html, maintenance=app_data["maintenance"])

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
    return redirect(url_for('admin_login'))

# ==================== GAME PROXY ROUTES ====================
@app.route('/')
def home():
    return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if full_path.startswith('admin'): return Response("Invalid Endpoint", status=404)

    # --- DEVICE COUNTER LOGIC (RAM BASED) ---
    client_ip = get_client_ip()
    app_data["connected_ips"].add(client_ip)

    # --- MAINTENANCE CHECK ---
    if app_data["maintenance"]:
        maint_response = {"maint": "true", "msg": "Server Under Maintenance! Join Telegram.", "url": TELEGRAM_LINK}
        return Response(json.dumps(maint_response), status=503, content_type="application/json")

    # --- NORMAL PROXY LOGIC ---
    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        print(f"[{datetime.now()}] {client_ip} | Status: {config}")
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            modified_data = modify_ver(resp.text, config)
            response = Response(modified_data, status=200, content_type="application/json")
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        config = read_url_config(full_path)

        if "assetindexer" in file_path_str:
            if config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
                with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_read = os.path.join(BASE_DIR, "cache_res2")
            if file_to_read:
                with open(file_to_read, "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            target_url = TARGET_BASE_URL + file_path_str
            try:
                resp = requests.get(target_url, timeout=30)
                patched_text = patch_fileinfo(resp.text, config)
                return Response(patched_text.encode(), content_type="binary/octet-stream")
            except Exception as e: return Response(f"Error: {e}", status=502)
                
        target_url = TARGET_BASE_URL + file_path_str
        try:
            resp = requests.get(target_url, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e: return Response(f"Error: {e}", status=502)

    return Response("Invalid Endpoint", status=404)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  NEON TERMINAL PROXY v3.0 (RAILWAY STABLE)")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)    return "\n".join(new_lines)

def modify_ver(text, config):
    try:
        data = json.loads(text)
        if config["HS_NECK"] or config["HS_CHEST"] or config["ASSET_INDEXER"]:
            my_cdn = f"https://{request.host}/cdn/live/ABHotUpdates/"
            data["cdn_url"] = my_cdn
            data["backup_cdn_url"] = my_cdn
            data["abhotupdate_cdn_url"] = my_cdn
        overrides = ANTI_BAN_OVERRIDES
        if overrides:
            gamevar = data.get("gamevar", "")
            for var_name, val in overrides.items():
                gamevar += f"\n{var_name},{var_name},{val['var_type']},{val['var_value']},,"
            data["gamevar"] = gamevar
        return json.dumps(data)
    except: return text

# ==================== BLUE NEON HTML UI ====================
LOGIN_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Secure Access</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;min-height:100vh;display:flex;justify-content:center;align-items:center;color:#8892b0}
.box{background:#112240;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #233554;box-shadow:0 20px 60px -15px rgba(2,12,27,0.7), 0 0 20px rgba(0,212,255,0.1)}
h2{text-align:center;font-size:24px;color:#ccd6f6;margin-bottom:5px;letter-spacing:2px;text-shadow: 0 0 10px rgba(0,212,255,0.5)}
h2 span{color:#64ffda;text-shadow: 0 0 10px rgba(100,255,218,0.7)}
p.sub{text-align:center;font-size:11px;color:#495670;margin-bottom:30px;letter-spacing:1px}
input{width:100%;padding:15px;background:#020c1b;border:1px solid #233554;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;outline:none;transition:0.3s}
input:focus{border-color:#64ffda;box-shadow:0 0 10px rgba(100,255,218,0.2)}
button{width:100%;padding:15px;background:transparent;border:1px solid #64ffda;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;font-weight:bold;cursor:pointer;letter-spacing:2px;transition:0.3s;margin-top:10px}
button:hover{background:rgba(100,255,218,0.1);box-shadow:0 0 20px rgba(100,255,218,0.3);transform:translateY(-2px)}
.msg{color:#ff6b6b;text-align:center;margin-top:15px;font-size:12px;text-shadow:0 0 5px rgba(255,107,107,0.5)}
</style></head><body>
<div class="box">
    <h2>ADMIN <span>ACCESS</span></h2>
    <p class="sub">PROXY TERMINAL v2.0</p>
    <form method="POST">
        <input type="password" name="password" placeholder="ENTER ACCESS KEY" required>
        <button type="submit">AUTHENTICATE</button>
    </form>
    {% if error %}<div class="msg">{{ error }}</div>{% endif %}
</div>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Terminal Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;color:#8892b0;min-height:100vh;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px;padding-bottom:15px;border-bottom:1px solid #233554}
.brand{font-size:18px;color:#ccd6f6;letter-spacing:2px}.brand span{color:#64ffda}
.logout{color:#8892b0;text-decoration:none;font-size:11px;border:1px solid #233554;padding:8px 14px;border-radius:6px;transition:0.3s}
.logout:hover{color:#ff6b6b;border-color:#ff6b6b;box-shadow:0 0 10px rgba(255,107,107,0.2)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px}
.card{background:#112240;padding:20px;border-radius:12px;border:1px solid #233554;box-shadow:0 10px 30px -15px rgba(2,12,27,0.7)}
.card h3{font-size:10px;color:#495670;text-transform:uppercase;letter-spacing:3px;margin-bottom:15px}
.stat-number{font-size:48px;font-weight:bold;color:#00d4ff;text-shadow:0 0 20px rgba(0,212,255,0.6);line-height:1}
.stat-label{font-size:12px;color:#64ffda;margin-top:8px;letter-spacing:1px}
.toggle-row{display:flex;justify-content:space-between;align-items:center;background:#0a192f;padding:15px;border-radius:8px;border:1px solid #233554}
.info h4{font-size:14px;color:#ccd6f6;margin-bottom:4px}.info p{font-size:10px;color:#495670}
.sw{width:50px;height:26px;background:#233554;border-radius:15px;cursor:pointer;position:relative;transition:0.3s;border:1px solid #495670}
.sw .dot{width:20px;height:20px;background:#8892b0;border-radius:50%;position:absolute;top:2px;left:2px;transition:0.3s}
.sw.on{background:rgba(255,0,64,0.2);border-color:#ff0040;box-shadow:0 0 15px rgba(255,0,64,0.4)}
.sw.on .dot{left:26px;background:#ff0040;box-shadow:0 0 10px rgba(255,0,64,0.8)}
.btn-row{display:flex;gap:10px;margin-top:10px}
.btn-reset{flex:1;padding:12px;background:transparent;border:1px solid #233554;border-radius:8px;color:#8892b0;font-size:11px;font-family:inherit;cursor:pointer;transition:0.3s;text-align:center}
.btn-reset:hover{border-color:#00d4ff;color:#00d4ff;box-shadow:0 0 15px rgba(0,212,255,0.2)}
.tg-btn{display:block;width:100%;padding:14px;background:rgba(0,136,204,0.1);border:1px solid #0088cc;border-radius:8px;color:#00d4ff;font-size:12px;font-family:inherit;font-weight:bold;text-align:center;text-decoration:none;transition:0.3s;letter-spacing:1px}
.tg-btn:hover{background:rgba(0,136,204,0.2);box-shadow:0 0 20px rgba(0,212,255,0.3)}
</style></head><body>
<div class="header">
    <div class="brand">PROXY <span>TERMINAL</span></div>
    <a href="/admin/logout" class="logout">[ DISCONNECT ]</a>
</div>
<div class="grid">
    <div class="card">
        <h3>// Active Connections</h3>
        <div class="stat-number" id="deviceCount">0</div>
        <div class="stat-label">DEVICES CONNECTED</div>
        <div class="btn-row">
            <button class="btn-reset" onclick="resetCounter()">[ RESET COUNTER ]</button>
        </div>
    </div>
    <div class="card">
        <h3>// System Status</h3>
        <div class="toggle-row">
            <div class="info">
                <h4>Maintenance Mode</h4>
                <p>Block access / Show TG</p>
            </div>
            <div class="sw {% if maintenance %}on{% endif %}" id="maintToggle" onclick="toggleMaint()">
                <div class="dot"></div>
            </div>
        </div>
    </div>
</div>
<div class="card" style="margin-top:0">
    <h3>// Network Links</h3>
    <a href="TELEGRAM_LINK_HOLDER" target="_blank" class="tg-btn">[ CONNECT TO TELEGRAM ]</a>
</div>
<script>
function loadStats(){fetch('/admin/api/stats').then(r=>r.json()).then(d=>{document.getElementById('deviceCount').innerText=d.devices;});}
function toggleMaint(){const sw=document.getElementById('maintToggle');fetch('/admin/api/toggle_maintenance',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success)sw.classList.toggle('on');});}
function resetCounter(){if(confirm('Reset device counter to 0?')){fetch('/admin/api/reset_ips',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success)loadStats();});}}
loadStats();setInterval(loadStats, 5000);
</script>
</body></html>
"""

# ==================== ADMIN ROUTES ====================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'logged_in' in session: return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else: error = "ACCESS DENIED: INVALID KEY"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' not in session: return redirect(url_for('admin_login'))
    data = load_data()
    # FIX: Yahan safely link inject kar rahe hain
    final_html = DASHBOARD_HTML.replace("TELEGRAM_LINK_HOLDER", TELEGRAM_LINK)
    return render_template_string(final_html, maintenance=data.get('maintenance', False))

@app.route('/admin/api/stats')
def admin_stats():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    ips = load_ips()
    return jsonify({"devices": len(ips), "ips": list(ips)})

@app.route('/admin/api/reset_ips', methods=['POST'])
def admin_reset_ips():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    reset_ips()
    return jsonify({"success": True})

@app.route('/admin/api/toggle_maintenance', methods=['POST'])
def api_toggle_maintenance():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    data = load_data()
    data['maintenance'] = not data.get('maintenance', False)
    save_data(data)
    return jsonify({"success": True, "maintenance": data['maintenance']})

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

# ==================== GAME PROXY ROUTES ====================
@app.route('/')
def home():
    return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if full_path.startswith('admin'): return Response("Invalid Endpoint", status=404)

    # --- DEVICE COUNTER LOGIC ---
    client_ip = get_client_ip()
    save_ip(client_ip)

    # --- MAINTENANCE CHECK ---
    data = load_data()
    if data.get('maintenance', False):
        maint_response = {"maint": "true", "msg": "Server Under Maintenance! Join Telegram.", "url": TELEGRAM_LINK}
        return Response(json.dumps(maint_response), status=503, content_type="application/json")

    # --- NORMAL PROXY LOGIC ---
    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        print(f"[{datetime.now()}] {client_ip} | Status: {config}")
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            modified_data = modify_ver(resp.text, config)
            response = Response(modified_data, status=200, content_type="application/json")
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        config = read_url_config(full_path)

        if "assetindexer" in file_path_str:
            if config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
                with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_read = os.path.join(BASE_DIR, "cache_res2")
            if file_to_read:
                with open(file_to_read, "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            target_url = TARGET_BASE_URL + file_path_str
            try:
                resp = requests.get(target_url, timeout=30)
                patched_text = patch_fileinfo(resp.text, config)
                return Response(patched_text.encode(), content_type="binary/octet-stream")
            except Exception as e: return Response(f"Error: {e}", status=502)
                
        target_url = TARGET_BASE_URL + file_path_str
        try:
            resp = requests.get(target_url, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e: return Response(f"Error: {e}", status=502)

    return Response("Invalid Endpoint", status=404)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  NEON TERMINAL PROXY v2.0 (STABLE)")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)    return "\n".join(new_lines)

def modify_ver(text, config):
    try:
        data = json.loads(text)
        if config["HS_NECK"] or config["HS_CHEST"] or config["ASSET_INDEXER"]:
            my_cdn = f"https://{request.host}/cdn/live/ABHotUpdates/"
            data["cdn_url"] = my_cdn
            data["backup_cdn_url"] = my_cdn
            data["abhotupdate_cdn_url"] = my_cdn
        overrides = ANTI_BAN_OVERRIDES
        if overrides:
            gamevar = data.get("gamevar", "")
            for var_name, val in overrides.items():
                gamevar += f"\n{var_name},{var_name},{val['var_type']},{val['var_value']},,"
            data["gamevar"] = gamevar
        return json.dumps(data)
    except: return text

# ==================== BLUE NEON HTML UI ====================
LOGIN_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Secure Access</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;min-height:100vh;display:flex;justify-content:center;align-items:center;color:#8892b0}
.box{background:#112240;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #233554;box-shadow:0 20px 60px -15px rgba(2,12,27,0.7), 0 0 20px rgba(0,212,255,0.1)}
h2{text-align:center;font-size:24px;color:#ccd6f6;margin-bottom:5px;letter-spacing:2px;text-shadow: 0 0 10px rgba(0,212,255,0.5)}
h2 span{color:#64ffda;text-shadow: 0 0 10px rgba(100,255,218,0.7)}
p.sub{text-align:center;font-size:11px;color:#495670;margin-bottom:30px;letter-spacing:1px}
input{width:100%;padding:15px;background:#020c1b;border:1px solid #233554;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;outline:none;transition:0.3s}
input:focus{border-color:#64ffda;box-shadow:0 0 10px rgba(100,255,218,0.2)}
button{width:100%;padding:15px;background:transparent;border:1px solid #64ffda;border-radius:8px;color:#64ffda;font-size:14px;font-family:inherit;font-weight:bold;cursor:pointer;letter-spacing:2px;transition:0.3s;margin-top:10px}
button:hover{background:rgba(100,255,218,0.1);box-shadow:0 0 20px rgba(100,255,218,0.3);transform:translateY(-2px)}
.msg{color:#ff6b6b;text-align:center;margin-top:15px;font-size:12px;text-shadow:0 0 5px rgba(255,107,107,0.5)}
</style></head><body>
<div class="box">
    <h2>ADMIN <span>ACCESS</span></h2>
    <p.sub>PROXY TERMINAL v2.0</p>
    <form method="POST">
        <input type="password" name="password" placeholder="ENTER ACCESS KEY" required>
        <button type="submit">AUTHENTICATE</button>
    </form>
    {% if error %}<div class="msg">{{ error }}</div>{% endif %}
</div>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Terminal Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New', Courier, monospace}
body{background:#020c1b;color:#8892b0;min-height:100vh;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px;padding-bottom:15px;border-bottom:1px solid #233554}
.brand{font-size:18px;color:#ccd6f6;letter-spacing:2px}.brand span{color:#64ffda}
.logout{color:#8892b0;text-decoration:none;font-size:11px;border:1px solid #233554;padding:8px 14px;border-radius:6px;transition:0.3s}
.logout:hover{color:#ff6b6b;border-color:#ff6b6b;box-shadow:0 0 10px rgba(255,107,107,0.2)}

.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px}
.card{background:#112240;padding:20px;border-radius:12px;border:1px solid #233554;box-shadow:0 10px 30px -15px rgba(2,12,27,0.7)}
.card h3{font-size:10px;color:#495670;text-transform:uppercase;letter-spacing:3px;margin-bottom:15px}

.stat-number{font-size:48px;font-weight:bold;color:#00d4ff;text-shadow:0 0 20px rgba(0,212,255,0.6);line-height:1}
.stat-label{font-size:12px;color:#64ffda;margin-top:8px;letter-spacing:1px}

.toggle-row{display:flex;justify-content:space-between;align-items:center;background:#0a192f;padding:15px;border-radius:8px;border:1px solid #233554}
.info h4{font-size:14px;color:#ccd6f6;margin-bottom:4px}.info p{font-size:10px;color:#495670}
.sw{width:50px;height:26px;background:#233554;border-radius:15px;cursor:pointer;position:relative;transition:0.3s;border:1px solid #495670}
.sw .dot{width:20px;height:20px;background:#8892b0;border-radius:50%;position:absolute;top:2px;left:2px;transition:0.3s}
.sw.on{background:rgba(255,0,64,0.2);border-color:#ff0040;box-shadow:0 0 15px rgba(255,0,64,0.4)}
.sw.on .dot{left:26px;background:#ff0040;box-shadow:0 0 10px rgba(255,0,64,0.8)}

.btn-row{display:flex;gap:10px;margin-top:10px}
.btn-reset{flex:1;padding:12px;background:transparent;border:1px solid #233554;border-radius:8px;color:#8892b0;font-size:11px;font-family:inherit;cursor:pointer;transition:0.3s;text-align:center}
.btn-reset:hover{border-color:#00d4ff;color:#00d4ff;box-shadow:0 0 15px rgba(0,212,255,0.2)}
.tg-btn{display:block;width:100%;padding:14px;background:rgba(0,136,204,0.1);border:1px solid #0088cc;border-radius:8px;color:#00d4ff;font-size:12px;font-family:inherit;font-weight:bold;text-align:center;text-decoration:none;transition:0.3s;letter-spacing:1px}
.tg-btn:hover{background:rgba(0,136,204,0.2);box-shadow:0 0 20px rgba(0,212,255,0.3)}
</style></head><body>
<div class="header">
    <div class="brand">PROXY <span>TERMINAL</span></div>
    <a href="/admin/logout" class="logout">[ DISCONNECT ]</a>
</div>

<div class="grid">
    <div class="card">
        <h3>// Active Connections</h3>
        <div class="stat-number" id="deviceCount">0</div>
        <div class="stat-label">DEVICES CONNECTED</div>
        <div class="btn-row">
            <button class="btn-reset" onclick="resetCounter()">[ RESET COUNTER ]</button>
        </div>
    </div>
    <div class="card">
        <h3>// System Status</h3>
        <div class="toggle-row">
            <div class="info">
                <h4>Maintenance Mode</h4>
                <p>Block access / Show TG</p>
            </div>
            <div class="sw {% if maintenance %}on{% endif %}" id="maintToggle" onclick="toggleMaint()">
                <div class="dot"></div>
            </div>
        </div>
    </div>
</div>

<div class="card" style="margin-top:0">
    <h3>// Network Links</h3>
    <a href="""" + TELEGRAM_LINK + """' target="_blank" class="tg-btn">[ CONNECT TO TELEGRAM ]</a>
</div>

<script>
function loadStats(){
    fetch('/admin/api/stats').then(r=>r.json()).then(d=>{
        document.getElementById('deviceCount').innerText = d.devices;
    });
}
function toggleMaint(){
    const sw = document.getElementById('maintToggle');
    fetch('/admin/api/toggle_maintenance', {method:'POST'}).then(r=>r.json()).then(d=>{
        if(d.success) sw.classList.toggle('on');
    });
}
function resetCounter(){
    if(confirm('Reset device counter to 0?')){
        fetch('/admin/api/reset_ips', {method:'POST'}).then(r=>r.json()).then(d=>{
            if(d.success) loadStats();
        });
    }
}
// Initial load
loadStats();
// Refresh every 5 seconds to show live count
setInterval(loadStats, 5000);
</script>
</body></html>
"""

# ==================== ADMIN ROUTES ====================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'logged_in' in session: return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else: error = "ACCESS DENIED: INVALID KEY"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' not in session: return redirect(url_for('admin_login'))
    data = load_data()
    return render_template_string(DASHBOARD_HTML, maintenance=data.get('maintenance', False))

@app.route('/admin/api/stats')
def admin_stats():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    ips = load_ips()
    return jsonify({"devices": len(ips), "ips": list(ips)})

@app.route('/admin/api/reset_ips', methods=['POST'])
def admin_reset_ips():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    reset_ips()
    return jsonify({"success": True})

@app.route('/admin/api/toggle_maintenance', methods=['POST'])
def api_toggle_maintenance():
    if 'logged_in' not in session: return jsonify({"success": False}), 401
    data = load_data()
    data['maintenance'] = not data.get('maintenance', False)
    save_data(data)
    return jsonify({"success": True, "maintenance": data['maintenance']})

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

# ==================== GAME PROXY ROUTES ====================
@app.route('/')
def home():
    return "Proxy Server is Live!"

@app.route('/<path:full_path>', methods=['GET'])
def handle_all_requests(full_path):
    if full_path.startswith('admin'): return Response("Invalid Endpoint", status=404)

    # --- DEVICE COUNTER LOGIC ---
    client_ip = get_client_ip()
    save_ip(client_ip)

    # --- MAINTENANCE CHECK ---
    data = load_data()
    if data.get('maintenance', False):
        maint_response = {"maint": "true", "msg": "Server Under Maintenance! Join Telegram.", "url": TELEGRAM_LINK}
        return Response(json.dumps(maint_response), status=503, content_type="application/json")

    # --- NORMAL PROXY LOGIC ---
    if 'ver.php' in full_path:
        config = read_url_config(full_path)
        print(f"[{datetime.now()}] {client_ip} | Status: {config}")
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        try:
            resp = requests.get(VER_PHP_URL, headers=headers, timeout=15)
            modified_data = modify_ver(resp.text, config)
            response = Response(modified_data, status=200, content_type="application/json")
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            return Response(f"Error: {e}", status=502)

    elif 'cdn/live/abhotupdates/' in full_path.lower():
        file_path_str = full_path.lower().split('cdn/live/abhotupdates/')[-1]
        config = read_url_config(full_path)

        if "assetindexer" in file_path_str:
            if config["ASSET_INDEXER"] and os.path.exists(os.path.join(BASE_DIR, "cache_res3")):
                with open(os.path.join(BASE_DIR, "cache_res3"), "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                    
        if "cache_res" in file_path_str:
            file_to_read = None
            if config["HS_NECK"] and os.path.exists(os.path.join(BASE_DIR, "cache_res")): file_to_read = os.path.join(BASE_DIR, "cache_res")
            elif config["HS_CHEST"] and os.path.exists(os.path.join(BASE_DIR, "cache_res2")): file_to_read = os.path.join(BASE_DIR, "cache_res2")
            if file_to_read:
                with open(file_to_read, "rb") as f: return Response(f.read(), content_type="application/octet-stream")
                
        if "fileinfo" in file_path_str:
            target_url = TARGET_BASE_URL + file_path_str
            try:
                resp = requests.get(target_url, timeout=30)
                patched_text = patch_fileinfo(resp.text, config)
                return Response(patched_text.encode(), content_type="binary/octet-stream")
            except Exception as e: return Response(f"Error: {e}", status=502)
                
        target_url = TARGET_BASE_URL + file_path_str
        try:
            resp = requests.get(target_url, timeout=30)
            return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
        except Exception as e: return Response(f"Error: {e}", status=502)

    return Response("Invalid Endpoint", status=404)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  NEON TERMINAL PROXY v2.0")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
