from flask import Flask, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
import random, json, os, hashlib, urllib.parse, math
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
app.secret_key = 'mochaina_business_pro_2026_final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mochaina_pwa.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def safe_init():
    with app.app_context():
        db.create_all()
        try:
            if not os.path.exists("static"): os.makedirs("static")
            if not os.path.exists("static/manifest.json"):
                with open("static/manifest.json","w") as f: json.dump({"name":"Mochaina Star","short_name":"Mochaina","start_url":"/","display":"standalone","background_color":"#020617","theme_color":"#facc15"}, f)
            if not os.path.exists("static/sw.js"):
                with open("static/sw.js","w") as f: f.write("self.addEventListener('fetch', e=>{});")
            if not os.path.exists("jackpot.json"):
                with open("jackpot.json","w") as f: json.dump({"amount":500000.0}, f)
            if Voucher.query.count()==0:
                for i in range(1,6): db.session.add(Voucher(code=f"MOCHA-10-TEST0{i}", amount=10))
                for i in range(1,4): db.session.add(Voucher(code=f"MOCHA-50-TEST0{i}", amount=50))
                db.session.commit()
        except Exception as e: print(e)

PAYFAST_MERCHANT_ID = "10000100"
PAYFAST_MERCHANT_KEY = "46f0cd694581a"
PAYFAST_PASSPHRASE = ""
PAYFAST_URL = "https://www.payfast.co.za/eng/process"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    balance = db.Column(db.Float, default=100.0)
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

safe_init()
wheel_next_bets = {}

def get_jackpot():
    try:
        with open("jackpot.json","r") as jf: return float(json.load(jf).get("amount",500000.0))
    except: return 500000.0
def save_jackpot(a):
    try:
        tmp="jackpot.json.tmp"
        with open(tmp,"w") as jf: json.dump({"amount":float(a)}, jf)
        os.replace(tmp, "jackpot.json")
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
        last_file="last_draw.txt"
        now=datetime.now()
        last=None
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
                tickets=Ticket.query.all(); won=False
                for tick in tickets:
                    user=User.query.get(tick.user_id)
                    if not user: continue
                    try: nums=list(map(int,tick.numbers.split(',')))
                    except: continue
                    matches=len(set(nums)&set(win)); w_match=(tick.wing==wing); prize=0
                    if matches==4 and w_match: prize=get_jackpot(); won=True
                    elif matches==4: prize=tick.bet*100
                    elif matches==3 and w_match: prize=tick.bet*50
                    elif matches==3: prize=tick.bet*10
                    elif matches==2 and w_match: prize=tick.bet*5
                    if prize>0: user.balance+=prize
                if won: save_jackpot(500000.0)
                db.session.query(Ticket).delete(); db.session.commit()
            with open(last_file,"w") as f: f.write(now.isoformat())
        else:
            if not os.path.exists(last_file):
                with open(last_file,"w") as f: f.write(now.isoformat())
    except Exception as e: print(e)

