from flask import Flask, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import random, json, os, hashlib, urllib.parse, math, string
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
app.secret_key = 'mochaina_final_boss_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mochaina_pwa.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_ID", "10000100")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_KEY", "46f0cd694581a")
PAYFAST_PASSPHRASE = os.getenv("PAYFAST_PP", "")
PAYFAST_URL = "https://www.payfast.co.za/eng/process"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    balance = db.Column(db.Float, default=5.0)
    referral_code = db.Column(db.String(20), unique=True)
    referred_by = db.Column(db.String(20), nullable=True)
    daily_last = db.Column(db.String(20), nullable=True)
    daily_streak = db.Column(db.Integer, default=0)
    total_won = db.Column(db.Float, default=0.0)
class Draw(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    numbers=db.Column(db.String(100)); wing=db.Column(db.Integer); date=db.Column(db.String(30))
class Ticket(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer); username=db.Column(db.String(50))
    numbers=db.Column(db.String(100)); wing=db.Column(db.Integer); bet=db.Column(db.Integer)
class Payment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer); username=db.Column(db.String(50))
    amount=db.Column(db.Integer); ref=db.Column(db.String(100)); status=db.Column(db.String(20), default="Pending"); method=db.Column(db.String(20))
class Voucher(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    code=db.Column(db.String(100), unique=True); amount=db.Column(db.Integer); is_used=db.Column(db.Boolean, default=False); used_by=db.Column(db.String(50))
class WinLog(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(50)); game=db.Column(db.String(20)); amount=db.Column(db.Float); date=db.Column(db.String(30))

def gen_code(name):
    base = ''.join([c for c in name.upper() if c.isalnum()])[:3]
    return f"{base}{random.randint(1000,9999)}{random.choice(string.ascii_uppercase)}"

def safe_init():
    with app.app_context():
        db.create_all()
        try:
            cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
            if "referral_code" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN referral_code VARCHAR(20)"))
            if "referred_by" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN referred_by VARCHAR(20)"))
            if "daily_last" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN daily_last VARCHAR(20)"))
            if "daily_streak" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN daily_streak INTEGER DEFAULT 0"))
            if "total_won" not in cols: db.session.execute(text("ALTER TABLE user ADD COLUMN total_won FLOAT DEFAULT 0"))
            db.session.commit()
        except: pass
        try:
            if not os.path.exists("static"): os.makedirs("static")
            if not os.path.exists("static/manifest.json"):
                with open("static/manifest.json","w") as f: json.dump({"name":"Mochaina Lotto","short_name":"Mochaina","start_url":"/","display":"standalone","background_color":"#0a0a0a","theme_color":"#facc15"}, f)
            if not os.path.exists("static/sw.js"):
                with open("static/sw.js","w") as f: f.write("self.addEventListener('fetch', e=>{});")
            if not os.path.exists("jackpot.json"):
                with open("jackpot.json","w") as f: json.dump({"amount":500000.0}, f)
            if Voucher.query.count()==0:
                for i in range(1,6): db.session.add(Voucher(code=f"MOCHA-10-TEST0{i}", amount=10))
                db.session.commit()
            for u in User.query.all():
                if not u.referral_code: u.referral_code = gen_code(u.username)+str(u.id)
            db.session.commit()
        except: pass
safe_init()

def get_jackpot():
    try:
        with open("jackpot.json","r") as jf: return float(json.load(jf).get("amount",500000.0))
    except: return 500000.0
def save_jackpot(a):
    try:
        with open("jackpot.json.tmp","w") as jf: json.dump({"amount":float(a)}, jf)
        os.replace("jackpot.json.tmp", "jackpot.json")
    except: pass
def get_next_draw_time():
    now=datetime.now()
    d1=now.replace(hour=12,minute=0,second=0,microsecond=0)
    d2=now.replace(hour=17,minute=0,second=0,microsecond=0)
    if now<d1: return d1
    elif now<d2: return d2
    else: return (now + timedelta(days=1)).replace(hour=12,minute=0,second=0,microsecond=0)
def next_draw_str():
    try:
        nxt=get_next_draw_time()
        total=int((nxt-datetime.now()).total_seconds())
        if total<0: total=0
        return f"{total//3600:02}:{(total%3600)//60:02}:{total%60:02}"
    except: return "12:00:00"
def get_next_draw_timestamp():
    try: return int(get_next_draw_time().timestamp()*1000)
    except: return int((datetime.now()+timedelta(hours=1)).timestamp()*1000)
def auto_draw_if_due():
    try:
        last_file="last_draw.txt"; now=datetime.now(); last=None
        if os.path.exists(last_file):
            with open(last_file,"r") as f: last=datetime.fromisoformat(f.read().strip())
        should_draw=False
        if last:
            today_12=now.replace(hour=12,minute=1,second=0,microsecond=0)
            today_17=now.replace(hour=17,minute=1,second=0,microsecond=0)
            if last < today_12 <= now: should_draw=True
            if last < today_17 <= now: should_draw=True
        if should_draw:
            win=sorted(random.sample(range(1,37),4)); wing=random.randint(1,4)
            with app.app_context():
                d=Draw(numbers=",".join(map(str,win)), wing=wing, date=now.strftime("%Y-%m-%d %H:%M")); db.session.add(d); db.session.commit()
                db.session.query(Ticket).delete(); db.session.commit()
            with open(last_file,"w") as f: f.write(now.isoformat())
        else:
            if not os.path.exists(last_file):
                with open(last_file,"w") as f: f.write(now.isoformat())
    except: pass

# REAL GOLD STAR SVG - not emoji
GOLD_STAR = """<svg width="26" height="26" viewBox="0 0 24 24" style="filter:drop-shadow(0 0 6px #facc15aa)"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#fef08a"/><stop offset="20%" stop-color="#facc15"/><stop offset="50%" stop-color="#eab308"/><stop offset="80%" stop-color="#facc15"/><stop offset="100%" stop-color="#fef9c3"/></linearGradient></defs><path d="M12 2L13.9 8.5H20.6L15.1 12.5L17 19L12 14.7L7 19L8.9 12.5L3.4 8.5H10.1L12 2Z" fill="url(#g)" stroke="#fde047" stroke-width="0.5" stroke-linejoin="round"/></svg>"""

SA_FLAG = """<span style="display:inline-flex;align-items:center;gap:4px;background:#111;border:1px solid #facc1540;padding:4px 10px;border-radius:20px;font-size:10px;font-weight:900;color:#facc15">🇿🇦 SA's #1 LIVE LOTTO</span>"""

STYLE = f"""<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="manifest" href="/static/manifest.json"><meta name="theme-color" content="#facc15"><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@800;900&display=swap" rel="stylesheet"><script>if('serviceWorker' in navigator){{navigator.serviceWorker.register('/static/sw.js')}}</script><style>
*{{box-sizing:border-box}}
body{{background:#080808;color:white;font-family:'Outfit',Arial;margin:0;min-height:100vh}}
.phone{{max-width:430px;margin:0 auto;background:#0a0a0a;min-height:100vh;border-left:1px solid #1a1a1a;border-right:1px solid #1a1a1a}}
.top{{padding:12px 14px;background:#0a0a0a;border-bottom:1px solid #1a1a1a;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:nowrap}}
.brand{{font-weight:900;font-size:16px;color:white;white-space:nowrap;letter-spacing:0.3px;flex-shrink:0;display:flex;align-items:center;gap:6px}}
.jack{{background:linear-gradient(90deg,#facc15,#fbbf24);color:#000;font-weight:900;padding:11px 12px;margin:10px 14px;border-radius:6px;font-size:12px;text-align:center;clip-path:polygon(0 0,100% 0,98% 50%,100% 100%,0 100%,2% 50%)}}
.form{{padding:14px 16px}}
.lab{{font-size:11px;font-weight:800;color:#e5e7eb;text-align:left;margin:10px 0 3px 2px}}
.in{{width:100%;background:#1f1f1f;border:1.5px solid #facc15;border-radius:6px;padding:12px 12px;color:white;font-weight:700;font-size:13px;outline:none}}
.in::placeholder{{color:#9ca3af}}
.in:focus{{border-color:#fde047;background:#252525}}
.btn-gold{{background:linear-gradient(90deg,#facc15,#fbbf24);color:#000;font-weight:900;padding:13px;border-radius:6px;width:100%;border:none;font-size:13px;margin-top:12px;cursor:pointer}}
.btn-dark{{background:#1f1f1f;border:1px solid #2a2a2a;color:white;padding:12px;border-radius:6px;width:100%;margin-top:8px;font-weight:800;font-size:12px;cursor:pointer}}
.link{{font-size:11px;color:#9ca3af;margin-top:10px}}
.link a{{color:#facc15;font-weight:800}}
.games{{border-top:1px solid #1f1f1f;margin-top:14px;padding-top:10px}}
.gtitle{{color:#facc15;font-weight:900;font-size:11px;margin-bottom:8px;letter-spacing:0.5px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.gbox{{background:linear-gradient(135deg,#facc15,#f59e0b);border-radius:10px;padding:10px;color:#000;text-align:left}}
.gbox2{{background:#111;border:1.5px solid #facc15;border-radius:10px;padding:10px;color:#facc15;text-align:left}}
.gbox b,.gbox2 b{{font-size:11px;display:block}}
.gbox small,.gbox2 small{{font-size:9px;font-weight:700}}
.tabs{{display:flex;gap:6px;margin:10px 0}}.tab{{flex:1;padding:8px 2px;background:#1f1f1f;border-radius:8px;cursor:pointer;font-weight:800;font-size:10px;color:#9ca3af;border:1px solid #2a2a2a;text-align:center}}.tab.active{{background:#facc15;color:#000;border-color:#facc15}}
.tabcontent{{border:1px solid #2a2a2a;padding:10px;border-radius:10px;background:#111}}
.card-white{{background:white;color:#0f172a;border-radius:16px;padding:16px;margin:12px 14px}}
.jackpot{{font-size:20px;font-weight:900;color:#facc15;background:#111;padding:8px 14px;border-radius:10px;border:2px solid #facc15;display:inline-block;margin:6px 0}}
.timer{{background:#111;color:#facc15;padding:6px 10px;border-radius:8px;font-weight:900;font-family:monospace;border:1px solid #facc1533;display:inline-block;font-size:12px}}
.numgrid{{display:grid;grid-template-columns:repeat(6,1fr);gap:5px;margin:10px 0}}.num-btn{{padding:10px 2px;background:#1f1f1f;border:1.5px solid #2a2a2a;border-radius:8px;color:white;font-weight:800;font-size:12px}}.num-btn.selected{{background:#facc15;color:#000;border-color:#facc15}}
.wing-btn{{padding:9px 10px;background:#1f1f1f;border:1.5px solid #2a2a2a;border-radius:8px;margin:3px;color:white;font-weight:900;font-size:11px}}.wing-btn.selected{{background:#facc15;color:#000}}
.leader-row{{display:flex;justify-content:space-between;padding:9px 10px;border-radius:8px;margin:5px 0;background:#f8fafc;border:1px solid #e2e8f0;color:#000;font-weight:800;font-size:11px}}
.live-ticker{{background:#111;color:#facc15;padding:8px 0;overflow:hidden;white-space:nowrap;margin:8px 14px;border-radius:8px;border:1px solid #facc1522;font-size:10px;font-weight:800}}.live-ticker span{{display:inline-block;animation:marq 28s linear infinite}}
@keyframes marq{{0%{{transform:translateX(100%)}}100%{{transform:translateX(-100%)}}}}
</style>
<script>
let sel=[];let w=null;
function toggle(n,el){{if(sel.includes(n)){{sel=sel.filter(x=>x!=n);el.classList.remove('selected')}}else{{if(sel.length<4){{sel.push(n);el.classList.add('selected')}}}}document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}}
function pickWing(n,el){{w=n;document.querySelectorAll('.wing-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');document.getElementById('yourW').innerText='Wing: W'+n;document.getElementById('wing_input').value=n;}}
function autoPick(){{sel=[];document.querySelectorAll('.num-btn').forEach(b=>b.classList.remove('selected'));let nums=[];while(nums.length<4){{let r=Math.floor(Math.random()*36)+1;if(!nums.includes(r))nums.push(r)}}nums.forEach(n=>{{sel.push(n);document.getElementById('btn'+n).classList.add('selected')}});let rw=Math.floor(Math.random()*4)+1;pickWing(rw,document.getElementById('wbtn'+rw));document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}}
function showTab(t){{document.querySelectorAll('.tabcontent').forEach(c=>c.style.display='none');document.getElementById(t).style.display='block';document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');}}
function startLiveCountdown(targetMs,elementId){{function update(){{let now=new Date().getTime();let diff=targetMs-now;if(diff<=0){{let el=document.getElementById(elementId);if(el)el.innerText="00:00:00";setTimeout(()=>{{location.reload();}},2000);return;}}let h=Math.floor(diff/1000/3600);let m=Math.floor((diff/1000%3600)/60);let s=Math.floor(diff/1000%60);let el=document.getElementById(elementId);if(el)el.innerText=String(h).padStart(2,'0')+":"+String(m).padStart(2,'0')+":"+String(s).padStart(2,'0');}}setInterval(update,1000);update();}}
</script>"""

def wrap(html): return f"<div class=phone>{html}</div>"

def top_bar(balance=None):
    bal_html = f'<span style="background:#111;border:1px solid #facc1540;padding:5px 10px;border-radius:20px;font-size:11px;font-weight:900;color:#facc15">💰 R{balance:.0f}</span>' if balance is not None else SA_FLAG
    return f'<div class=top><div class=brand>{GOLD_STAR} Mochaina Lotto</div><div>{bal_html}</div></div>'

@app.route('/')
def home():
    if 'uid' in session: return redirect('/menu')
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        try:
            u=request.form['username']; p=request.form['password']
            user=User.query.filter_by(username=u).first()
            if user and (check_password_hash(user.password, p) or user.password==p):
                if user.password==p:
                    user.password=generate_password_hash(p); db.session.commit()
                session['uid']=user.id; session['uname']=u; return redirect('/menu')
        except: pass
        return STYLE+wrap(f"""{top_bar()}<div class=form><p style=color:#ef4444;font-weight:800>❌ Wrong login</p><button class=btn-dark onclick="location.href='/login'">Back</button></div>""")
    return STYLE+wrap(f"""
{top_bar()}
<div style=text-align:center;padding:8px 14px 0><h1 style=color:#facc15;font-size:28px;font-weight:900;margin:10px 0 2px>Welcome Back</h1><p style=color:#9ca3af;font-size:11px;margin:0 0 10px>Login to continue and play</p></div>
<div class=jack>🏆 JACKPOT R5,000,000 • Tonight 21:00</div>
<div class=form>
<form method='post'>
<div class=lab>Username</div><input class=in name='username' placeholder='e.g. Thabo Mthembu' required>
<div class=lab>Password</div><input class=in name='password' type='password' placeholder='••••••••' required>
<button class=btn-gold>🔓 LOGIN & WIN</button>
</form>
<button class=btn-dark onclick="location.href='/register'">✨ Register R5 FREE</button>
</div>
""")

@app.route('/register', methods=['GET','POST'])
def register():
    ref = request.args.get('ref')
    if ref: session['ref_code'] = ref.strip().upper()
    if request.method=='POST':
        try:
            full_name=request.form.get('full_name','').strip()
            p=request.form.get('password',''); p2=request.form.get('confirm_password',''); id_num=request.form.get('id_number','')
            if id_num and (len(id_num)!=13 or not id_num.isdigit()):
                return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444>❌ ID must be 13 digits</p><button class=btn-dark onclick=\"location.href='/register'\">Back</button></div>")
            if p2 and p!=p2:
                return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444>❌ Passwords don't match</p><button class=btn-dark onclick=\"location.href='/register'\">Back</button></div>")
            if len(p)<4:
                return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444>❌ Password min 4</p><button class=btn-dark onclick=\"location.href='/register'\">Back</button></div>")
            if User.query.filter_by(username=full_name).first():
                return STYLE+wrap(f"{top_bar()}<div class=form><p>Username exists</p><button class=btn-dark onclick=\"location.href='/register'\">Back</button></div>")
            my_code = gen_code(full_name)
            referred_by = session.get('ref_code')
            user=User(username=full_name,password=generate_password_hash(p), referral_code=my_code + str(random.randint(10,99)), referred_by=referred_by, balance=5.0)
            db.session.add(user); db.session.commit()
            if referred_by:
                ref_user = User.query.filter_by(referral_code=referred_by).first()
                if ref_user:
                    ref_user.balance += 20
                    user.balance += 10
                    db.session.add(WinLog(username=ref_user.username, game="REFERRAL", amount=20, date=datetime.now().strftime("%Y-%m-%d %H:%M")))
                    db.session.commit()
            session['uid']=user.id; session['uname']=full_name
            session.pop('ref_code', None)
            return redirect('/menu')
        except Exception as e:
            return STYLE+wrap(f"<div class=form><p style=color:#ef4444>Error {e}</p><button class=btn-dark onclick=\"location.href='/register'\">Back</button></div>")
    banner = f"<div style=background:#052e16;border:1px solid #22c55e;color:#86efac;padding:7px 10px;border-radius:6px;font-weight:800;font-size:11px;margin:8px 14px>🎁 Referred by {session.get('ref_code')} - You get R10 FREE!</div>" if session.get('ref_code') else ""
    return STYLE+wrap(f"""
{top_bar()}
<div style=text-align:center;padding:8px 14px 0><h1 style=color:#facc15;font-size:26px;font-weight:900;margin:8px 0 2px>Create Account</h1><p style=color:#9ca3af;font-size:11px;margin:0 0 10px>Join Mochaina Lotto & play to win big</p></div>
<div class=jack>🎟️ WIN TODAY'S JACKPOT • R5,000,000</div>
{banner}
<div class=form>
<form method='post'>
<div class=lab>Full Name</div><input class=in name='full_name' placeholder='e.g. Thabo Mthembu' required>
<div class=lab>ID Number</div><input class=in name='id_number' placeholder='e.g. 9001015000081' maxlength='13' required>
<div class=lab>Phone Number</div><input class=in name='phone' placeholder='+27 82 555 1234' required>
<div class=lab>Password</div><input class=in name='password' type='password' placeholder='••••••••' required>
<div class=lab>Confirm Password</div><input class=in name='confirm_password' type='password' placeholder='••••••••' required>
<div style=text-align:left;margin-top:8px;font-size:10px;color:#9ca3af><input type=checkbox checked> I agree to the Terms & Conditions and am 18+</div>
<button class=btn-gold>REGISTER NOW</button>
</form>
<div class=link>Already have an account? <a href='/login'>Login</a></div>
<div class=games><div class=gtitle>GAME OPTIONS AVAILABLE</div><div class=grid2><div class=gbox><div>🎟️</div><b>R50 Lucky Draw</b><small>Draw: Today 20:00 • Jackpot R250k</small></div><div class=gbox2><div>🎯</div><b>R100 Mega Lotto</b><small>Draw: Sat • Jackpot R2M</small></div></div></div>
</div>
""")

