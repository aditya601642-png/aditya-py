import os
import re
import json
import gzip
import hashlib
import base64
import requests
import string
import random
import threading
import time
from flask import Flask, request, Response, jsonify, session, redirect, url_for, render_template_string
from datetime import datetime, timedelta
from functools import wraps
import socket

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

# ==================== CONFIG ====================
TARGET_BASE_URL = "https://dl.bs.freefiremobile.com/live/ABHotUpdates/"
VER_PHP_URL = "https://version.ggwhitehawk.com/live/ver.php"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', 10000))

ADMIN_USER = "UXDEMONOFC"
ADMIN_PASS = "Aditya@7457$aditya*7457"

# Data file paths
DATA_FILE = os.path.join(BASE_DIR, "crx_data.json")

user_configs = {}
registered_ips = {}
generated_keys = {}
key_expiry = {}

DEFAULT_CONFIG = {
    "HS_NECK": False,
    "HS_CHEST": False,
    "BYPASSV1": True,
    "BACKJUMPV1": False,
    "HIGH_SENSI": False,
    "ZIG_ZAG_MOVE": False
}

ANTI_BAN_OVERRIDES = {
    "CleanFFAntiState": {"var_type": "bool", "var_value": "true"},
    "FFAntihackDefenceLevel": {"var_type": "string", "var_value": "0"},
    "FFAntihackLightInitOnThread": {"var_type": "bool", "var_value": "false"},
    "FFAntihackEmulatorCheckDisbaledClientVariant": {"var_type": "string", "var_value": ""},
    "FFAntihackSDKDetailEncryptBySHA1": {"var_type": "bool", "var_value": "false"},
    "EnableFFAntihackInfoExtra": {"var_type": "bool", "var_value": "false"},
    "CheckHacker": {"var_type": "bool", "var_value": "false"},
    "DebugHack": {"var_type": "bool", "var_value": "false"},
    "TestModeEnabled": {"var_type": "bool", "var_value": "true"},
    "EarlyInitGGP": {"var_type": "bool", "var_value": "false"},
    "DisableGinInfoSend": {"var_type": "int", "var_value": "1"},
    "GinInfoBRAliveThreshold": {"var_type": "int", "var_value": "0"},
    "AntiHackResetSubgameInterval": {"var_type": "int", "var_value": "0"},
    "FFANTIHACKEXT_SPLIT_THRESHOLD": {"var_type": "int", "var_value": "0"},
    "NeedProcessAH": {"var_type": "bool", "var_value": "true"},
    "EnablePlatformCheck": {"var_type": "bool", "var_value": "false"},
    "EnableSupCheck": {"var_type": "bool", "var_value": "false"},
    "EnableMMKPlatformCheck": {"var_type": "bool", "var_value": "false"},
    "ShowHighFrameRateSetting": {"var_type": "bool", "var_value": "true"},
    "Real60FrameSwitch": {"var_type": "bool", "var_value": "true"},
    "IsAlbumScreenShotNeedAntiMod": {"var_type": "bool", "var_value": "false"},
    "EnableIceWallHacker": {"var_type": "bool", "var_value": "false"},
    "EnableIceWallHackerKill": {"var_type": "bool", "var_value": "false"},
    "EnableHipHackerKill": {"var_type": "bool", "var_value": "false"},
    "EnableSendHackStoreLog": {"var_type": "bool", "var_value": "false"},
    "SystemAlbumImageAntiModStrategy": {"var_type": "int", "var_value": "0"},
    "AlbumImageAntiModSecs": {"var_type": "int", "var_value": "0"},
    "AlbumImageAntiMod_iOS": {"var_type": "bool", "var_value": "false"},
    "ReportInstantiateJank": {"var_type": "bool", "var_value": "false"},
    "InstantiateJankTimeLimit": {"var_type": "int", "var_value": "0"},
    "DisableKillRefreshGetTime": {"var_type": "int", "var_value": "0"},
    "BugReportIntervalOnLowMemory": {"var_type": "int", "var_value": "0"},
    "EnableIngameQuickReport": {"var_type": "bool", "var_value": "false"},
    "EnableBugReportTime": {"var_type": "bool", "var_value": "false"},
    "EnableBugReportEarly": {"var_type": "int", "var_value": "0"},
    "BugReportMaxCountPerSession": {"var_type": "int", "var_value": "0"},
    "KickUserInMatchGame": {"var_type": "bool", "var_value": "false"},
    "Reportee_Damager_RecentlyMaxCnt": {"var_type": "int", "var_value": "0"},
    "Reportee_Killer_RecentlyMaxCnt": {"var_type": "int", "var_value": "0"},
    "BlocklistMaxNum": {"var_type": "int", "var_value": "0"},
    "EnableCheckFileStates": {"var_type": "bool", "var_value": "false"},
    "OptionalDeepFileCheck": {"var_type": "bool", "var_value": "false"},
    "EnableFileCacherReadOpt": {"var_type": "bool", "var_value": "false"},
    "EnableFileCacherReadOpt_2022": {"var_type": "bool", "var_value": "false"},
    "EnableGGPDecryptFailureProtection": {"var_type": "bool", "var_value": "false"}
}