STYLE="""<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="manifest" href="/static/manifest.json"><meta name="theme-color" content="#facc15"><script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/static/sw.js')}</script><style>body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0}.header{padding:15px}.header h1{color:#facc15;font-size:26px;font-weight:900;margin:0}.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:400px;margin:15px auto}input,select{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:10px;border:2px solid #e2e8f0}.btn{border:none;padding:12px;border-radius:10px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}.btn-green{background:#16a34a;color:white}.btn-dark{background:#14532d;color:white}.btn-blue{background:#2563eb;color:white}.btn-orange{background:#f97316;color:white}.btn-purple{background:#9333ea;color:white}.btn-red{background:#dc2626;color:white}.btn-gold{background:linear-gradient(90deg,#facc15,#f97316);color:black}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin:10px 0}.num-btn{padding:10px;background:white;border:2px solid #e2e8f0;border-radius:8px;font-weight:700}.num-btn.selected{background:#86efac;border-color:#16a34a}.wing-btn{padding:10px 15px;background:white;border:2px solid #e2e8f0;border-radius:8px;margin:2px}.wing-btn.selected{background:#fde047;border-color:#eab308}.jackpot{background:black;color:gold;font-size:22px;font-weight:900;padding:8px 16px;border-radius:8px;display:inline-block;border:2px solid #facc15}.timer-box{background:#fee2e2;color:#dc2626;font-weight:900;padding:8px 12px;border-radius:10px;display:inline-block;margin:6px 0;white-space:nowrap;letter-spacing:1px;font-family:monospace;font-size:16px;border:1px solid #fecaca}.tabs{display:flex;gap:4px;margin:10px 0}.tab{flex:1;padding:8px;background:#e2e8f0;border-radius:8px;cursor:pointer;font-weight:700;font-size:10px}.tab.active{background:#2563eb;color:white}.tabcontent{border:1px solid #eee;padding:10px;border-radius:10px}.install-banner{background:#facc15;color:black;padding:10px;border-radius:10px;margin:10px;font-weight:900;display:none}.game-card{border:2px solid #fde68a;border-radius:16px;padding:14px;margin:10px 0;background:linear-gradient(135deg,#fffbeb,#fef3c7);cursor:pointer;text-align:left;color:#000}.reel-box{width:80px;height:90px;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.2);border:3px solid white;display:flex;align-items:center;justify-content:center}.reel{font-size:42px;font-weight:900;transition:0.1s}.reel.spinning{filter:blur(3px);transform:scaleY(1.2)}.table{background:#0f172a;border-radius:20px;height:340px;position:relative;overflow:hidden}.dice{width:68px;height:68px;background:linear-gradient(145deg,#fff,#f1e9de);border-radius:14px;position:absolute;left:50%;bottom:40px;transform:translateX(-50%);display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);padding:7px;gap:2px;box-shadow:0 8px 20px rgba(0,0,0,0.6);z-index:20;border:2px solid #e8dcc8;opacity:0}.dice2{z-index:21}.dot{width:11px;height:11px;background:#0f172a;border-radius:50%;justify-self:center;align-self:center}.hidden{visibility:hidden}.hand{position:absolute;bottom:25px;left:50%;transform:translateX(-50%);font-size:82px;z-index:10}@keyframes throw1{0%{bottom:45px;transform:translateX(-50%) rotate(0deg) scale(0.5);opacity:0}30%{bottom:190px;transform:translateX(-75px) rotate(360deg) scale(1.2);opacity:1}60%{bottom:245px;transform:translateX(-85px) rotate(720deg) scale(1.1);opacity:1}100%{bottom:115px;transform:translateX(-78px) rotate(1080deg) scale(1);opacity:1}}@keyframes throw2{0%{bottom:45px;transform:translateX(-50%) rotate(0deg) scale(0.5);opacity:0}35%{bottom:200px;transform:translateX(30px) rotate(-360deg) scale(1.2);opacity:1}65%{bottom:255px;transform:translateX(38px) rotate(-720deg) scale(1.1);opacity:1}100%{bottom:115px;transform:translateX(28px) rotate(-1080deg) scale(1);opacity:1}}@keyframes handOut{0%{transform:translateX(-50%) scale(1);opacity:1}100%{transform:translateX(-50%) translateY(130px) scale(0.3);opacity:0}}.throw1{animation:throw1 1.5s cubic-bezier(0.2,0.8,0.3,1) forwards}.throw2{animation:throw2 1.6s cubic-bezier(0.2,0.8,0.3,1) forwards}.handThrow{animation:handOut 0.5s ease 0.3s forwards}.coinBox{height:280px;background:radial-gradient(at center,#1e293b,#020617);border-radius:20px;display:flex;align-items:center;justify-content:center;border:3px solid #1e293b;perspective:800px}.coin{width:150px;height:150px;border-radius:50%;background:linear-gradient(145deg,#facc15,#f97316);display:flex;align-items:center;justify-content:center;font-size:55px;font-weight:900;color:#000;box-shadow:0 0 30px #facc15aa,inset 0 0 20px #fff8;border:4px solid #fde047}.color-btn{padding:14px 6px;border-radius:12px;border:3px solid white;font-weight:900;font-size:12px;cursor:pointer;transition:0.2s}.color-btn.selected{border-color:black;transform:scale(1.05);box-shadow:0 6px 15px rgba(0,0,0,0.4)}.music-tag{background:linear-gradient(90deg,#fce7f3,#f5d0fe);color:#831843;padding:6px 12px;border-radius:20px;font-size:11px;font-weight:900;display:inline-block;margin-bottom:8px;border:1px solid #f9a8d4}</style><script>let sel=[];let w=null;function toggle(n,el){if(sel.includes(n)){sel=sel.filter(x=>x!=n);el.classList.remove('selected')}else{if(sel.length<4){sel.push(n);el.classList.add('selected')}}document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}function pickWing(n,el){w=n;document.querySelectorAll('.wing-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');document.getElementById('yourW').innerText='Wing: W'+n;document.getElementById('wing_input').value=n;}function autoPick(){sel=[];document.querySelectorAll('.num-btn').forEach(b=>b.classList.remove('selected'));let nums=[];while(nums.length<4){let r=Math.floor(Math.random()*36)+1;if(!nums.includes(r))nums.push(r)}nums.forEach(n=>{sel.push(n);document.getElementById('btn'+n).classList.add('selected')});let rw=Math.floor(Math.random()*4)+1;pickWing(rw,document.getElementById('wbtn'+rw));document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}function showTab(t){document.querySelectorAll('.tabcontent').forEach(c=>c.style.display='none');document.getElementById(t).style.display='block';document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');}function dots(n){let m={1:[[1,1]],2:[[0,0],[2,2]],3:[[0,0],[1,1],[2,2]],4:[[0,0],[0,2],[2,0],[2,2]],5:[[0,0],[0,2],[1,1],[2,0],[2,2]],6:[[0,0],[0,2],[1,0],[1,2],[2,0],[2,2]]};let p={};m[n].forEach(a=>p[a[0]+'-'+a[1]]=1);let h='';for(let r=0;r<3;r++){for(let c=0;c<3;c++){h+=p[r+'-'+c]?'<div class="dot"></div>':'<div class="dot hidden"></div>';}}return h;}function setDice(id,n){let el=document.getElementById(id);if(el)el.innerHTML=dots(n);}</script>"""

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
        return STYLE+"<div class=card><p style=color:red>Wrong login</p><button class='btn btn-red' onclick=\"location.href='/login'\">Back</button></div>"
    return STYLE+"""<div class=header><h1 style=color:#facc15>⭐ Mochaina Lotto 🇿🇦</h1></div><div class=card><h2>LOGIN</h2><form method='post'><input name='username' placeholder='Username' required><input name='password' type='password' placeholder='Password' required><button class='btn btn-green'>Login</button></form><button class='btn btn-blue' onclick="location.href='/register'">Register R100 FREE</button></div>"""

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        try:
            full_name=request.form.get('full_name','').strip()
            p=request.form.get('password',''); p2=request.form.get('confirm_password','')
            if p2 and p!=p2:
                return STYLE+"<div class=card><p style=color:red>❌ Passwords don't match</p><button class='btn btn-red' onclick=\"location.href='/register'\">Back</button></div>"
            if User.query.filter_by(username=full_name).first():
                return STYLE+"<div class=card><p>Exists</p><button onclick=\"location.href='/register'\">Back</button></div>"
            user=User(username=full_name,password=generate_password_hash(p)); db.session.add(user); db.session.commit()
            session['uid']=user.id; session['uname']=full_name; return redirect('/menu')
        except: return STYLE+"<div class=card><p>Error</p></div>"
    return STYLE+"""<div class=card><h2>Register</h2><form method='post'><input name='full_name' placeholder='Full Name' required><input name='password' type='password' placeholder='Password' required><input name='confirm_password' type='password' placeholder='Confirm' required><button class='btn btn-gold'>REGISTER NOW</button></form><p>Have account? <a href='/login'>Login</a></p></div>"""

