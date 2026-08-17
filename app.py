import os, json, gzip, hashlib, base64, requests, threading, time
from flask import Flask, request, Response, redirect, session, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret'

DATA = {"maintenance": False, "ips": set()}
VER_URL = "https://version.ggwhitehawk.com/live/ver.php"
CDN_URL = "https://dl.bs.freefiremobile.com/live/ABHotUpdates/"
PASS = "Aditya@7457$aditya*7457"
TG = "https://t.me/+aOpyPp0gZyg1YmU1"
DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', 8080))

def ping():
    while True:
        try: requests.get(f"http://localhost:{PORT}/")
        except: pass
        time.sleep(180)
threading.Thread(target=ping, daemon=True).start()

MODS = {
    "CleanFFAntiState": {"var_type": "bool", "var_value": "true"},
    "FFAntihackDefenceLevel": {"var_type": "string", "var_value": "0"},
    "EnablePlatformCheck": {"var_type": "bool", "var_value": "false"},
    "NeedProcessAH": {"var_type": "bool", "var_value": "true"},
}

def b64(data): return base64.b64encode(hashlib.sha1(data).digest()).decode()
def ip(): return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def cfg(path):
    c = {"neck": False, "chest": False, "idx": False}
    p = path.lower().split('/')
    for i in range(len(p)-1):
        if p[i]=='hs_neck' and p[i+1]=='true': c["neck"]=True
        if p[i]=='hs_chest' and p[i+1]=='true': c["chest"]=True
        if p[i]=='asset_indexer' and p[i+1]=='true': c["idx"]=True
    return c

def patch(text, c):
    if not c["neck"] and not c["chest"]: return text
    lines, out = text.splitlines(), []
    for l in lines:
        if l.startswith("cache_res,"):
            f = None
            if c["neck"] and os.path.exists(os.path.join(DIR, "cache_res")): f="cache_res"
            elif c["chest"] and os.path.exists(os.path.join(DIR, "cache_res2")): f="cache_res2"
            if f:
                try:
                    with open(os.path.join(DIR, f), "rb") as fp: gz=fp.read()
                    raw=gzip.decompress(gz)
                    out.append(f"cache_res,{b64(raw)},{len(raw)},0,{b64(gz)},{len(gz)},True,0")
                    continue
                except: pass
        out.append(l)
    return "\n".join(out)

def mod_ver(text, c):
    try:
        d = json.loads(text)
        if c["neck"] or c["chest"] or c["idx"]:
            cdn = f"https://{request.host}/cdn/live/ABHotUpdates/"
            d["cdn_url"]=cdn; d["backup_cdn_url"]=cdn; d["abhotupdate_cdn_url"]=cdn
        gv = d.get("gamevar", "")
        for k,v in MODS.items(): gv += f"\n{k},{k},{v['var_type']},{v['var_value']},,"
        d["gamevar"] = gv
        return json.dumps(d)
    except: return text

@app.route('/admin', methods=['GET','POST'])
def login():
    if 'ok' in session: return redirect('/dash')
    if request.method=='POST' and request.form.get('p')==PASS:
        session['ok']=True; return redirect('/dash')
    return '<html><body style="background:#111;color:#0ff;text-align:center;margin-top:20%"><h2>ADMIN</h2><form method="post"><input name="p" type="password" style="padding:10px;margin:10px"><br><button style="padding:10px">GO</button></form></body></html>'

@app.route('/dash')
def dash():
    if 'ok' not in session: return redirect('/admin')
    m = "on" if DATA["maintenance"] else ""
    return f'''<html><head><script src="https://cdnjs.cloudflare.com/ajax/libs/fetch/3.0.0/fetch.min.js"></script></head>
    <body style="background:#111;color:#0ff;font-family:monospace;padding:20px">
    <h2>DEVICES: <span id="c">{len(DATA["ips"])}</span></h2>
    <h3>Maintenance</h3>
    <button id="m" onclick="toggle()" style="padding:10px;background:{'red' if DATA['maintenance'] else 'green'};color:#fff;border:none;cursor:pointer">{'ON' if DATA['maintenance'] else 'OFF'}</button>
    <br><br><a href="{TG}" style="color:#0ff">TELEGRAM</a> | <a href="/out" style="color:red">LOGOUT</a>
    <script>
    function toggle(){{fetch('/tm',{{method:'POST'}}).then(r=>r.json()).then(d=>{{if(d.s)location.reload();}})}}
    fetch('/st').then(r=>r.json()).then(d=>{{document.getElementById('c').innerText=d.n;}});
    </script></body></html>'''

@app.route('/st')
def st():
    if 'ok' not in session: return jsonify({"error":1}), 401
    return jsonify({"n": len(DATA["ips"])})

@app.route('/tm', methods=['POST'])
def tm():
    if 'ok' not in session: return jsonify({"s":0}), 401
    DATA["maintenance"] = not DATA["maintenance"]
    return jsonify({"s":1})

@app.route('/out')
def out():
    session.pop('ok', None); return redirect('/admin')

@app.route('/')
def home(): return "Live"

@app.route('/<path:p>')
def proxy(p):
    if p.startswith('admin') or p=='dash' or p=='st' or p=='tm' or p=='out': return Response("", 404)
    
    DATA["ips"].add(ip())
    
    if DATA["maintenance"]:
        return Response(json.dumps({"m":"1","u":TG}), 503, mimetype='application/json')

    if 'ver.php' in p:
        c = cfg(p)
        h = {"User-Agent":"Garena/1.0 (Android; OB54)","Accept":"application/json","X-Device-Model":"SM-G998B","Connection":"keep-alive"}
        try:
            r = requests.get(VER_URL, headers=h, timeout=15)
            res = Response(mod_ver(r.text, c), 200, mimetype='application/json')
            res.headers['Access-Control-Allow-Origin']='*'
            return res
        except Exception as e: return Response(str(e), 502)

    if 'cdn/live/abhotupdates/' in p.lower():
        fp = p.lower().split('cdn/live/abhotupdates/')[-1]
        c = cfg(p)
        if "assetindexer" in fp and c["idx"] and os.path.exists(os.path.join(DIR, "cache_res3")):
            return Response(open(os.path.join(DIR, "cache_res3"),"rb").read(), mimetype='application/octet-stream')
        if "cache_res" in fp:
            f = None
            if c["neck"] and os.path.exists(os.path.join(DIR, "cache_res")): f=os.path.join(DIR, "cache_res")
            elif c["chest"] and os.path.exists(os.path.join(DIR, "cache_res2")): f=os.path.join(DIR, "cache_res2")
            if f: return Response(open(f,"rb").read(), mimetype='application/octet-stream')
        if "fileinfo" in fp:
            try:
                r = requests.get(CDN_URL+fp, timeout=30)
                return Response(patch(r.text, c).encode(), mimetype='application/octet-stream')
            except: return Response("E", 502)
        try:
            r = requests.get(CDN_URL+fp, timeout=30)
            return Response(r.content, r.status_code, mimetype=r.headers.get('content-type','application/octet-stream'))
        except: return Response("E", 502)

    return Response("", 404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