BACKJUMPV1_OVERRIDES = {
    "EnableAccelerationOnFalling": {"var_type": "bool", "var_value": "false"},
    "CanJumpFallingRunFast": {"var_type": "bool", "var_value": "false"},
    "CanCreepRunFast": {"var_type": "bool", "var_value": "false"},
    "CanCrouchingRunFast": {"var_type": "bool", "var_value": "false"},
    "StropFallingResetSpeed": {"var_type": "bool", "var_value": "true"}
}

HIGH_SENSI_OVERRIDES = {
    "SensitivityMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "Sensitivity1PMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "X1ScopeMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "X2ScopeMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "X4ScopeMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "X8ScopeMaxSetting": {"var_type": "float", "var_value": "9.0"},
    "FreeLookMaxSetting": {"var_type": "float", "var_value": "9.0"}
}

ZIG_ZAG_MOVE_OVERRIDES = {
    "FreeMoveAngularSpeed": {"var_type": "float", "var_value": "9999.0"},
    "FreeMoveAngularSpeedStand": {"var_type": "float", "var_value": "9999.0"},
    "FreeMoveAngularSpeedCrouch": {"var_type": "float", "var_value": "9999.0"},
    "FreeMoveAngularSpeedCreep": {"var_type": "float", "var_value": "9999.0"},
    "ResetRotationSpeed": {"var_type": "float", "var_value": "9999.0"},
}

# ==================== KEEP ALIVE ====================
def keep_alive():
    while True:
        try:
            requests.get(f"http://localhost:{PORT}/api/ping", timeout=5)
            print(f"[{datetime.now()}] Keep-alive ping sent")
        except:
            pass
        time.sleep(240)

@app.route('/api/ping')
def ping():
    return jsonify({'status': 'alive', 'time': datetime.now().isoformat()})

threading.Thread(target=keep_alive, daemon=True).start()

# ==================== DATA PERSISTENCE ====================

def save_data():
    data = {
        'user_configs': user_configs,
        'registered_ips': registered_ips,
        'generated_keys': generated_keys,
        'key_expiry': {ip: exp.isoformat() for ip, exp in key_expiry.items()}
    }
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    global user_configs, registered_ips, generated_keys, key_expiry
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            user_configs = data.get('user_configs', {})
            registered_ips = data.get('registered_ips', {})
            generated_keys = data.get('generated_keys', {})
            key_expiry = {}
            for ip, exp_str in data.get('key_expiry', {}).items():
                try:
                    key_expiry[ip] = datetime.fromisoformat(exp_str)
                except:
                    pass
            print(f"Loaded data: {len(generated_keys)} keys, {len(registered_ips)} IPs")
        except Exception as e:
            print(f"Error loading data: {e}")
            user_configs = {}
            registered_ips = {}
            generated_keys = {}
            key_expiry = {}
    else:
        print("No existing data file found. Starting fresh.")
        user_configs = {}
        registered_ips = {}
        generated_keys = {}
        key_expiry = {}
        save_data()

# ========================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def get_user_config(client_ip):
    if client_ip not in user_configs:
        user_configs[client_ip] = DEFAULT_CONFIG.copy()
        save_data()
    return user_configs[client_ip]

def generate_key(prefix="CRX-HACKS"):
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{random_part}"

def get_overrides_for_ip(client_ip):
    config = get_user_config(client_ip)
    overrides = {}
    if config.get("BYPASSV1", False):
        overrides.update(ANTI_BAN_OVERRIDES)
    if config.get("BACKJUMPV1", False):
        overrides.update(BACKJUMPV1_OVERRIDES)
    if config.get("HIGH_SENSI", False):
        overrides.update(HIGH_SENSI_OVERRIDES)
    if config.get("ZIG_ZAG_MOVE", False):
        overrides.update(ZIG_ZAG_MOVE_OVERRIDES)
    return overrides

def sha1_b64(data):
    return base64.b64encode(hashlib.sha1(data).digest()).decode()

def patch_fileinfo(original_text, config):
    if not config.get("HS_NECK", False) and not config.get("HS_CHEST", False):
        return original_text
    lines = original_text.splitlines()
    new_lines = []
    cache_res_file = os.path.join(BASE_DIR, "cache_res")
    cache_res2_file = os.path.join(BASE_DIR, "cache_res2")
    for line in lines:
        if line.startswith("cache_res,"):
            if config.get("HS_NECK", False) and os.path.exists(cache_res_file):
                try:
                    with open(cache_res_file, "rb") as f:
                        gz_data = f.read()
                    raw_data = gzip.decompress(gz_data)
                    new_line = f"cache_res,{sha1_b64(raw_data)},{len(raw_data)},0,{sha1_b64(gz_data)},{len(gz_data)},True,0"
                    new_lines.append(new_line)
                except:
                    new_lines.append(line)
            elif config.get("HS_CHEST", False) and os.path.exists(cache_res2_file):
                try:
                    with open(cache_res2_file, "rb") as f:
                        gz_data = f.read()
                    raw_data = gzip.decompress(gz_data)
                    new_line = f"cache_res,{sha1_b64(raw_data)},{len(raw_data)},0,{sha1_b64(gz_data)},{len(gz_data)},True,0"
                    new_lines.append(new_line)
                except:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)