@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    try: auto_draw_if_due()
    except: pass
    user=User.query.get(session['uid'])
    if not user: session.clear(); return redirect('/login')
    return STYLE+f"""<div class=header><h1>⭐ MOCHAINA STAR ⭐</h1><p>Welcome {session['uname']}</p></div><div class=card><div class=jackpot>R{get_jackpot():,.2f}</div><p style=color:green;font-weight:900>Balance: R{user.balance:.2f}</p><button class='btn btn-green' onclick="location.href='/play'">1. PLAY LOTTO</button><button class='btn btn-blue' onclick="location.href='/load'">3. LOAD FUNDS</button><button class='btn' style=background:linear-gradient(90deg,#ef4444,#9333ea);color:white;padding:18px;margin-top:6px' onclick="location.href='/live'">7. 🔴 LIVE GAMES</button><button class='btn' style=background:gray;color:white onclick="location.href='/logout'">LOGOUT</button></div>"""

@app.route('/live')
def live_games():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🔴 LIVE GAMES</h2><p style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div class='game-card' onclick="location.href='/wheel'" style=border-left:6px solid #9333ea><b>🎡 WHEEL - BET WHILE SPIN (NEW)</b></div><div class='game-card' onclick="location.href='/coin'"><b>🪙 COIN FLIP</b></div><div class='game-card' onclick="location.href='/slots'"><b>🎰 SLOTS</b></div><div class='game-card' onclick="location.href='/dice'"><b>🎲 DICE</b></div><button class='btn' style=background:#e2e8f0;color:#475569;margin-top:16px onclick="location.href='/menu'">BACK</button></div>"""