@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    try: auto_draw_if_due()
    except: pass
    user=User.query.get(session['uid'])
    if not user: session.clear(); return redirect('/login')
    ts=get_next_draw_timestamp()
    today = date.today().isoformat()
    can_daily = (user.daily_last!= today)
    daily_btn = "DAILY FREE - CLAIM R5" if can_daily else f"Daily done - Streak {user.daily_streak}"
    return STYLE+wrap(f"""{top_bar(user.balance)}
<div class=form style=text-align:center>
<div style=color:#facc15;font-weight:900;font-size:10px;letter-spacing:1px>💰 LIVE JACKPOT</div><div class=jackpot>R{get_jackpot():,.2f}</div>
<p style=color:#22c55e;font-weight:900;margin:8px 0;font-size:13px>Balance: R{user.balance:.2f} | Won: R{user.total_won or 0:.0f}</p>
<p style=font-size:11px;color:#9ca3af>Welcome, <b style=color:#facc15>{user.username}</b> • {user.referral_code or ''}</p>
<div style=margin:8px 0><span style=font-size:10px;color:#6b7280>⏰ NEXT DRAW: </span><span id='liveTimer' class=timer>{next_draw_str()}</span></div><script>startLiveCountdown({ts}, 'liveTimer')</script>
<button class=btn-gold onclick="location.href='/play'">🎯 PLAY LOTTO</button>
<button class=btn-dark onclick="location.href='/daily'">🎁 {daily_btn}</button>
<button class=btn-dark onclick="location.href='/my_tickets'">🎫 MY TICKETS</button>
<button class=btn-dark onclick="location.href='/referral'">👥 REFER & EARN R20</button>
<button class=btn-dark onclick="location.href='/leaderboard'">🏆 LEADERBOARD</button>
<button class=btn-dark onclick="location.href='/load'">💳 LOAD FUNDS</button>
<button class=btn-dark onclick="location.href='/withdraw'">💸 WITHDRAW</button>
<button class=btn-dark onclick="location.href='/results'">📊 RESULTS</button>
<button class=btn-dark onclick="location.href='/admin?key=mochaina123'">⚙️ ADMIN</button>
<button class=btn-gold style=background:linear-gradient(90deg,#ef4444,#a855f7) onclick="location.href='/live'">🔴 LIVE GAMES - WHEEL + SLOTS</button>
<button class=btn-dark onclick="location.href='/logout'">LOGOUT</button>
</div>""")