def modify_ver_response(response_text, client_ip):
    try:
        data = json.loads(response_text)
        cdn_url = f"https://{request.host}/cdn/live/ABHotUpdates/"
        data["cdn_url"] = cdn_url
        data["backup_cdn_url"] = cdn_url
        data["abhotupdate_cdn_url"] = cdn_url
        overrides = get_overrides_for_ip(client_ip)
        if overrides:
            gamevar = data.get("gamevar", "")
            for var_name, override in overrides.items():
                gamevar += f"\n{var_name},{var_name},{override['var_type']},{override['var_value']},,"
            data["gamevar"] = gamevar
        return json.dumps(data)
    except:
        return response_text

# ==================== ROUTES ====================

@app.route('/Po7eO', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template_string(LOGIN_PAGE, error="Invalid credentials")
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template_string(ADMIN_DASHBOARD, 
                                 keys=generated_keys, 
                                 ips=registered_ips,
                                 key_expiry=key_expiry)

@app.route('/admin/generate', methods=['POST'])
@login_required
def generate_new_key():
    data = request.json
    key_prefix = data.get('prefix', 'CRX-HACKS')
    ip_limit = int(data.get('limit', 1))
    days_valid = int(data.get('days', 7))
    new_key = generate_key(key_prefix)
    generated_keys[new_key] = {
        'prefix': key_prefix,
        'limit': ip_limit,
        'days': days_valid,
        'created': datetime.now().isoformat(),
        'used_ips': []
    }
    save_data()
    return jsonify({'key': new_key, 'limit': ip_limit, 'days': days_valid})

@app.route('/admin/revoke', methods=['POST'])
@login_required
def revoke_key():
    data = request.json
    key = data.get('key')
    if key in generated_keys:
        for ip in generated_keys[key]['used_ips']:
            if ip in registered_ips:
                del registered_ips[ip]
            if ip in key_expiry:
                del key_expiry[ip]
        del generated_keys[key]
        save_data()
        return jsonify({'success': True})
    return jsonify({'error': 'Key not found'}), 400

@app.route('/admin/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/verify', methods=['POST'])
def verify_key():
    client_ip = get_client_ip()
    data = request.json
    key = data.get('key', '').strip()
    
    if client_ip in registered_ips:
        return jsonify({'success': True, 'message': 'Already registered'})
    
    if key not in generated_keys:
        return jsonify({'success': False, 'message': 'Invalid key'}), 401
    
    key_data = generated_keys[key]
    if len(key_data['used_ips']) >= key_data['limit']:
        return jsonify({'success': False, 'message': 'Key limit reached'}), 401
    
    registered_ips[client_ip] = key
    key_data['used_ips'].append(client_ip)
    expiry_date = datetime.now() + timedelta(days=key_data['days'])
    key_expiry[client_ip] = expiry_date
    save_data()
    
    return jsonify({
        'success': True, 
        'message': 'Key verified successfully',
        'expires': expiry_date.isoformat()
    })

# ============ PROXY ROUTES - NO KEY REQUIRED ============

@app.route('/ver.php', methods=['GET'])
@app.route('/live/ver.php', methods=['GET'])
def handle_ver_php():
    client_ip = get_client_ip()
    params = dict(request.args)
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    try:
        response = requests.get(VER_PHP_URL, params=params, headers=headers, timeout=60)
        modified = modify_ver_response(response.text, client_ip)
        return Response(modified, status=200, content_type="application/json")
    except Exception as e:
        return Response(f"Error: {e}", status=502)

@app.route('/cdn/live/ABHotUpdates/', methods=['GET'])
@app.route('/cdn/live/ABHotUpdates/<path:path>', methods=['GET'])
def handle_cdn(path=""):
    client_ip = get_client_ip()
    config = get_user_config(client_ip)
    cache_file = os.path.join(BASE_DIR, "cache_res")
    cache_res2_file = os.path.join(BASE_DIR, "cache_res2")
    assetindexer_file = os.path.join(BASE_DIR, "cache_res3")
    
    if re.compile(r"android_astc/1\.123\.[^/]*/gameassetbundles/avatar/assetindexer").match(path) and os.path.exists(assetindexer_file):
        with open(assetindexer_file, "rb") as f:
            return Response(f.read(), status=200, content_type="application/octet-stream")
    
    if "cache_res" in path:
        if config.get("HS_NECK", False) and os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return Response(f.read(), status=200, content_type="application/octet-stream")
        elif config.get("HS_CHEST", False) and os.path.exists(cache_res2_file):
            with open(cache_res2_file, "rb") as f:
                return Response(f.read(), status=200, content_type="application/octet-stream")
    
    if "fileinfo" in path:
        target_url = TARGET_BASE_URL + path
        try:
            resp = requests.get(target_url, timeout=60)
            if config.get("HS_NECK", False) or config.get("HS_CHEST", False):
                patched = patch_fileinfo(resp.text, config)
                return Response(patched.encode(), status=200, content_type="binary/octet-stream")
            return Response(resp.content, status=200, content_type="binary/octet-stream")
        except Exception as e:
            return Response(f"Error: {e}", status=502)
    
    target_url = TARGET_BASE_URL + path
    try:
        resp = requests.get(target_url, timeout=60)
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('content-type', 'application/octet-stream'))
    except Exception as e:
        return Response(f"Error: {e}", status=502)