# ===== FIXED WHEEL - EXACT LIKE SCREENSHOT - ROTATING + BET WHILE SPIN =====
@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    cols = ["#dc2626","#facc15","#16a34a","#2563eb","#ea580c","#ec4899","#7c3aed","#06b6d4","#16a34a","#facc15","#dc2626","#06b6d4"]
    svg=""
    for i in range(12):
        a1=math.radians(i*30-90); a2=math.radians((i+1)*30-90)
        x1=100+95*math.cos(a1); y1=100+95*math.sin(a1)
        x2=100+95*math.cos(a2); y2=100+95*math.sin(a2)
        svg+=f'<path d="M100,100 L{x1:.1f},{y1:.1f} A95,95 0 0,1 {x2:.1f},{y2:.1f} Z" fill="{cols[i]}" stroke="white" stroke-width="2.5"/>'
    return STYLE+f"""
<style>
@keyframes idleRoll {{ from{{transform:rotate(0deg)}} to{{transform:rotate(360deg)}} }}
.wheel-idle {{ animation: idleRoll 10s linear infinite; }}
.wheel-glow {{ box-shadow: 0 0 35px #facc1599, 0 0 70px #facc1544; }}
</style>
<div class=card style=background:white;padding:14px>
<h2 style=margin:4px 0 0 0;font-weight:900;font-size:20px>🎡 WHEEL - BET WHILE SPIN</h2>
<div style=font-size:24px;margin:0 0 6px 0>⚡</div>

<div style=background:#0f172a;color:#facc15;padding:12px;border-radius:14px;font-weight:900;font-size:17px;line-height:1.3>
⏳ BET NEXT: <span id='countdown'>11</span>s | #<span id='roundNum'>{random.randint(1000000000,1999999999)}</span>
</div>

<div id='greenBox' style=background:#dcfce7;color:#166534;padding:10px;border-radius:12px;margin:10px 0;font-weight:800;font-size:13px>
✅ BET FOR NEXT WHILE SPINNING! <span id='left2'>11</span>s left
</div>

<p id='bal' style=color:#16a34a;font-weight:900;margin:8px 0>Balance: R{user.balance:.2f}</p>

<div style=position:relative;width:300px;height:300px;margin:12px auto>
<div style=position:absolute;top:-8px;left:50%;transform:translateX(-50%);font-size:38px;z-index:20>👇</div>
<div id='wheelWrap' class='wheel-idle wheel-glow' style='width:100%;height:100%;border-radius:50%;border:8px solid #facc15;background:white;overflow:hidden'><svg viewBox="0 0 200 200" style=width:100%;height:100%>{svg}<circle cx="100" cy="100" r="24" fill="#0f172a" stroke="white" stroke-width="3"/><circle cx="100" cy="100" r="12" fill="#facc15"/></svg></div>
</div>

<div id='lastWin' style=font-weight:900;margin:8px 0>Last: -</div>
<div id='myBetBox' style=background:#fef9c3;padding:8px;border-radius:10px;font-weight:800;margin:6px 0;font-size:13px>Next bet: -</div>

<div style=text-align:left;font-weight:900;font-size:12px;margin:10px 0 6px 0>BET FOR NEXT WHILE SPINNING:</div>
<div style=display:grid;grid-template-columns:repeat(4,1fr);gap:7px>
<button class='color-btn' style=background:#dc2626;color:white;border-radius:10px;padding:12px 4px onclick="pickColor('RED',2,this)">🔴 RED x2</button>
<button class='color-btn' style=background:#fef9c3;color:#000;border:2px solid #facc15;border-radius:10px;padding:12px 4px onclick="pickColor('YEL',3,this)">🟡 YEL x3</button>
<button class='color-btn' style=background:#16a34a;color:white;border-radius:10px;padding:12px 4px;border:2px solid black onclick="pickColor('GREEN',2.5,this)">🟢 GREEN x2.5</button>
<button class='color-btn' style=background:#3b82f6;color:white;border-radius:10px;padding:12px 4px onclick="pickColor('BLUE',2.5,this)">🔵 BLUE x2.5</button>
<button class='color-btn' style=background:#f97316;color:white;border-radius:10px;padding:10px 4px onclick="pickColor('ORG',3,this)">ORG x3</button>
<button class='color-btn' style=background:#ec4899;color:white;border-radius:10px;padding:10px 4px onclick="pickColor('PINK',4,this)">PINK x4</button>
<button class='color-btn' style=background:#7c3aed;color:white;border-radius:10px;padding:10px 4px onclick="pickColor('PURP',6,this)">PURP x6</button>
<button class='color-btn' style=background:#0891b2;color:white;border-radius:10px;padding:10px 4px onclick="pickColor('CYAN',8,this)">CYAN x8</button>
</div>

<div style=display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px>
<button class='btn btn-dark' onclick="setStake(2)">R2</button><button class='btn btn-dark' onclick="setStake(5)">R5</button><button class='btn btn-dark' onclick="setStake(10)">R10</button><button class='btn btn-dark' onclick="setStake(20)">R20</button></div>
<input id='stake' type='hidden' value='5'><div id='stakeShow' style=text-align:left;font-size:13px;font-weight:800;margin:6px 0>Stake: R5</div>
<button id='betBtn' class='btn btn-gold' style=padding:16px;font-size:15px;opacity:0.5;pointer-events:none onclick="placeBet()">PICK COLOR</button>
<div id='winBox' style=font-weight:900;font-size:22px;min-height:28px;margin-top:8px></div>
<button class='btn' style=background:#e2e8f0;color:#475569;margin-top:8px onclick="location.href='/live'">BACK</button>
<script>
let sel=null, selMult=2, roundId=parseInt(document.getElementById('roundNum').innerText), timeLeft=11, spinning=false, cr=0;
function setStake(v){{document.getElementById('stake').value=v; document.getElementById('stakeShow').innerText='Stake: R'+v; if(sel) enableBet();}}
function pickColor(c,m,el){{sel=c; selMult=m; document.querySelectorAll('.color-btn').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); document.getElementById('stakeShow').innerText='Stake: R'+document.getElementById('stake').value+' on '+c+' x'+m; enableBet();}}
function enableBet(){{let b=document.getElementById('betBtn'); b.style.opacity='1'; b.style.pointerEvents='auto'; b.innerText=spinning?'BET R'+document.getElementById('stake').value+' ON '+sel+' FOR #'+(roundId+1)+' WHILE ROLLING!':'LOCK R'+document.getElementById('stake').value+' ON '+sel+' x'+selMult+' FOR #'+roundId;}}
function placeBet(){{if(!sel)return; let s=document.getElementById('stake').value; fetch('/wheel_place_next?color='+sel+'&stake='+s+'&mult='+selMult).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);return;}} document.getElementById('myBetBox').innerText='Locked #'+(spinning?roundId+1:roundId)+': R'+s+' on '+sel+' x'+selMult; document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2); document.getElementById('betBtn').style.opacity='0.5'; document.getElementById('betBtn').style.pointerEvents='none';}});}}
setInterval(function(){{
  if(!spinning){{
    timeLeft--; if(timeLeft<0) timeLeft=0;
    document.getElementById('countdown').innerText=timeLeft;
    document.getElementById('left2').innerText=timeLeft;
    if(timeLeft<=0) doSpin();
  }} else {{
    timeLeft--; if(timeLeft<0) timeLeft=0;
    document.getElementById('countdown').innerText=timeLeft;
    document.getElementById('left2').innerText=timeLeft;
  }}
}},1000);
function doSpin(){{
  spinning=true;
  let wrap=document.getElementById('wheelWrap');
  wrap.classList.remove('wheel-idle');
  wrap.style.transform='rotate('+cr+'deg)';
  document.getElementById('greenBox').innerHTML='⚡ ROLLING... BET FOR NEXT #'+(roundId+1)+' NOW OPEN!';
  fetch('/wheel_spin_next?round='+roundId).then(r=>r.json()).then(d=>{{
    let center=d.index*30+15; let target=(360-center+360)%360;
    let finalRot=cr+1080+target;
    wrap.style.transition='transform 3.5s cubic-bezier(0.1,0.85,0.2,1)';
    wrap.style.transform='rotate('+finalRot+'deg)';
    roundId++; document.getElementById('roundNum').innerText=roundId; timeLeft=11;
    setTimeout(function(){{
      cr=finalRot%360;
      wrap.style.transition='none';
      wrap.style.transform='rotate('+cr+'deg)';
      setTimeout(function(){{ wrap.classList.add('wheel-idle'); }},100);
      document.getElementById('lastWin').innerText='Last: '+d.landed;
      document.getElementById('winBox').innerText=d.win>0?'YOU WON R'+d.win+'! 🎉':'LOST — '+d.landed;
      document.getElementById('winBox').style.color=d.win>0?'#16a34a':'#ef4444';
      document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);
      document.getElementById('greenBox').innerHTML='✅ BET FOR NEXT WHILE SPINNING! '+timeLeft+'s left';
      spinning=false;
    }},3600);
  }});
}}
</script></div>"""