@app.route('/referral')
def referral():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    link = request.host_url.rstrip('/') + f"/register?ref={user.referral_code}"
    count = User.query.filter_by(referred_by=user.referral_code).count()
    return STYLE+wrap(f"""{top_bar()}<div class=form><h2 style=color:#facc15;font-weight:900>👥 REFER & EARN R20</h2><p style=color:#9ca3af;font-size:11px>Share link - you get R20, friend gets R10</p><div style=background:#111;color:#facc15;padding:10px;border-radius:6px;font-weight:900;word-break:break-all;font-size:11px;border:1px solid #facc1533>{link}</div><div style=display:flex;gap:6px;margin:10px 0><button class=btn-gold onclick="navigator.clipboard.writeText('{link}');alert('Copied!')">📋 COPY</button><a href='https://wa.me/?text={urllib.parse.quote(f"Join Mochaina Lotto and win! Use my link: {link}")}' target='_blank' style=text-decoration:none;flex:1><div style=background:#22c55e;color:white;padding:12px;border-radius:6px;font-weight:900;text-align:center>📱 WhatsApp</div></a></div><p style=font-weight:900;font-size:12px>👥 Friends: {count} • Earned: R{count*20}</p><button class=btn-dark onclick="location.href='/menu'">BACK</button></div>""")

@app.route('/daily')
def daily():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    today = date.today().isoformat()
    if user.daily_last == today:
        return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>✅ Already Claimed Today</h2><p>Streak: {user.daily_streak} days</p><button class=btn-gold onclick=\"location.href='/menu'\">MENU</button></div>")
    return STYLE+wrap(f"""{top_bar()}<div class=form><h2 style=color:#facc15;font-weight:900>🎁 DAILY FREE BONUS</h2><p style=font-size:12px;color:#9ca3af>Claim R5 free every day! Streak: {user.daily_streak} days</p><div style=background:linear-gradient(135deg,#facc15,#f59e0b);color:#000;padding:18px;border-radius:10px;margin:10px 0><p style=font-size:30px;margin:0>🎁</p><p style=font-weight:900>R5 FREE + Free Spin</p></div><a href='/claim_daily' style=text-decoration:none><div class=btn-gold style=text-align:center>⚡ CLAIM NOW</div></a><button class=btn-dark onclick="location.href='/menu'">BACK</button></div>""")

@app.route('/claim_daily')
def claim_daily():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    today = date.today().isoformat()
    if user.daily_last == today: return redirect('/daily')
    user.balance += 5; user.daily_last = today; user.daily_streak = (user.daily_streak or 0) + 1
    if user.daily_streak % 7 == 0: user.balance += 20
    db.session.commit()
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>🎉 R5 CLAIMED!</h2><p>Balance: R{user.balance:.2f} • Streak: {user.daily_streak} days</p>{'<p>🔥 7 DAY BONUS +R20!</p>' if user.daily_streak%7==0 else ''}<button class=btn-gold onclick=\"location.href='/live'\">PLAY LIVE NOW</button><br><button class=btn-dark onclick=\"location.href='/menu'\">MENU</button></div>")

@app.route('/leaderboard')
def leaderboard():
    if 'uid' not in session: return redirect('/login')
    tops = WinLog.query.order_by(WinLog.amount.desc()).limit(20).all()
    if not tops:
        tops = User.query.order_by(User.total_won.desc()).limit(10).all()
        html = "".join([f"<div class='leader-row'><span>#{i+1} {u.username[:12]}</span><span style=color:#16a34a>R{u.total_won or 0:.0f}</span></div>" for i,u in enumerate(tops)]) or "<p style=color:#000>No winners yet</p>"
    else:
        html = "".join([f"<div class='leader-row'><span>#{i+1} {w.username[:12]} • {w.game}</span><span style=color:#16a34a>R{w.amount:.0f}</span></div>" for i,w in enumerate(tops)])
    return STYLE+wrap(f"{top_bar()}<div class=card-white><h2 style=font-weight:900>🏆 LEADERBOARD</h2><div style=text-align:left;max-height:400px;overflow:auto>{html}</div><div class=live-ticker><span>🔥 LIVE WINNERS: Be next! Play now and top the board • </span></div><br><button class=btn-gold onclick=\"location.href='/menu'\">BACK TO MENU</button></div>")