# ============ API ROUTES ============

@app.route('/api/status', methods=['GET'])
def api_status():
    client_ip = get_client_ip()
    config = get_user_config(client_ip)
    return jsonify({
        "ip": client_ip,
        "config": config,
        "key": registered_ips.get(client_ip),
        "expires": key_expiry.get(client_ip, "").isoformat() if client_ip in key_expiry else None
    })

@app.route('/api/toggle', methods=['POST'])
def api_toggle():
    client_ip = get_client_ip()
    data = request.json
    feature = data.get('feature')
    value = data.get('value')
    
    feature_map = {
        'hs_neck': 'HS_NECK',
        'hs_chest': 'HS_CHEST',
        'backjump_v1': 'BACKJUMPV1',
        'high_sensi': 'HIGH_SENSI',
        'zig_zag_move': 'ZIG_ZAG_MOVE'
    }
    
    config_key = feature_map.get(feature)
    if not config_key:
        return jsonify({"error": "Invalid feature"}), 400
    
    config = get_user_config(client_ip)
    config[config_key] = value
    save_data()
    
    return jsonify({
        "success": True,
        "ip": client_ip,
        "feature": feature,
        "value": value
    })

@app.route('/api/ip/check', methods=['GET'])
def api_ip_check():
    client_ip = get_client_ip()
    return jsonify({
        "ip": client_ip,
        "key": registered_ips.get(client_ip),
        "is_authorized": client_ip in registered_ips,
        "expires": key_expiry.get(client_ip, "").isoformat() if client_ip in key_expiry else None
    })

@app.route('/')
def landing():
    return render_template_string(LANDING_PAGE)

@app.route('/dashboard')
def dashboard():
    if not session.get('unlocked'):
        return redirect(url_for('landing'))
    return render_template_string(DASHBOARD_PAGE)

@app.route('/unlock', methods=['POST'])
def unlock():
    session['unlocked'] = True
    return jsonify({'success': True})

# ==================== HTML TEMPLATES ====================