@app.route('/wheel_place_next')
def wheel_place_next():
    if 'uid' not in session: return {"error":"login"}
    uid=session['uid']; user=User.query.get(uid)
    try: stake=int(float(request.args.get('stake',5)))
    except: stake=5
    try: mult=float(request.args.get('mult',2))
    except: mult=2
    color=request.args.get('color','RED').upper()
    if color not in ["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN"]: return {"error":"color"}
    if stake<=0 or stake>1000: return {"error":"stake"}
    if stake>user.balance: return {"error":"No balance R%.2f"%user.balance}
    if uid in wheel_next_bets:
        user.balance+=wheel_next_bets[uid]['stake']
    user.balance-=stake
    wheel_next_bets[uid]={"color":color,"stake":stake,"mult":mult}
    db.session.commit()
    return {"balance":round(user.balance,2)}

@app.route('/wheel_spin_next')
def wheel_spin_next():
    if 'uid' not in session: return {"error":"login"}
    uid=session['uid']; user=User.query.get(uid)
    colors12=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]
    idx=random.randint(0,11)
    landed=colors12[idx]
    win=0
    bet=wheel_next_bets.pop(uid, None)
    if bet:
        if bet['color']==landed or (bet['color']=="YEL" and landed=="YEL") or (bet['color']=="RED" and landed=="RED"):
            win=round(bet['stake']*bet['mult'],2)
            user.balance+=win
        db.session.commit()
    return {"landed":landed,"index":idx,"win":win,"balance":round(user.balance,2)}

