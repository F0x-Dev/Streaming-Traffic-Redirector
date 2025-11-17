from fastapi import FastAPI, Request, Form, Depends, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import sqlite3, os, threading, subprocess, signal, time, asyncio

JWT_ALGORITHM = 'HS256'
DB_PATH = 'database.db'
FFMPEG_SCRIPT = '/app/scripts/start_transcode.sh'

app = FastAPI(title='Stream Orchestrator V2')
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
jwt_secret = os.getenv('JWT_SECRET', 'replace_me')

# Prometheus metrics
streams_started = Counter('streams_started_total', 'Total streams started')

# Simple websocket manager
class ConnectionManager:
    def __init__(self):
        self.active = set()
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
    async def broadcast(self, msg: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(msg)
            except Exception:
                pass

manager = ConnectionManager()

def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_admin_if_missing(user, password):
    conn = db_conn()
    conn.execute('CREATE TABLE IF NOT EXISTS streams (id INTEGER PRIMARY KEY, key TEXT UNIQUE, status TEXT, pid INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)')
    cur = conn.execute('SELECT id FROM admins WHERE username=?', (user,)).fetchone()
    if not cur:
        ph = pwd_context.hash(password)
        conn.execute('INSERT INTO admins (username, password_hash) VALUES (?,?)', (user, ph))
        conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = db_conn()
    row = conn.execute('SELECT password_hash FROM admins WHERE username=?', (username,)).fetchone()
    conn.close()
    if not row:
        return False
    return pwd_context.verify(password, row['password_hash'])

def create_access_token(data: dict, expires_sec: int = 3600):
    to_encode = data.copy()
    to_encode.update({'exp': time.time() + expires_sec})
    return jwt.encode(to_encode, jwt_secret, algorithm=JWT_ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

def start_transcode(stream_key):
    cmd = ['/bin/sh', FFMPEG_SCRIPT, stream_key]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    conn = db_conn()
    conn.execute('UPDATE streams SET pid=? WHERE key=?', (proc.pid, stream_key))
    conn.commit()
    conn.close()
    streams_started.inc()
    asyncio.create_task(manager.broadcast({'event':'started','stream':stream_key}))

@app.on_event('startup')
def startup():
    admin_user = os.getenv('ADMIN_USER', 'admin')
    admin_pass = os.getenv('ADMIN_PASSWORD', 'changeme')
    create_admin_if_missing(admin_user, admin_pass)

@app.post('/login')
async def login(form: Request):
    data = await form.form()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        raise HTTPException(status_code=400, detail='Missing credentials')
    if not authenticate_user(username, password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token({'sub': username})
    return JSONResponse({'access_token': token})

@app.post('/on_publish')
async def on_publish(request: Request):
    form = await request.form()
    stream_key = form.get('name')
    if not stream_key:
        return {'status':'error','message':'missing name'}
    conn = db_conn()
    cur = conn.execute('SELECT key FROM streams WHERE key=?', (stream_key,)).fetchone()
    if not cur:
        conn.close()
        return {'status':'error','message':'Invalid stream key'}
    conn.execute("UPDATE streams SET status='live' WHERE key=?", (stream_key,))
    conn.commit()
    conn.close()
    threading.Thread(target=start_transcode, args=(stream_key,), daemon=True).start()
    return {'status':'ok'}

@app.post('/on_done')
async def on_done(request: Request):
    form = await request.form()
    stream_key = form.get('name')
    if not stream_key:
        return {'status':'error','message':'missing name'}
    conn = db_conn()
    row = conn.execute('SELECT pid FROM streams WHERE key=?', (stream_key,)).fetchone()
    if row and row['pid']:
        try:
            os.kill(row['pid'], signal.SIGTERM)
        except Exception:
            pass
    conn.execute("UPDATE streams SET status='offline', pid=NULL WHERE key=?", (stream_key,))
    conn.commit()
    conn.close()
    asyncio.create_task(manager.broadcast({'event':'stopped','stream':stream_key}))
    return {'status':'ok'}

@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    conn = db_conn()
    rows = conn.execute('SELECT key, status FROM streams ORDER BY id').fetchall()
    conn.close()
    return templates.TemplateResponse('dashboard.html', {'request': request, 'streams': rows})

@app.post('/add_stream')
def add_stream(key: str = Form(...), token: str = Form(None)):
    if not token:
        raise HTTPException(status_code=401, detail='Missing token')
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail='Invalid token')
    conn = db_conn()
    conn.execute('INSERT OR IGNORE INTO streams (key, status) VALUES (?,?)', (key, 'offline'))
    conn.commit()
    conn.close()
    return RedirectResponse('/', status_code=303)

@app.get('/metrics')
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