LOGIN_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REACH PANEL · Admin</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#08080e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:'Segoe UI',system-ui,sans-serif;background-image:radial-gradient(ellipse at 50% 0%,rgba(108,92,231,0.06),transparent 60%)}
        .container{background:rgba(16,16,28,0.92);backdrop-filter:blur(24px);border-radius:28px;padding:48px 44px;width:100%;max-width:400px;border:1px solid rgba(255,255,255,0.04);box-shadow:0 48px 96px rgba(0,0,0,0.8)}
        .brand{text-align:center;margin-bottom:36px}
        .brand h1{color:#fff;font-size:26px;font-weight:300;letter-spacing:6px}
        .brand h1 span{color:#6c5ce7;font-weight:700}
        .brand p{color:rgba(255,255,255,0.12);font-size:10px;letter-spacing:3px;margin-top:6px}
        .field{margin-bottom:18px}
        .field label{display:block;color:rgba(255,255,255,0.2);font-size:10px;text-transform:uppercase;letter-spacing:2px;margin-bottom:6px}
        .field input{width:100%;padding:14px 18px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:12px;color:#fff;font-size:15px;transition:0.3s;outline:none}
        .field input:focus{border-color:rgba(108,92,231,0.3);background:rgba(108,92,231,0.03)}
        .btn{width:100%;padding:16px;background:linear-gradient(135deg,#6c5ce7,#a855f7);border:none;border-radius:12px;color:#fff;font-size:14px;font-weight:600;letter-spacing:2px;cursor:pointer;transition:0.3s}
        .btn:hover{transform:translateY(-2px);box-shadow:0 12px 36px rgba(108,92,231,0.25)}
        .error{color:#ef4444;font-size:13px;text-align:center;margin-top:14px;padding:10px;background:rgba(239,68,68,0.04);border-radius:8px;border:1px solid rgba(239,68,68,0.06)}
        .footer{text-align:center;margin-top:24px;color:rgba(255,255,255,0.02);font-size:9px;letter-spacing:3px}
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">
            <h1>REACH <span>REACH</span></h1>
            <p>ADMINISTRATOR ACCESS</p>
        </div>
        <form method="POST">
            <div class="field"><label>Username</label><input type="text" name="username" placeholder="Enter username" required autocomplete="off"></div>
            <div class="field"><label>Password</label><input type="password" name="password" placeholder="Enter password" required></div>
            <button type="submit" class="btn">Authenticate</button>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
        </form>
        <div class="footer">SECURE</div>
    </div>
</body>
</html>"""

ADMIN_DASHBOARD = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REACH PANEL · Admin</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#08080e;font-family:'Segoe UI',system-ui,sans-serif;color:#fff;padding:24px;min-height:100vh}
        .container{max-width:1200px;margin:0 auto}
        .header{display:flex;justify-content:space-between;align-items:center;padding:20px 0;border-bottom:1px solid rgba(255,255,255,0.04);margin-bottom:32px}
        .header h1{font-size:22px;font-weight:300;letter-spacing:4px}
        .header h1 span{color:#6c5ce7;font-weight:700}
        .header a{color:rgba(255,255,255,0.2);text-decoration:none;padding:10px 22px;border:1px solid rgba(255,255,255,0.04);border-radius:10px;transition:0.3s;font-size:13px}
        .header a:hover{background:rgba(255,255,255,0.03)}
        .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
        .card{background:rgba(16,16,28,0.85);backdrop-filter:blur(12px);border-radius:18px;padding:24px;border:1px solid rgba(255,255,255,0.04)}
        .card h2{font-size:14px;font-weight:600;margin-bottom:18px;color:rgba(255,255,255,0.4);letter-spacing:2px}
        .card h2 i{color:#6c5ce7;margin-right:10px}
        .field{margin-bottom:14px}
        .field label{display:block;color:rgba(255,255,255,0.15);font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px}
        .field input{width:100%;padding:12px 16px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);border-radius:10px;color:#fff;font-size:14px;outline:none;transition:0.3s}
        .field input:focus{border-color:rgba(108,92,231,0.3)}
        .btn{padding:12px 24px;background:linear-gradient(135deg,#6c5ce7,#a855f7);border:none;border-radius:10px;color:#fff;font-size:12px;font-weight:600;letter-spacing:1px;cursor:pointer;transition:0.3s}
        .btn:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(108,92,231,0.2)}
        .btn-danger{background:linear-gradient(135deg,#ef4444,#dc2626)}
        .btn-sm{padding:6px 14px;font-size:10px}
        .table-wrap{overflow-x:auto;margin-top:8px}
        table{width:100%;border-collapse:collapse;font-size:12px}
        th{text-align:left;padding:10px 8px;color:rgba(255,255,255,0.15);font-weight:500;font-size:9px;text-transform:uppercase;letter-spacing:1.5px;border-bottom:1px solid rgba(255,255,255,0.03)}
        td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,0.02);color:rgba(255,255,255,0.5)}
        .badge{padding:2px 10px;border-radius:6px;font-size:10px;font-weight:600;background:rgba(108,92,231,0.08);color:#6c5ce7;font-family:monospace}
        .badge.active{background:rgba(52,211,153,0.08);color:#34d399}
        .badge.expired{background:rgba(239,68,68,0.08);color:#ef4444}
        .full{grid-column:1/-1}
        @media(max-width:768px){.grid{grid-template-columns:1fr}.header{flex-direction:column;gap:12px}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>REACH <span>REACH</span> · Administration</h1>
            <a href="/admin/logout"><i class="fas fa-sign-out-alt"></i> Exit</a>
        </div>
        <div class="grid">
            <div class="card">
                <h2><i class="fas fa-key"></i> Generate Key</h2>
                <div class="field"><label>Key Prefix</label><input type="text" id="keyPrefix" value="CRX-HACKS"></div>
                <div class="field"><label>IP Limit</label><input type="number" id="ipLimit" value="1" min="1"></div>
                <div class="field"><label>Validity (Days)</label><input type="number" id="keyDays" value="7" min="1"></div>
                <button class="btn" onclick="generateKey()"><i class="fas fa-plus"></i> Generate</button>
                <div id="generatedKey" style="margin-top:14px;font-family:monospace;color:#6c5ce7;font-size:16px;font-weight:600;"></div>
            </div>
            <div class="card">
                <h2><i class="fas fa-info-circle"></i> Statistics</h2>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px;">
                    <div style="background:rgba(255,255,255,0.01);padding:16px;border-radius:10px;border:1px solid rgba(255,255,255,0.02);">
                        <div style="color:rgba(255,255,255,0.1);font-size:9px;text-transform:uppercase;letter-spacing:1px;">Total Keys</div>
                        <div style="font-size:28px;font-weight:700;color:#6c5ce7;">{{ keys|length }}</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.01);padding:16px;border-radius:10px;border:1px solid rgba(255,255,255,0.02);">
                        <div style="color:rgba(255,255,255,0.1);font-size:9px;text-transform:uppercase;letter-spacing:1px;">Active IPs</div>
                        <div style="font-size:28px;font-weight:700;color:#34d399;">{{ ips|length }}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card full" style="margin-top:24px;">
            <h2><i class="fas fa-list"></i> Keys</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Key</th><th>Prefix</th><th>Limit</th><th>Used</th><th>Days</th><th>Created</th><th>Action</th></tr></thead>
                    <tbody>
                        {% for key, data in keys.items() %}
                        <tr><td><span class="badge">{{ key }}</span></td><td>{{ data.prefix }}</td><td>{{ data.limit }}</td><td>{{ data.used_ips|length }}</td><td>{{ data.days }}</td><td>{{ data.created[:10] }}</td><td><button class="btn btn-danger btn-sm" onclick="revokeKey('{{ key }}')">Revoke</button></td></tr>
                        {% else %}
                        <tr><td colspan="7" style="text-align:center;padding:30px;color:rgba(255,255,255,0.05);">No keys generated</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        <div class="card full" style="margin-top:24px;">
            <h2><i class="fas fa-users"></i> Registered IPs</h2>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>IP Address</th><th>Key</th><th>Expires</th><th>Status</th></tr></thead>
                    <tbody>
                        {% for ip, key in ips.items() %}
                        <tr><td>{{ ip }}</td><td><span class="badge">{{ key }}</span></td><td>{% if key_expiry[ip] %}{{ key_expiry[ip].strftime('%Y-%m-%d') }}{% else %}-{% endif %}</td><td><span class="badge active">Active</span></td></tr>
                        {% else %}
                        <tr><td colspan="4" style="text-align:center;padding:30px;color:rgba(255,255,255,0.05);">No IPs registered</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        function generateKey(){const prefix=document.getElementById('keyPrefix').value||'CRX-HACKS';const limit=parseInt(document.getElementById('ipLimit').value)||1;const days=parseInt(document.getElementById('keyDays').value)||7;fetch('/admin/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prefix,limit,days})}).then(r=>r.json()).then(d=>{document.getElementById('generatedKey').textContent='✓ '+d.key;setTimeout(()=>location.reload(),1200);});}
        function revokeKey(key){if(!confirm('Revoke '+key+'?'))return;fetch('/admin/revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})}).then(r=>r.json()).then(d=>{if(d.success)location.reload();});}
    </script>
</body>
</html>"""

LANDING_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REACH PANEL · Unlock</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#08080e;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;background-image:radial-gradient(ellipse at 50% 0%,rgba(108,92,231,0.05),transparent 60%)}
        .container{max-width:400px;width:100%;background:rgba(16,16,28,0.92);backdrop-filter:blur(32px);border-radius:28px;padding:44px 36px;border:1px solid rgba(255,255,255,0.04);box-shadow:0 48px 96px rgba(0,0,0,0.9)}
        .brand{text-align:center;margin-bottom:32px}
        .brand .icon{width:56px;height:56px;background:linear-gradient(135deg,#6c5ce7,#a855f7);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:24px;margin-bottom:12px}
        .brand h1{color:#fff;font-size:22px;font-weight:300;letter-spacing:4px}
        .brand h1 span{color:#6c5ce7;font-weight:700}
        .brand p{color:rgba(255,255,255,0.06);font-size:9px;letter-spacing:3px;margin-top:4px}
        .step-status{display:flex;justify-content:center;gap:30px;margin:10px 0 20px 0;font-size:11px;color:rgba(255,255,255,0.2)}
        .step-status .done{color:#34d399}
        .social-btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:14px;border:none;border-radius:12px;color:#fff;font-size:14px;font-weight:600;text-decoration:none;transition:0.3s;margin:6px 0}
        .social-btn.youtube{background:linear-gradient(135deg,#ff0000,#cc0000)}
        .social-btn.youtube:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(255,0,0,0.3)}
        .social-btn.telegram{background:linear-gradient(135deg,#0088cc,#006699)}
        .social-btn.telegram:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(0,136,204,0.3)}
        .note{text-align:center;color:rgba(255,255,255,0.1);font-size:10px;margin:8px 0 14px 0;letter-spacing:0.5px}
        .unlock-btn{width:100%;padding:16px;background:linear-gradient(135deg,#34d399,#22d3ee);border:none;border-radius:12px;color:#fff;font-size:16px;font-weight:700;letter-spacing:1px;cursor:pointer;transition:0.3s;margin-top:4px}
        .unlock-btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 8px 28px rgba(52,211,153,0.3)}
        .unlock-btn:disabled{opacity:0.3;cursor:not-allowed;transform:none}
        .footer{text-align:center;margin-top:24px;color:rgba(255,255,255,0.02);font-size:8px;letter-spacing:3px}
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">
            <div class="icon"><i class="fas fa-unlock-alt"></i></div>
            <h1>REACH <span>REACH</span></h1>
            <p>@CEO_UXDEMONOFC</p>
        </div>
        <div class="step-status">
            <span id="ytStatus"><i class="fab fa-youtube"></i> YouTube</span>
            <span id="tgStatus"><i class="fab fa-telegram"></i> Telegram</span>
        </div>
        <a href="https://youtube.com/@demon_xx_999?si=eDdR7AlwqLIL9YD9" target="_blank" class="social-btn youtube" onclick="markYouTube()">
            <i class="fab fa-youtube"></i> Subscribe to Continue
        </a>
        <a href="https://t.me/UX_DEMON_OFC" target="_blank" class="social-btn telegram" onclick="markTelegram()">
            <i class="fab fa-telegram-plane"></i> Join TG to Continue
        </a>
        <div class="note">Subscribe and Join TG to Continue.</div>
        <button class="unlock-btn" id="unlockBtn" disabled onclick="unlockProxy()">
            <i class="fas fa-arrow-right"></i> Tap to Continue
        </button>
        <div class="footer">SECURE</div>
    </div>
    <script>
        let ytClicked=false;let tgClicked=false;
        function markYouTube(){ytClicked=true;document.getElementById('ytStatus').className='done';document.getElementById('ytStatus').innerHTML='<i class="fab fa-youtube"></i> ✓ YouTube';checkUnlock();}
        function markTelegram(){tgClicked=true;document.getElementById('tgStatus').className='done';document.getElementById('tgStatus').innerHTML='<i class="fab fa-telegram"></i> ✓ Telegram';checkUnlock();}
        function checkUnlock(){if(ytClicked&&tgClicked){document.getElementById('unlockBtn').disabled=false;}}
        function unlockProxy(){if(!ytClicked||!tgClicked)return;fetch('/unlock',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success){window.location.href='/dashboard';}});}
    </script>
</body>
</html>"""

DASHBOARD_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REACH PANEL · Proxy</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:#08080e;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;background-image:radial-gradient(ellipse at 30% 20%,rgba(108,92,231,0.04),transparent 60%)}
        .dashboard{max-width:420px;width:100%;background:rgba(16,16,28,0.92);backdrop-filter:blur(32px);border-radius:28px;padding:28px 24px;border:1px solid rgba(255,255,255,0.04);box-shadow:0 48px 96px rgba(0,0,0,0.9)}
        .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
        .brand{display:flex;align-items:center;gap:12px}
        .brand-icon{width:40px;height:40px;background:linear-gradient(135deg,#6c5ce7,#a855f7);border-radius:12px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px}
        .brand-text{color:#fff;font-size:18px;font-weight:700;letter-spacing:-0.5px}
        .brand-text span{background:linear-gradient(135deg,#6c5ce7,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .status-badge{display:flex;align-items:center;gap:6px;padding:4px 14px;border-radius:12px;border:1px solid rgba(52,211,153,0.08);background:rgba(52,211,153,0.04)}
        .status-dot{width:6px;height:6px;border-radius:50%;background:#34d399;animation:pulse 2s infinite}
        .status-text{color:#34d399;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.2}}
        .ip-bar{background:rgba(255,255,255,0.02);border-radius:14px;padding:10px 14px;margin:10px 0 14px 0;display:flex;align-items:center;gap:10px;border:1px solid rgba(255,255,255,0.03)}
        .ip-bar i{color:#6c5ce7;font-size:12px;opacity:0.4}
        .ip-bar .ip{color:rgba(255,255,255,0.3);font-size:12px;font-family:monospace;flex:1}
        .ip-bar .tag{font-size:8px;padding:2px 12px;border-radius:6px;background:rgba(108,92,231,0.08);color:#6c5ce7;font-weight:600;letter-spacing:0.5px}
        .section{color:rgba(255,255,255,0.08);font-size:8px;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:16px 0 8px 0}
        .grid{display:grid;grid-template-columns:1fr 1fr;gap:4px}
        .item{background:rgba(255,255,255,0.01);border:1px solid rgba(255,255,255,0.03);border-radius:12px;padding:10px 12px;display:flex;align-items:center;gap:10px;cursor:pointer;transition:0.3s}
        .item:hover{background:rgba(255,255,255,0.02)}
        .item .ico{font-size:14px;width:24px;text-align:center;opacity:0.4}
        .item .info{flex:1}
        .item .name{color:rgba(255,255,255,0.5);font-size:11px;font-weight:600}
        .item .desc{color:rgba(255,255,255,0.05);font-size:7px}
        .sw{width:32px;height:17px;background:rgba(255,255,255,0.03);border-radius:10px;cursor:pointer;position:relative;transition:0.3s;flex-shrink:0;border:1px solid rgba(255,255,255,0.02)}
        .sw .th{width:13px;height:13px;background:rgba(255,255,255,0.05);border-radius:50%;position:absolute;top:1px;left:1px;transition:0.3s}
        .sw.on{background:linear-gradient(135deg,#6c5ce7,#a855f7);border-color:transparent}
        .sw.on .th{left:16px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.3)}
        .note-box{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.03);border-radius:12px;padding:12px 14px;margin-top:12px;color:rgba(255,255,255,0.25);font-size:11px;text-align:center;line-height:1.5}
        .note-box a{color:#6c5ce7;text-decoration:none;word-break:break-all}
        .note-box a:hover{text-decoration:underline}
        .footer{text-align:center;margin-top:18px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.02)}
        .footer-text{color:rgba(255,255,255,0.02);font-size:8px;letter-spacing:3px;font-weight:700}
        .footer-text span{background:linear-gradient(135deg,#6c5ce7,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .social-footer{display:flex;gap:12px;justify-content:center;margin-top:8px}
        .social-footer a{color:rgba(255,255,255,0.05);font-size:20px;transition:0.3s}
        .social-footer a:hover{color:rgba(255,255,255,0.2)}
        .toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:rgba(16,16,28,0.96);border:1px solid rgba(108,92,231,0.06);border-radius:12px;padding:10px 20px;color:#fff;font-size:12px;font-weight:500;backdrop-filter:blur(20px);opacity:0;transition:opacity 0.3s;pointer-events:none;max-width:90%;z-index:999}
        .toast.show{opacity:1}
        @media(max-width:380px){.grid{grid-template-columns:1fr}}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <div class="brand">
                <div class="brand-icon"><i class="fas fa-satellite-dish"></i></div>
                <div class="brand-text">REACH <span>REACH</span></div>
            </div>
            <div class="status-badge">
                <div class="status-dot"></div>
                <div class="status-text">Live</div>
            </div>
        </div>
        <div class="ip-bar">
            <i class="fas fa-network-wired"></i>
            <span class="ip" id="ipDisplay">Loading...</span>
            <span class="tag"><i class="fas fa-check-circle"></i> Unlocked</span>
        </div>
        
        <div class="section"><i class="fas fa-crosshairs"></i> Aim Assist</div>
        <div class="grid">
            <div class="item" onclick="toggle('hs_neck')">
                <div class="ico" style="color:#6c5ce7;"><i class="fas fa-crosshairs"></i></div>
                <div class="info"><div class="name">HS NECK</div><div class="desc">Headshot</div></div>
                <div class="sw" id="sw_hs_neck"><div class="th"></div></div>
            </div>
            <div class="item" onclick="toggle('hs_chest')">
                <div class="ico" style="color:#a78bfa;"><i class="fas fa-bullseye"></i></div>
                <div class="info"><div class="name">HS CHEST</div><div class="desc">Chest</div></div>
                <div class="sw" id="sw_hs_chest"><div class="th"></div></div>
            </div>
        </div>

        <div class="section"><i class="fas fa-sliders-h"></i> Configuration</div>
        <div class="grid">
            <div class="item" onclick="toggle('backjump_v1')">
                <div class="ico" style="color:#f87171;"><i class="fas fa-arrow-up"></i></div>
                <div class="info"><div class="name">BACKJUMP</div><div class="desc">Jump</div></div>
                <div class="sw" id="sw_backjump_v1"><div class="th"></div></div>
            </div>
            <div class="item" onclick="toggle('high_sensi')">
                <div class="ico" style="color:#f472b6;"><i class="fas fa-sliders-h"></i></div>
                <div class="info"><div class="name">HIGH SENSI</div><div class="desc">Sensitivity</div></div>
                <div class="sw" id="sw_high_sensi"><div class="th"></div></div>
            </div>
        </div>

        <div class="section"><i class="fas fa-running"></i> Movement</div>
        <div class="grid">
            <div class="item" onclick="toggle('zig_zag_move')">
                <div class="ico" style="color:#34d399;"><i class="fas fa-random"></i></div>
                <div class="info"><div class="name">ZIG ZAG</div><div class="desc">Movement</div></div>
                <div class="sw" id="sw_zig_zag_move"><div class="th"></div></div>
            </div>
        </div>

        <div class="note-box">
            <i class="fas fa-info-circle" style="color:#6c5ce7;margin-right:6px;"></i>
            If game is not opening copy and paste/open the above link on chrome<br>
            <a href="https://reachpanel-uxdemonofc.onrender.com" target="_blank">https://reachpanel-uxdemonofc.onrender.com</a>
        </div>

        <div class="social-footer">
            <a href="https://youtube.com/@demon_xx_999?si=eDdR7AlwqLIL9YD9" target="_blank"><i class="fab fa-youtube"></i></a>
            <a href="https://t.me/" target="_blank"><i class="fab fa-telegram"></i></a>
        </div>
        
        <div class="footer"><div class="footer-text"><span>REACH PANEL</span> · PROXY</div></div>
    </div>
    <div class="toast" id="toast"></div>
    <script>
        function toast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.className = 'toast show';
            clearTimeout(t._h);
            t._h = setTimeout(() => t.className = 'toast', 1800);
        }
        
        fetch('/api/ip/check').then(r=>r.json()).then(d=>{
            document.getElementById('ipDisplay').textContent = d.ip || 'Unknown';
        });
        
        // Load current config
        fetch('/api/status').then(r=>r.json()).then(d=>{
            const c = d.config;
            document.getElementById('sw_hs_neck').className = 'sw' + (c.HS_NECK ? ' on' : '');
            document.getElementById('sw_hs_chest').className = 'sw' + (c.HS_CHEST ? ' on' : '');
            document.getElementById('sw_backjump_v1').className = 'sw' + (c.BACKJUMPV1 ? ' on' : '');
            document.getElementById('sw_high_sensi').className = 'sw' + (c.HIGH_SENSI ? ' on' : '');
            document.getElementById('sw_zig_zag_move').className = 'sw' + (c.ZIG_ZAG_MOVE ? ' on' : '');
        });
        
        function toggle(feature) {
            const el = document.getElementById('sw_' + feature);
            const on = el.classList.contains('on');
            const val = !on;
            
            // Optimistically update UI
            el.className = 'sw' + (val ? ' on' : '');
            
            fetch('/api/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({feature: feature, value: val})
            }).then(r=>r.json()).then(d=>{
                if(d.success) {
                    toast(feature.toUpperCase().replace('_', ' ') + ' ' + (val ? 'ON' : 'OFF'));
                } else {
                    // Revert on error
                    el.className = 'sw' + (!val ? ' on' : '');
                    toast('Error toggling ' + feature);
                }
            }).catch(err => {
                // Revert on error
                el.className = 'sw' + (!val ? ' on' : '');
                toast('Error toggling ' + feature);
            });
        }
    </script>
</body>
</html>"""

# ==================== MAIN ====================
def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text.strip()
    except:
        try:
            response = requests.get('https://icanhazip.com', timeout=5)
            return response.text.strip()
        except:
            return "Unable to get public IP"

if __name__ == "__main__":
    load_data()
    port = int(os.environ.get('PORT', 10000))
    
    print("\n" + "="*50)
    print("  REACH PANEL PROXY INTERCEPTOR")
    print("="*50)
    print(f"  Server Port: {port}")
    print(f"  Public URL: https://reachpanel-uxdemonofc.onrender.com")
    print(f"  Admin     : /Po7eO")
    print(f"  Status    : Running")
    print("="*50 + "\n")
    
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