@app.route('/slots')
def slots():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🎰 SLOTS</h2><p>Balance: R{user.balance:.2f}</p><div style=background:#0f172a;padding:18px;border-radius:20px;display:flex;justify-content:center;gap:10px><div class='reel-box'><div id='r1' class='reel'>🍒</div></div><div class='reel-box'><div id='r2' class='reel'>🍋</div></div><div class='reel-box'><div id='r3' class='reel'>🔔</div></div></div><div id='slot_res' style=font-weight:900;margin:12px 0></div><div id='slot_win' style=font-weight:900;font-size:24px></div><input id='slot_stake' type='hidden' value='1'><button class='btn btn-blue' onclick="spinSlot()">SPIN</button><button class='btn' style=background:#e2e8f0 onclick="location.href='/live'">BACK</button></div><script>let slotSymbols=["🍒","🍋","🔔","7️⃣","⭐","💎"];function spinSlot(){{let stake=document.getElementById('slot_stake').value;fetch('/slots_spin?stake='+stake).then(r=>r.json()).then(d=>{{document.getElementById('r1').innerText=d.reels[0];document.getElementById('r2').innerText=d.reels[1];document.getElementById('r3').innerText=d.reels[2];document.getElementById('slot_res').innerText=d.msg;}});}}</script>"""