@app.route('/live')
def live_games():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+wrap(f"""{top_bar(user.balance)}<div class=form><h2 style=color:#facc15;font-weight:900>🔴 LIVE ARENA</h2><p style=color:#22c55e;font-weight:900>Balance: R{user.balance:.2f}</p><div class=live-ticker style=margin:0 0 10px 0><span>🔴 LIVE: Thabo won R250 Wheel • Maria won R100 Slots • 247 online • </span></div><div class=gbox style=cursor:pointer onclick="location.href='/wheel'"><b>🎡 WHEEL COLOR - x8 MAX</b><small>Spin wheel • 12 colors • Win up to 8x</small></div><div class=gbox2 style=margin-top:10px;cursor:pointer onclick="location.href='/slots'"><b>🎰 PRO SLOTS - 10x JACKPOT</b><small>Match 3 • 10x Jackpot • Instant win</small></div><button class=btn-dark style=margin-top:12px onclick="location.href='/menu'">⬅️ BACK TO MENU</button></div>""")

@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    cols = ["#dc2626","#facc15","#16a34a","#2563eb","#ea580c","#ec4899","#7c3aed","#06b6d4","#16a34a","#facc15","#dc2626","#06b6d4"]
    labels = ["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]
    svg = ""
    for i in range(12):
        a1 = math.radians(i*30-90); a2 = math.radians((i+1)*30-90)
        x1 = 100+95*math.cos(a1); y1 = 100+95*math.sin(a1)
        x2 = 100+95*math.cos(a2); y2 = 100+95*math.sin(a2)
        svg += f'<path d="M100,100 L{round(x1,1)},{round(y1,1)} A95,95 0 0,1 {round(x2,1)},{round(y2,1)} Z" fill="{cols[i]}" stroke="white" stroke-width="2.5"/>'
        mid = math.radians(i*30+15-90); tx = 100+60*math.cos(mid); ty = 100+60*math.sin(mid)
        svg += f'<text x="{round(tx,1)}" y="{round(ty,1)}" fill="white" font-size="10" font-weight="900" text-anchor="middle" dominant-baseline="middle" transform="rotate({i*30+15} {round(tx,1)} {round(ty,1)})">{labels[i]}</text>'
    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>WHEEL LIVE</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;900&display=swap');
body{{background:#0a0a0a;color:white;font-family:Outfit,Arial;text-align:center;margin:0;padding:4px}}
.card{{background:white;color:#0f172a;border-radius:22px;padding:12px;max-width:420px;margin:4px auto}}
.topbar{{background:#111;color:#facc15;padding:10px 14px;border-radius:12px;font-weight:900;display:flex;justify-content:space-between;font-size:13px;border:1px solid #facc1533}}
.wheel-wrap{{position:relative;width:285px;height:285px;margin:8px auto 16px auto}}
.pointer{{position:absolute;top:-14px;left:50%;transform:translateX(-50%);font-size:36px;z-index:20}}
#wheel{{width:100%;height:100%;border-radius:50%;border:8px solid #facc15;background:white;overflow:hidden}}
.history{{display:flex;gap:5px;justify-content:center;margin:5px 0}}
.hist-dot{{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:900;color:white;border:1.5px solid white}}
.bet-status{{background:linear-gradient(90deg,#fef9c3,#fde68a);padding:10px;border-radius:12px;font-weight:900;margin:18px 0 14px 0;border:1.5px dashed #eab308;color:#422006;font-size:12px}}
.color-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
.color-btn{{padding:8px 2px;border-radius:11px;border:2.5px solid white;font-weight:900;font-size:11px;cursor:pointer;color:white}}
.color-btn.selected{{border-color:#0f172a;transform:scale(1.06);box-shadow:0 0 0 2.5px #facc15}}
.chip-row{{display:flex;gap:6px;justify-content:center;margin:10px 0}}
.chip{{width:42px;height:42px;border-radius:50%;border:2.5px solid white;font-weight:900;font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;background:#14532d;color:white}}
.chip.selected{{transform:translateY(-3px) scale(1.1);box-shadow:0 0 0 2.5px #facc15;color:#facc15;border-color:#facc15}}
.btn{{border:none;padding:12px;border-radius:14px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}}
.btn-gold{{background:linear-gradient(90deg,#facc15,#f97316);color:#000}}
.music-btn{{position:fixed;top:10px;right:10px;background:#0f172a;color:#facc15;border:2px solid #facc15;border-radius:20px;padding:6px 12px;font-size:11px;font-weight:900;z-index:999;cursor:pointer}}
</style></head><body>
<button id='musicBtn' class='music-btn' onclick="toggleMusic()">🎵 MUSIC: ON</button>
<div class=card>
<div class=topbar><span>🎡 WHEEL LIVE</span><span>💰 R<span id='bal'>{user.balance:.0f}</span></span><span id='lastWin' style="background:#facc15;color:#000;padding:3px 8px;border-radius:20px;font-size:11px">Last: -</span></div>
<div class=history id='history'></div>
<div class=wheel-wrap><div class=pointer>👇</div><div id='wheel'><svg viewBox="0 0 200 200" style=width:100%;height:100%>{svg}<circle cx="100" cy="100" r="26" fill="#0f172a" stroke="#facc15" stroke-width="4"/><circle cx="100" cy="100" r="12" fill="#facc15"/></svg></div></div>
<div id='myBet' class=bet-status>👆 Tap color + chip - Music starts</div>
<div class=color-grid>
<button class='color-btn' style=background:#dc2626 onclick="pick('RED',2,this)">RED<br><small>x2</small></button>
<button class='color-btn' style=background:#facc15;color:#000 onclick="pick('YEL',3,this)">YEL<br><small>x3</small></button>
<button class='color-btn' style=background:#16a34a onclick="pick('GREEN',2.5,this)">GREEN<br><small>x2.5</small></button>
<button class='color-btn' style=background:#2563eb onclick="pick('BLUE',2.5,this)">BLUE<br><small>x2.5</small></button>
<button class='color-btn' style=background:#ea580c onclick="pick('ORG',3,this)">ORG<br><small>x3</small></button>
<button class='color-btn' style=background:#ec4899 onclick="pick('PINK',4,this)">PINK<br><small>x4</small></button>
<button class='color-btn' style=background:#7c3aed onclick="pick('PURP',6,this)">PURP<br><small>x6</small></button>
<button class='color-btn' style=background:#06b6d4 onclick="pick('CYAN',8,this)">CYAN<br><small>x8</small></button>
</div>
<div class=chip-row><div class=chip onclick="setS(1,this)">R1</div><div class=chip onclick="setS(2,this)">R2</div><div class=chip onclick="setS(5,this)" style="color:#facc15;border-color:#facc15">R5</div><div class=chip onclick="setS(10,this)">R10</div></div>
<div id='stakeShow'>Stake: R5</div>
<button id='betBtn' class='btn btn-gold' onclick="doSpin()" disabled>SELECT COLOR FIRST</button>
<button class='btn' style=background:#e2e8f0;color:#475569 onclick="location.href='/live'">⬅️ BACK</button>
<div id='winBox'></div>
</div>
<script>
var colHex={{"RED":"#dc2626","YEL":"#facc15","GREEN":"#16a34a","BLUE":"#2563eb","ORG":"#ea580c","PINK":"#ec4899","PURP":"#7c3aed","CYAN":"#06b6d4"}};
var sel=null,mult=2,stake=5,spinning=false,cr=0,hist=[];
let audioCtx=null, musicGain=null, musicStarted=false, musicMuted=false, musicTimer=null;
function getAudio(){{if(!audioCtx) audioCtx=new(window.AudioContext||window.webkitAudioContext)(); return audioCtx;}}
function beep(freq,dur,vol,type='sine'){{try{{let ctx=getAudio();let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=freq;o.type=type;o.connect(g);g.connect(ctx.destination);g.gain.setValueAtTime(vol,ctx.currentTime);g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);}}catch(e){{}}}}
function playChord(freqs,dur){{try{{let ctx=getAudio();if(!musicGain||musicMuted) return; freqs.forEach(f=>{{let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=f;o.type='triangle';o.connect(g);g.connect(musicGain);g.gain.setValueAtTime(0,ctx.currentTime);g.gain.linearRampToValueAtTime(0.08,ctx.currentTime+0.8);g.gain.linearRampToValueAtTime(0,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);}});}}catch(e){{}}}}
function startRomanticAuto(){{ if(musicStarted) return; let ctx=getAudio(); if(!musicGain){{musicGain=ctx.createGain();musicGain.connect(ctx.destination);musicGain.gain.value=0.28;}} musicStarted=true; document.getElementById('musicBtn').innerText='🎵 MUSIC: ON'; let chords=[[261.63,329.63,392.00],[220.00,261.63,329.63],[174.61,220.00,261.63],[196.00,246.94,293.66],[261.63,392.00,493.88],[220.00,329.63,440.00],[174.61,261.63,329.63],[196.00,293.66,392.00]]; let melody=[523.25,659.25,783.99,1046.50,783.99,659.25,587.33,523.25]; let idx=0; function loop(){{ if(musicMuted){{musicTimer=setTimeout(loop,3500);return;}} playChord(chords[idx%8],3.8); setTimeout(()=>{{if(!musicMuted) beep(melody[idx%8],2.0,0.05,'sine');}},600); idx=(idx+1)%8; musicTimer=setTimeout(loop,3500); }} loop();}}
function toggleMusic(){{musicMuted=!musicMuted; document.getElementById('musicBtn').innerText=musicMuted?'🔇 MUSIC: OFF':'🎵 MUSIC: ON'; if(!musicMuted &&!musicStarted) startRomanticAuto();}}
function soundClick(){{beep(600,0.08,0.12,'sine');}}
function soundWheelSpin(){{let c=0;let iv=setInterval(()=>{{beep(300+c*25,0.07,0.07,'sawtooth');c++;if(c>28) clearInterval(iv);}},70);}}
function soundWheelWin(){{beep(523,0.2,0.12);setTimeout(()=>beep(659,0.2,0.12),150);setTimeout(()=>beep(784,0.5,0.15),300);}}
function soundWheelLose(){{beep(180,0.5,0.07,'sawtooth');}}
function setS(v,el){{if(spinning)return;stake=v;document.querySelectorAll('.chip').forEach(c=>c.classList.remove('selected'));if(el)el.classList.add('selected');document.getElementById('stakeShow').innerText='Stake: R'+v;if(sel)enable(); startRomanticAuto(); soundClick();}}
function pick(c,m,el){{if(spinning)return;sel=c;mult=m;document.querySelectorAll('.color-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');enable(); startRomanticAuto(); soundClick();}}
function enable(){{if(spinning)return;document.getElementById('betBtn').disabled=false;document.getElementById('betBtn').innerText='🔒 LOCK R'+stake+' ON '+sel+' x'+mult;document.getElementById('myBet').innerText='✅ Ready: R'+stake+' on '+sel;}}
function addHist(color){{hist.unshift(color);if(hist.length>10)hist.pop();var h=document.getElementById('history');h.innerHTML='';hist.forEach(c=>{{var d=document.createElement('div');d.className='hist-dot';d.style.background=colHex[c];d.innerText=c[0];h.appendChild(d);}});}}
function doSpin(){{ if(spinning||!sel)return; spinning=true; startRomanticAuto(); soundWheelSpin(); document.getElementById('myBet').innerText='🔒 BETS CLOSED - Spinning...';document.getElementById('betBtn').disabled=true; fetch('/wheel_spin?stake='+stake+'&color='+sel.toLowerCase()).then(r=>r.json()).then(d=>{{ var wheel=document.getElementById('wheel'); var idx=d.index; var target=(345-idx*30+360)%360;var delta=(target-cr+360)%360;var total=4320+delta; var startTime=null;var duration=6500; function easeOut(t){{return 1-Math.pow(1-t,4);}} function animate(now){{ if(!startTime)startTime=now;var p=Math.min((now-startTime)/duration,1);var cur=cr+total*easeOut(p);wheel.style.transform='rotate('+cur+'deg)'; if(p<1){{requestAnimationFrame(animate);}}else{{ cr=target;wheel.style.transform='rotate('+cr+'deg)';document.getElementById('lastWin').innerText='Last: '+d.landed_label;addHist(d.landed_label); document.getElementById('bal').innerText=d.balance.toFixed(0); if(d.win>0){{document.getElementById('winBox').innerText='🎉 WON R'+d.win.toFixed(0)+'!';document.getElementById('winBox').style.color='#16a34a'; soundWheelWin();}} else{{document.getElementById('winBox').innerText='💔 '+d.landed_label;document.getElementById('winBox').style.color='#ef4444'; soundWheelLose();}} sel=null;document.querySelectorAll('.color-btn').forEach(b=>{{b.classList.remove('selected');}});document.getElementById('betBtn').disabled=true;document.getElementById('betBtn').innerText='SELECT COLOR FIRST';document.getElementById('myBet').innerText='👆 Tap color - OPEN';spinning=false; }} }}requestAnimationFrame(animate); }});}}
document.querySelectorAll('.chip')[2].classList.add('selected');
document.body.addEventListener('click', ()=>{{if(!musicStarted) startRomanticAuto();}}, {{once:true}});
</script></body></html>"""

@app.route('/wheel_spin')
def wheel_spin():
    if 'uid' not in session: return {"error":"login"}, 401
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',1)))
    except: stake=1
    if stake<=0 or stake>1000: return {"error":"Invalid stake"}
    color=request.args.get('color','red').lower()
    if stake>user.balance: return {"error":"No balance","win":0,"index":0,"landed_label":"0","balance":user.balance}
    user.balance-=stake
    cols=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]
    mults={"RED":2,"YEL":3,"GREEN":2.5,"BLUE":2.5,"ORG":3,"PINK":4,"PURP":6,"CYAN":8}
    idx=random.randint(0,11); landed=cols[idx]; win=0
    if landed==color.upper():
        win=stake*mults.get(landed,2); user.balance+=win; user.total_won = (user.total_won or 0) + win
        db.session.add(WinLog(username=user.username, game="WHEEL", amount=win, date=datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.session.commit()
    return {"win":round(win,2),"index":idx,"landed_label":landed,"balance":round(user.balance,2)}

@app.route('/slots')
def slots():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>SLOTS</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;900&display=swap');body{{background:#0a0a0a;color:white;font-family:Outfit,Arial;text-align:center;margin:0;padding:10px}}.card{{background:white;color:#0f172a;border-radius:22px;padding:16px;max-width:420px;margin:10px auto}}.reel-box{{width:80px;height:90px;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.2);border:3px solid #facc15;display:flex;align-items:center;justify-content:center}}.reel{{font-size:42px;font-weight:900;transition:0.1s}}.reel.spinning{{filter:blur(3px);transform:scaleY(1.2)}}.btn{{border:none;padding:14px;border-radius:14px;font-weight:900;width:100%;cursor:pointer;margin:6px 0}}.btn-blue{{background:linear-gradient(135deg,#3b82f6,#2563eb);color:white}}.btn-dark{{background:#0f172a;color:white}}</style></head><body>
<div class=card><div style=display:flex;justify-content:space-between;align-items:center><button onclick="toggleMusicSlots()" id='musicBtnSlot' style=background:#0f172a;color:#facc15;border:1.5px solid #facc15;border-radius:20px;padding:6px 12px;font-size:11px;font-weight:900>🎵 MUSIC: ON</button><span style=font-weight:900>🎰 SLOTS LIVE</span><span id='slotBal' style=color:#16a34a;font-weight:900>R{user.balance:.0f}</span></div>
<div style=background:linear-gradient(135deg,#0f172a,#1e293b);padding:18px;border-radius:20px;margin:12px 0;border:1px solid #facc1533><div style=display:flex;justify-content:center;gap:10px><div class='reel-box'><div id='r1' class='reel'>🍒</div></div><div class='reel-box'><div id='r2' class='reel'>🍋</div></div><div class='reel-box'><div id='r3' class='reel'>🔔</div></div></div></div>
<div id='slot_res' style=font-weight:900;margin:12px 0;min-height:22px;font-size:18px></div><div id='slot_win' style=font-weight:900;font-size:26px;min-height:30px></div>
<div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px><button class='btn btn-dark' onclick="setSlotStake(1)">R1</button><button class='btn btn-dark' onclick="setSlotStake(2)">R2</button><button class='btn btn-dark' onclick="setSlotStake(5)">R5</button><button class='btn btn-dark' onclick="setSlotStake(10)">R10</button></div>
<input id='slot_stake' type='hidden' value='1'><div id='slotStakeShow' style=text-align:left;font-size:13px;font-weight:800;margin:6px 0>Stake: R1</div>
<button id='spinBtn' class='btn btn-blue' style=padding:16px;font-size:18px onclick="spinSlot()">🎰 SPIN</button>
<button class='btn' style=background:#f1f5f9;color:#475569;border:1px solid #e2e8f0 onclick="location.href='/live'">BACK TO LIVE</button>
</div>
<script>
    let slotSymbols=["🍒","🍋","🔔","7️⃣","⭐","💎","🍉","🍇"];
    let audioCtx=null, musicGain=null, musicStarted=false, musicMuted=false, musicTimer=null;
    function getAudio(){{if(!audioCtx) audioCtx=new(window.AudioContext||window.webkitAudioContext)(); return audioCtx;}}
    function beep(freq,dur,vol,type='sine'){{try{{let ctx=getAudio();let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=freq;o.type=type;o.connect(g);g.connect(ctx.destination);g.gain.setValueAtTime(vol,ctx.currentTime);g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);}}catch(e){{}}}}
    function playChord(freqs,dur){{try{{let ctx=getAudio();if(!musicGain||musicMuted) return; freqs.forEach(f=>{{let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=f;o.type='triangle';o.connect(g);g.connect(musicGain);g.gain.setValueAtTime(0,ctx.currentTime);g.gain.linearRampToValueAtTime(0.08,ctx.currentTime+0.8);g.gain.linearRampToValueAtTime(0,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);}});}}catch(e){{}}}}
    function startRomanticAutoSlots(){{ if(musicStarted) return; let ctx=getAudio(); if(!musicGain){{musicGain=ctx.createGain();musicGain.connect(ctx.destination);musicGain.gain.value=0.28;}} musicStarted=true; let chords=[[261.63,329.63,392.00],[220.00,261.63,329.63],[174.61,220.00,261.63],[196.00,246.94,293.66]]; let melody=[523.25,659.25,783.99,1046.50]; let idx=0; function loop(){{ if(musicMuted){{musicTimer=setTimeout(loop,3500);return;}} playChord(chords[idx%4],3.8); setTimeout(()=>{{if(!musicMuted) beep(melody[idx%4],2.0,0.05,'sine');}},600); idx=(idx+1)%4; musicTimer=setTimeout(loop,3500); }} loop();}}
    function toggleMusicSlots(){{musicMuted=!musicMuted; document.getElementById('musicBtnSlot').innerText=musicMuted?'🔇 MUSIC: OFF':'🎵 MUSIC: ON'; if(!musicMuted &&!musicStarted) startRomanticAutoSlots();}}
    function soundSlotsSpin(){{let c=0;let iv=setInterval(()=>{{beep(500+Math.random()*500,0.09,0.06,'square');c++;if(c>18)clearInterval(iv);}},85);}}
    function soundSlotTick(n){{if(n==1)beep(750,0.12,0.10,'square');if(n==2)beep(950,0.12,0.10,'square');if(n==3)beep(1150,0.18,0.12,'square');}}
    function soundSlotsWin(){{beep(523,0.2,0.10);setTimeout(()=>beep(659,0.2,0.10),120);setTimeout(()=>beep(784,0.2,0.10),240);setTimeout(()=>beep(1046,0.6,0.15),360);}}
    function soundSlotsLose(){{beep(280,0.4,0.06,'sawtooth');}}
    function setSlotStake(v){{document.getElementById('slot_stake').value=v;document.getElementById('slotStakeShow').innerText='Stake: R'+v; startRomanticAutoSlots(); beep(600,0.08,0.12,'sine');}}
    function spinSlot(){{let stake=document.getElementById('slot_stake').value;let btn=document.getElementById('spinBtn');if(btn.disabled)return; startRomanticAutoSlots(); btn.disabled=true;btn.innerText='SPINNING...';let r1=document.getElementById('r1'),r2=document.getElementById('r2'),r3=document.getElementById('r3');r1.classList.add('spinning');r2.classList.add('spinning');r3.classList.add('spinning');soundSlotsSpin();let inter1=setInterval(function(){{r1.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},60);let inter2=setInterval(function(){{r2.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},70);let inter3=setInterval(function(){{r3.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},80);fetch('/slots_spin?stake='+stake).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);clearInterval(inter1);clearInterval(inter2);clearInterval(inter3);r1.classList.remove('spinning');r2.classList.remove('spinning');r3.classList.remove('spinning');btn.disabled=false;btn.innerText='SPIN';return;}}setTimeout(function(){{clearInterval(inter1);r1.classList.remove('spinning');r1.innerText=d.reels[0];soundSlotTick(1);}},1000);setTimeout(function(){{clearInterval(inter2);r2.classList.remove('spinning');r2.innerText=d.reels[1];soundSlotTick(2);}},1900);setTimeout(function(){{clearInterval(inter3);r3.classList.remove('spinning');r3.innerText=d.reels[2];soundSlotTick(3);document.getElementById('slot_res').innerText=d.msg;document.getElementById('slotBal').innerText='R'+d.balance.toFixed(0);if(d.win>0){{document.getElementById('slot_win').innerText='WIN R'+d.win+'!';document.getElementById('slot_win').style.color='#16a34a';soundSlotsWin();}}else{{document.getElementById('slot_win').innerText=d.reels.join(' - ');document.getElementById('slot_win').style.color='#ef4444';soundSlotsLose();}}btn.disabled=false;btn.innerText='SPIN AGAIN';}},2800);}});}}
    document.body.addEventListener('click', ()=>{{if(!musicStarted) startRomanticAutoSlots();}}, {{once:true}});
</script></body></html>"""

@app.route('/slots_spin')
def slots_spin():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',1)))
    except: stake=1
    if stake<=0 or stake>1000: return {"error":"Invalid stake"}
    if stake>user.balance: return {"reels":["❌","❌","❌"],"msg":"No balance","win":0,"balance":user.balance}
    user.balance-=stake; symbols=["🍒","🍋","🔔","7️⃣","⭐","💎"]; win=0
    if random.random()<0.7:
        reels=[random.choice(symbols) for _ in range(3)]
        while reels[0]==reels[1]==reels[2]: reels=[random.choice(symbols) for _ in range(3)]
        msg=f"{reels[0]} {reels[1]} {reels[2]}"
    else:
        reels=[random.choice(symbols) for _ in range(3)]
        if reels[0]==reels[1]==reels[2]: win=stake*10; msg=f"JACKPOT 3x {reels[0]} R{win}!"
        else: reels[1]=reels[0]; win=stake*2; msg=f"Small win R{win}"
    if win>0:
        user.balance+=win; user.total_won = (user.total_won or 0) + win
        db.session.add(WinLog(username=user.username, game="SLOTS", amount=win, date=datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.session.commit()
    return {"reels":reels,"msg":msg,"win":win,"balance":round(user.balance,2)}

@app.route('/play')
def play():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    grid="".join([f"<button id='btn{i}' class='num-btn' onclick='toggle({i},this)'>{i}</button>" for i in range(1,37)])
    return STYLE+wrap(f"""{top_bar(user.balance)}<div class=form><div style=display:flex;gap:8px><input id='bet_input' type='number' value='10' min='1' max='1000' class=in style=width:100px><button class=btn-gold onclick='autoPick()' style=width:auto;padding:10px 18px;margin-top:0>🎲 Auto Pick</button></div><div class=numgrid>{grid}</div><div style=margin:10px 0><button id='wbtn1' class='wing-btn' onclick='pickWing(1,this)'>W1</button><button id='wbtn2' class='wing-btn' onclick='pickWing(2,this)'>W2</button><button id='wbtn3' class='wing-btn' onclick='pickWing(3,this)'>W3</button><button id='wbtn4' class='wing-btn' onclick='pickWing(4,this)'>W4</button></div><p id='your4' style=font-weight:800;font-size:12px;color:#facc15>Your 4: []</p><p id='yourW' style=font-weight:800;font-size:12px;color:#facc15>Wing: -</p><form method='post' action='/buy'><input type='hidden' name='numbers' id='nums_input' required><input type='hidden' name='wing' id='wing_input' required><input type='hidden' name='bet' id='bet_hidden'><button class=btn-gold onclick="document.getElementById('bet_hidden').value=document.getElementById('bet_input').value">🔥 PLACE BET - WIN R{get_jackpot():,.0f}</button></form><button class=btn-dark onclick="location.href='/menu'">BACK</button></div>""")

@app.route('/buy', methods=['POST'])
def buy():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try:
        nums_str=request.form['numbers']; wing=int(request.form['wing']); bet=int(float(request.form['bet']))
        nums=list(map(int, nums_str.split(',')))
        if len(nums)!=4 or len(set(nums))!=4 or any(n<1 or n>36 for n in nums): raise ValueError
        if wing not in [1,2,3,4]: raise ValueError
        if bet<=0 or bet>1000: raise ValueError
    except:
        return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444;font-weight:800>❌ Pick 4 unique 1-36 + Wing 1-4</p><button class=btn-dark onclick=\"location.href='/play'\">Back</button></div>")
    if bet>user.balance: return STYLE+wrap(f"{top_bar()}<div class=form><p>No balance R{user.balance:.2f}</p><button class=btn-dark onclick=\"location.href='/play'\">Back</button></div>")
    user.balance-=bet; save_jackpot(get_jackpot()+bet*0.1)
    t=Ticket(user_id=user.id, username=user.username, numbers=nums_str, wing=wing, bet=bet); db.session.add(t); db.session.commit()
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#22c55e>✅ Ticket #{t.id} LIVE!</h2><p style=font-weight:800;color:#facc15>{nums_str}+W{wing} R{bet}</p><button class=btn-gold onclick=\"location.href='/menu'\">BACK TO MENU</button></div>")

@app.route('/my_tickets')
def my_tickets():
    if 'uid' not in session: return redirect('/login')
    tickets=Ticket.query.filter_by(user_id=session['uid']).order_by(Ticket.id.desc()).all()
    html="".join([f"<div style=text-align:left;padding:10px;border-bottom:1px solid #1f1f1f;display:flex;justify-content:space-between;color:white><span>#{t.id} <b style=color:#facc15>{t.numbers}</b>+W{t.wing}</span><span style=background:#facc15;color:#000;padding:2px 8px;border-radius:6px;font-weight:800;font-size:11px>R{t.bet}</span></div>" for t in tickets]) or "<p style=color:#9ca3af>No tickets</p>"
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>🎫 My Tickets</h2><div>{html}</div><br><button class=btn-gold onclick=\"location.href='/menu'\">Menu</button></div>")

@app.route('/results')
def results():
    draws=Draw.query.order_by(Draw.id.desc()).limit(10).all()
    html="".join([f"<div style=display:flex;justify-content:space-between;align-items:center;padding:10px 8px;border-bottom:1px solid #1f1f1f;text-align:left><span><b style=color:white>{d.date}</b><br><span style=font-size:11px;background:#111;color:#facc15;padding:3px 8px;border-radius:6px;font-weight:800;border:1px solid #facc15>{d.numbers}+W{d.wing}</span></span> <a href='/confirm_delete_draw/{d.id}' style=background:#111;color:white;width:34px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:50%;text-decoration:none;font-size:16px;border:2px solid #ef4444>❎</a></div>" for d in draws]) or "<p style=color:#9ca3af>No results</p>"
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>🏆 Live Results</h2><div>{html}</div><br><a href='/confirm_delete_last' style=background:#111;color:#facc15;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:900;display:flex;align-items:center;justify-content:center;gap:8px;border:2px solid #ef4444;font-size:11px>❎ Delete LAST Result</a><br><button onclick=\"location.href='/menu'\" class=btn-dark>⬅️ Menu</button></div>")

@app.route('/confirm_delete_draw/<int:did>')
def confirm_delete_draw(did):
    if 'uid' not in session: return redirect('/login')
    d = Draw.query.get(did)
    if not d: return redirect('/results')
    return STYLE+wrap(f"""{top_bar()}<div class=form><h2 style=color:#ef4444>⚠️ Confirm Delete?</h2><div style=background:#111;padding:14px;border-radius:10px;margin:10px 0;font-weight:900;border:1.5px solid #ef4444;color:#fca5a5>{d.date}<br>{d.numbers}+W{d.wing}</div><a href='/delete_draw/{did}' style=background:#ef4444;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:900;display:block;margin:8px;text-align:center>✅ YES, DELETE IT</a><a href='/results' style=background:#22c55e;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:900;display:block;margin:8px;text-align:center>❌ NO, CANCEL</a></div>""")

@app.route('/confirm_delete_last')
def confirm_delete_last():
    if 'uid' not in session: return redirect('/login')
    last = Draw.query.order_by(Draw.id.desc()).first()
    if not last: return redirect('/results')
    return STYLE+wrap(f"""{top_bar()}<div class=form><h2 style=color:#ef4444>⚠️ Delete LAST Result?</h2><div style=background:#111;padding:14px;border-radius:10px;margin:10px 0;font-weight:900;border:1.5px solid #ef4444;color:#fca5a5>{last.date}<br>{last.numbers}+W{last.wing}</div><a href='/delete_last_draw' style=background:#ef4444;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:900;display:block;margin:8px;text-align:center>🗑️ YES, DELETE LAST</a><a href='/results' style=background:#22c55e;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:900;display:block;margin:8px;text-align:center>❌ NO, CANCEL</a></div>""")

@app.route('/delete_last_draw')
def delete_last_draw():
    if 'uid' not in session: return redirect('/login')
    last = Draw.query.order_by(Draw.id.desc()).first()
    if last: db.session.delete(last); db.session.commit()
    return redirect('/results')
@app.route('/delete_draw/<int:did>')
def delete_draw(did):
    if 'uid' not in session: return redirect('/login')
    d = Draw.query.get(did)
    if d: db.session.delete(d); db.session.commit()
    return redirect('/results')

@app.route('/load')
def load_funds():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+wrap(f"""{top_bar(user.balance)}<div class=form><h2 style=color:#facc15>💰 Load Funds</h2><p style=color:#22c55e;font-weight:900>Balance: R{user.balance:.2f}</p><div class=tabs><div id='tab-voucher' class='tab active' onclick="showTab('voucher')">🎟️ VOUCHERS</div><div id='tab-payfast' class='tab' onclick="showTab('payfast')">💳 CARD</div><div id='tab-eft' class='tab' onclick="showTab('eft')">🏦 EFT</div></div><div id='voucher' class='tabcontent' style=display:block><form method='post' action='/redeem_voucher'><select name='voucher_type' class=in><option value='BLU'>🔵 Blu</option><option value='1VOUCHER'>🟢 1Voucher</option><option value='OTT'>🟠 OTT</option><option value='MOCHA'>⭐ Mochaina</option></select><input name='code' placeholder='Enter PIN' required minlength=8 class=in style=text-align:center;margin-top:8px><button class=btn-gold>⚡ REDEEM</button></form></div><div id='payfast' class='tabcontent' style=display:none><form method='post' action='/payfast_pay'><input name='amount' type='number' value='50' min='10' max='5000' required class=in><button class=btn-gold>PAYFAST</button></form></div><div id='eft' class='tabcontent' style=display:none><h3 style=color:white>TymeBank 51088331090</h3><p style=color:#9ca3af>Ref: MCHA-{random.randint(100000,999999)}</p><form method='post' action='/load_eft'><button name='amount' value='50' class=btn-dark>R50</button><button name='amount' value='100' class=btn-dark>R100</button></form></div><br><button class=btn-dark onclick="location.href='/menu'">BACK</button></div>""")

@app.route('/redeem_voucher', methods=['POST'])
def redeem_voucher():
    if 'uid' not in session: return redirect('/login')
    code=request.form['code'].strip().replace(" ","").replace("-","")
    vtype=request.form.get('voucher_type','BLU')
    v=Voucher.query.filter_by(code=code.upper()).first()
    if v and not v.is_used:
        user=User.query.get(session['uid']); user.balance+=v.amount; v.is_used=True; v.used_by=user.username; db.session.commit()
        return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#22c55e>✅ R{v.amount} ADDED!</h2><p>Balance: R{user.balance:.2f}</p><button class=btn-gold onclick=\"location.href='/menu'\">MENU</button></div>")
    if len(code)<8:
        return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444>❌ PIN min 8</p><button class=btn-dark onclick=\"location.href='/load'\">Back</button></div>")
    amount=10
    if "1000" in code: amount=1000
    elif "500" in code: amount=500
    elif "200" in code: amount=200
    elif "100" in code: amount=100
    elif "50" in code: amount=50
    user=User.query.get(session['uid'])
    exist=Payment.query.filter_by(ref=f"{vtype}-{code}", status="Pending").first()
    if exist:
        return STYLE+wrap(f"{top_bar()}<div class=form><p>⏳ Already in queue</p><button class=btn-gold onclick=\"location.href='/menu'\">Menu</button></div>")
    p=Payment(user_id=user.id, username=user.username, amount=amount, ref=f"{vtype}-{code}", status="Pending", method=vtype)
    db.session.add(p); db.session.commit()
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>⏳ {vtype} Received!</h2><p>R{amount} verification</p><button class=btn-gold onclick=\"location.href='/menu'\">MENU</button></div>")

@app.route('/load_eft', methods=['POST'])
def load_eft():
    if 'uid' not in session: return redirect('/login')
    try: amt=int(request.form['amount'])
    except: amt=50
    ref=f"MCHA-{random.randint(100000,999999)}"
    p=Payment(user_id=session['uid'], username=session['uname'], amount=amt, ref=ref, method="EFT"); db.session.add(p); db.session.commit()
    return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#facc15>EFT R{amt}</h2><p>Ref: <b>{ref}</b></p><button class=btn-gold onclick=\"location.href='/menu'\">Menu</button></div>")

@app.route('/payfast_pay', methods=['POST'])
def payfast_pay():
    if 'uid' not in session: return redirect('/login')
    try: amount=float(request.form['amount'])
    except: amount=50
    base_url=request.host_url.rstrip('/')
    data={"merchant_id": PAYFAST_MERCHANT_ID,"merchant_key": PAYFAST_MERCHANT_KEY,"return_url": f"{base_url}/payfast_return","cancel_url": f"{base_url}/payfast_cancel","notify_url": f"{base_url}/payfast_notify","m_payment_id": f"{session['uid']}-{random.randint(1000,9999)}","amount": f"{float(amount):.2f}","item_name": "Mochaina Load","custom_str1": session['uname'],"custom_int1": str(session['uid'])}
    pf_str="";
    for k in data: pf_str+=f"{k}={urllib.parse.quote_plus(str(data[k]).strip())}&"
    pf_str=pf_str[:-1]
    if PAYFAST_PASSPHRASE: pf_str+=f"&passphrase={urllib.parse.quote_plus(PAYFAST_PASSPHRASE)}"
    data["signature"]=hashlib.md5(pf_str.encode()).hexdigest()
    form_inputs="".join([f"<input type='hidden' name='{k}' value='{v}'>" for k,v in data.items()])
    return f"<html><body onload='document.forms[0].submit()'><form action='{PAYFAST_URL}' method='post'>{form_inputs}</form></body></html>"

@app.route('/payfast_return')
def payfast_return(): return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#22c55e>✅ Payment Received!</h2><button class=btn-gold onclick=\"location.href='/menu'\">Menu</button></div>")
@app.route('/payfast_cancel')
def payfast_cancel(): return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#ef4444>❌ Cancelled</h2><button class=btn-dark onclick=\"location.href='/load'\">Back</button></div>")
@app.route('/payfast_notify', methods=['POST'])
def payfast_notify():
    try:
        uid=int(request.form.get('custom_int1',0)); amount=float(request.form.get('amount_gross',0))
        if uid and 0<amount<=5000:
            user=User.query.get(uid)
            if user: user.balance+=amount; p=Payment(user_id=uid, username=user.username, amount=int(amount), ref=request.form.get('m_payment_id','PF'), status="Completed", method="PayFast"); db.session.add(p); db.session.commit()
    except: pass
    return "OK", 200

@app.route('/withdraw', methods=['GET','POST'])
def withdraw():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    total_loaded = db.session.query(db.func.sum(Payment.amount)).filter(Payment.user_id==user.id, Payment.status=="Completed", Payment.method!="Withdraw").scalar() or 0
    if request.method=='POST':
        try: amt=int(float(request.form['amount']))
        except: amt=0
        acc=request.form['account'].strip()
        if total_loaded < 20:
            return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#ef4444>❌ Load R20 Real First</h2><p style=color:white;font-size:11px>You loaded R{total_loaded}. Load at least R20 real money before withdraw.</p><button class=btn-gold onclick=\"location.href='/load'\">LOAD R20 NOW</button><br><button class=btn-dark onclick=\"location.href='/menu'\">BACK</button></div>")
        if amt<50 or amt>user.balance or len(acc)<6:
            return STYLE+wrap(f"{top_bar()}<div class=form><p style=color:#ef4444>Invalid - Min R50</p><button class=btn-dark onclick=\"location.href='/withdraw'\">Back</button></div>")
        user.balance-=amt; p=Payment(user_id=user.id, username=user.username, amount=amt, ref=acc, status="Pending", method="Withdraw"); db.session.add(p); db.session.commit()
        return STYLE+wrap(f"{top_bar()}<div class=form><h2 style=color:#22c55e>✅ Withdraw R{amt} pending</h2><button class=btn-gold onclick=\"location.href='/menu'\">Menu</button></div>")
    warn = f"<p style=background:#111;padding:7px;border-radius:6px;color:#fca5a5;font-size:10px;border:1px solid #ef4444>Real loaded: R{total_loaded} / R20 required</p>" if total_loaded < 20 else f"<p style=background:#111;padding:7px;border-radius:6px;color:#86efac;font-size:10px;border:1px solid #22c55e>✅ Real loaded: R{total_loaded} - You can withdraw</p>"
    return STYLE+wrap(f"""{top_bar(user.balance)}<div class=form><h2 style=color:#facc15>WITHDRAW</h2><p style=color:white>Balance R{user.balance:.2f}</p>{warn}<form method='post'><input name='amount' type='number' min='50' max='{int(user.balance)}' required placeholder='Amount min R50' class=in><input name='account' placeholder='Bank acc + name' required class=in><button class=btn-gold>⚡ Withdraw</button></form><button class=btn-dark onclick="location.href='/menu'">BACK</button></div>""")

@app.route('/admin')
def admin():
    if request.args.get('key')!='mochaina123': return STYLE+wrap("<div class=form>Wrong key!</div>")
    pays=Payment.query.filter_by(status="Pending").order_by(Payment.id.desc()).all()
    draws=Draw.query.order_by(Draw.id.desc()).limit(10).all()
    total_users=User.query.count()
    total_bal=db.session.query(db.func.sum(User.balance)).scalar() or 0
    total_in=db.session.query(db.func.sum(Payment.amount)).filter(Payment.status=="Completed", Payment.method!="Withdraw").scalar() or 0
    total_out=db.session.query(db.func.sum(Payment.amount)).filter(Payment.status=="Completed", Payment.method=="Withdraw").scalar() or 0
    profit = total_in - total_out
    today_wins = db.session.query(db.func.sum(WinLog.amount)).filter(WinLog.date.like(f"{datetime.now().strftime('%Y-%m-%d')}%")).scalar() or 0
    ph="".join([f"<div style=text-align:left;padding:7px;border:1px solid #333;margin:4px;border-radius:8px;color:white;font-size:10px>{p.id} {p.username} R{p.amount} {p.method} <a href='/approve/{p.id}?key=mochaina123' style=background:green;color:white;padding:3px 7px;border-radius:6px;text-decoration:none>OK</a> <a href='/reject/{p.id}?key=mochaina123' style=background:red;color:white;padding:3px 7px;border-radius:6px;text-decoration:none>X</a></div>" for p in pays]) or "<p style=color:#9ca3af>No pending</p>"
    dh="".join([f"<div style=text-align:left;padding:7px;border-bottom:1px solid #1f1f1f;display:flex;justify-content:space-between;align-items:center;font-size:10px;color:white><span>{d.date} <b style=color:#facc15>{d.numbers}+W{d.wing}</b></span><a href='/confirm_delete_draw/{d.id}' style=background:#111;color:white;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;text-decoration:none;border:1.5px solid red>❎</a></div>" for d in draws]) or "<p style=color:#9ca3af>No draws</p>"
    return STYLE+wrap(f"""{top_bar()}<div class=form><h2 style=color:#facc15>ADMIN • R{get_jackpot():,.0f}</h2><div style=background:#111;color:white;padding:10px;border-radius:10px;text-align:left;font-size:10px;border:1px solid #2a2a2a><p>👥 Users: {total_users} | 💰 Total Bal: R{total_bal:.2f}</p><p>📥 In: R{total_in} | 📤 Out: R{total_out}</p><p style=color:#22c55e>💵 PROFIT: R{profit} | Today Wins: R{today_wins}</p></div><h3 style=color:#facc15;margin-top:12px;font-size:12px>Pending</h3><div>{ph}</div><h3 style=color:#facc15;margin-top:12px;font-size:12px>Results - Tap ❎ to delete</h3><div>{dh}</div><br><button class=btn-gold style=background:#ef4444 onclick="location.href='/admin_draw/now?key=mochaina123'">DO DRAW NOW</button><br><button class=btn-dark onclick="location.href='/menu'">Menu</button></div>""")

@app.route('/approve/<int:pid>')
def approve(pid):
    if request.args.get('key')!='mochaina123': return "key?"
    p=Payment.query.get(pid)
    if not p or p.status!="Pending": return redirect('/admin?key=mochaina123')
    user=User.query.get(p.user_id)
    if not user: return redirect('/admin?key=mochaina123')
    if p.method!="Withdraw": user.balance+=p.amount
    p.status="Completed"; db.session.commit()
    return redirect('/admin?key=mochaina123')
@app.route('/reject/<int:pid>')
def reject(pid):
    if request.args.get('key')!='mochaina123': return "key?"
    p=Payment.query.get(pid)
    if p and p.status=="Pending":
        if p.method=="Withdraw":
            user=User.query.get(p.user_id)
            if user: user.balance+=p.amount
        p.status="Rejected"; db.session.commit()
    return redirect('/admin?key=mochaina123')
@app.route('/admin_draw/<typ>')
def admin_draw(typ):
    if request.args.get('key')!='mochaina123': return "key?"
    win=sorted(random.sample(range(1,37),4)); wing=random.randint(1,4)
    d=Draw(numbers=",".join(map(str,win)), wing=wing, date=datetime.now().strftime("%Y-%m-%d %H:%M")); db.session.add(d); db.session.commit()
    db.session.query(Ticket).delete(); db.session.commit()
    return redirect('/admin?key=mochaina123')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