@app.route('/slots_spin')
def slots_spin():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',1)))
    except: stake=1
    if stake>user.balance: return {"reels":["❌","❌","❌"],"msg":"No balance","win":0,"balance":user.balance}
    user.balance-=stake; symbols=["🍒","🍋","🔔","7️⃣","⭐","💎"]; win=0
    if random.random()<0.7:
        reels=[random.choice(symbols) for _ in range(3)]
        msg=" ".join(reels)
    else:
        reels=[random.choice(symbols) for _ in range(3)]
        if reels[0]==reels[1]==reels[2]: win=stake*10; msg=f"JACKPOT {reels[0]} R{win}"
        else: reels[1]=reels[0]; win=stake*2; msg=f"Win R{win}"
    if win>0: user.balance+=win
    db.session.commit()
    return {"reels":reels,"msg":msg,"win":win,"balance":round(user.balance,2)}

@app.route('/coin')
def coin_page():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"<div class=card><h2>COIN</h2><p>Balance R{user.balance:.2f}</p><button class='btn btn-green' onclick=\"fetch('/coin_flip?choice=heads&stake=2').then(r=>r.json()).then(d=>{{alert(d.result+' win '+d.win);location.reload()}})\">HEADS</button><button class='btn btn-blue' onclick=\"fetch('/coin_flip?choice=tails&stake=2').then(r=>r.json()).then(d=>{{alert(d.result+' win '+d.win);location.reload()}})\">TAILS</button><button class='btn' onclick=\"location.href='/live'\">BACK</button></div>"

@app.route('/coin_flip')
def coin_flip():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',2)))
    except: stake=2
    choice=request.args.get('choice','heads')
    if stake>user.balance: return {"error":"No balance","result":"none","win":0}
    result=random.choice(['heads','tails'])
    user.balance-=stake; win=0
    if result==choice: win=round(stake*1.9,2); user.balance+=win
    db.session.commit(); return {"result":result,"win":win}

@app.route('/dice')
def dice_page():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"<div class=card><h2>DICE</h2><p>Balance R{user.balance:.2f}</p><button class='btn btn-green' onclick=\"fetch('/dice_roll?choice=low&stake=2').then(r=>r.json()).then(d=>{{alert(d.msg);location.reload()}})\">LOW</button><button class='btn btn-blue' onclick=\"fetch('/dice_roll?choice=high&stake=2').then(r=>r.json()).then(d=>{{alert(d.msg);location.reload()}})\">HIGH</button><button class='btn' onclick=\"location.href='/live'\">BACK</button></div>"

@app.route('/dice_roll')
def dice_roll():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',2)))
    except: stake=2
    choice=request.args.get('choice','low')
    if stake>user.balance: return {"roll":0,"msg":"No bal","win":0,"d1":1,"d2":1}
    rn=random.randint(0,100); win=0
    if 40<=rn<=60: user.balance-=stake; msg=f"HOUSE {rn} LOSE"
    elif (choice=='low' and rn<=39) or (choice=='high' and rn>=61): win=stake*2; user.balance+=win-stake; msg=f"WON R{win} Roll {rn}"
    else: user.balance-=stake; msg=f"LOST Roll {rn}"
    db.session.commit(); return {"roll":rn,"msg":msg,"win":win,"d1":1,"d2":2}

@app.route('/play')
def play():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    grid="".join([f"<button id='btn{i}' class='num-btn' onclick='toggle({i},this)'>{i}</button>" for i in range(1,37)])
    return STYLE+f"""<div class=card><div class=grid>{grid}</div><button id='wbtn1' class='wing-btn' onclick='pickWing(1,this)'>W1</button><button id='wbtn2' class='wing-btn' onclick='pickWing(2,this)'>W2</button><button id='wbtn3' class='wing-btn' onclick='pickWing(3,this)'>W3</button><button id='wbtn4' class='wing-btn' onclick='pickWing(4,this)'>W4</button><p id='your4'></p><p id='yourW'></p><form method='post' action='/buy'><input type='hidden' name='numbers' id='nums_input'><input type='hidden' name='wing' id='wing_input'><input type='hidden' name='bet' id='bet_hidden' value='10'><button class='btn btn-gold' onclick="document.getElementById('bet_hidden').value='10'">PLACE BET</button></form><button class='btn' onclick="location.href='/menu'">BACK</button></div>"""

@app.route('/buy', methods=['POST'])
def buy():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try:
        nums_str=request.form['numbers']; wing=int(request.form['wing']); bet=int(float(request.form['bet']))
        nums=list(map(int, nums_str.split(',')))
        if len(nums)!=4: raise ValueError
    except: return STYLE+"<div class=card>Pick 4</div>"
    if bet>user.balance: return STYLE+"<div class=card>No bal</div>"
    user.balance-=bet; save_jackpot(get_jackpot()+bet*0.1)
    t=Ticket(user_id=user.id, username=user.username, numbers=nums_str, wing=wing, bet=bet); db.session.add(t); db.session.commit()
    return STYLE+f"<div class=card>Ticket #{t.id}<button onclick=\"location.href='/menu'\">MENU</button></div>"

@app.route('/load')
def load_funds():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"<div class=card><h2>LOAD</h2><p>R{user.balance:.2f}</p><form method='post' action='/redeem_voucher'><input name='code' placeholder='Voucher'><select name='voucher_type'><option>BLU</option></select><button class='btn btn-green'>REDEEM</button></form><button class='btn' onclick=\"location.href='/menu'\">BACK</button></div>"

@app.route('/redeem_voucher', methods=['POST'])
def redeem_voucher():
    if 'uid' not in session: return redirect('/login')
    code=request.form['code'].strip().upper().replace(" ","").replace("-","")
    v=Voucher.query.filter_by(code=code).first()
    if v and not v.is_used:
        user=User.query.get(session['uid']); user.balance+=v.amount; v.is_used=True; v.used_by=user.username; db.session.commit()
        return STYLE+f"<div class=card>✅ R{v.amount}<button onclick=\"location.href='/menu'\">MENU</button></div>"
    return STYLE+"<div class=card>Invalid</div>"

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
