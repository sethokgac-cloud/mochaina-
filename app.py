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

STYLE="""<meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0}.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:400px;margin:15px auto}input,select{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:10px;border:2px solid #e2e8f0}.btn{border:none;padding:12px;border-radius:10px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}.btn-green{background:#16a34a;color:white}.btn-dark{background:#14532d;color:white}.btn-blue{background:#2563eb;color:white}.btn-orange{background:#f97316;color:white}.btn-purple{background:#9333ea;color:white}.btn-red{background:#dc2626;color:white}.btn-gold{background:linear-gradient(90deg,#facc15,#f97316);color:black}.jackpot{background:black;color:gold;font-size:22px;font-weight:900;padding:8px 16px;border-radius:8px;display:inline-block;border:2px solid #facc15}.color-btn{padding:14px 6px;border-radius:12px;border:3px solid white;font-weight:900;font-size:12px;cursor:pointer}.color-btn.selected{border-color:black;transform:scale(1.08)}</style>"""

@app.route('/')
def home():
    if 'uid' in session: return redirect('/menu')
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        user=User.query.filter_by(username=u).first()
        if user and (check_password_hash(user.password, p) or user.password==p):
            session['uid']=user.id; session['uname']=u; return redirect('/menu')
        return STYLE+"<div class=card><p style=color:red>Wrong</p><button class='btn btn-red' onclick=\"location.href='/login'\">Back</button></div>"
    return STYLE+"""<div class=card><h2>LOGIN</h2><form method='post'><input name='username' placeholder='Username' required><input name='password' type='password' required><button class='btn btn-green'>Login</button></form><button class='btn btn-blue' onclick="location.href='/register'">Register</button></div>"""

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        full_name=request.form.get('full_name','').strip()
        p=request.form.get('password','')
        if User.query.filter_by(username=full_name).first():
            return STYLE+"<div class=card>Exists</div>"
        user=User(username=full_name,password=generate_password_hash(p)); db.session.add(user); db.session.commit()
        session['uid']=user.id; session['uname']=full_name; return redirect('/menu')
    return STYLE+"""<div class=card><h2>Register</h2><form method='post'><input name='full_name' placeholder='Full Name' required><input name='password' type='password' placeholder='Password' required><button class='btn btn-gold'>REGISTER</button></form></div>"""

@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><div class=jackpot>R{get_jackpot():,.2f}</div><p style=color:green;font-weight:900>Balance: R{user.balance:.2f}</p><button class='btn btn-green' onclick="location.href='/play'">PLAY LOTTO</button><button class='btn' style=background:linear-gradient(90deg,#ef4444,#9333ea);color:white;padding:18px;margin-top:6px' onclick="location.href='/live'">🔴 LIVE GAMES</button><button class='btn' style=background:gray;color:white onclick="location.href='/logout'">LOGOUT</button></div>"""

@app.route('/live')
def live_games():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🔴 LIVE GAMES</h2><p style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div style="border:2px solid #fde68a;border-radius:16px;padding:14px;margin:10px 0;background:#fffbeb;cursor:pointer" onclick="location.href='/wheel'"><b>🎡 WHEEL - FAST SPIN</b></div><div style="border:2px solid #e2e8f0;border-radius:16px;padding:14px;margin:10px 0;background:white;cursor:pointer" onclick="location.href='/coin'"><b>🪙 COIN</b></div><div style="border:2px solid #e2e8f0;border-radius:16px;padding:14px;margin:10px 0;background:white;cursor:pointer" onclick="location.href='/slots'"><b>🎰 SLOTS</b></div><div style="border:2px solid #e2e8f0;border-radius:16px;padding:14px;margin:10px 0;background:white;cursor:pointer" onclick="location.href='/dice'"><b>🎲 DICE</b></div><button class='btn' style=background:#e2e8f0 onclick="location.href='/menu'">BACK</button></div>"""

# WHEEL - GUARANTEED ROTATE - FAST LIKE REAL WHEEL
@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    cols=["#dc2626","#facc15","#16a34a","#2563eb","#ea580c","#ec4899","#7c3aed","#06b6d4","#16a34a","#facc15","#dc2626","#06b6d4"]
    svg=""
    for i in range(12):
        a1=math.radians(i*30-90); a2=math.radians((i+1)*30-90)
        x1=100+95*math.cos(a1); y1=100+95*math.sin(a1)
        x2=100+95*math.cos(a2); y2=100+95*math.sin(a2)
        svg+=f'<path d="M100,100 L{x1:.1f},{y1:.1f} A95,95 0 0,1 {x2:.1f},{y2:.1f} Z" fill="{cols[i]}" stroke="white" stroke-width="2.5"/>'
    return STYLE+f"""
<div class=card style=background:white;padding:14px>
<h2 style=margin:0;font-weight:900>🎡 WHEEL - FAST SPIN</h2>
<div style=background:#0f172a;color:#facc15;padding:10px;border-radius:12px;font-weight:900;margin:8px 0>⏳ SPIN IN: <span id='countdown'>10</span>s | #<span id='roundNum'>1000</span></div>
<p id='bal' style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p>
<div style=position:relative;width:300px;height:300px;margin:10px auto>
<div style=position:absolute;top:-10px;left:50%;transform:translateX(-50%);font-size:36px;z-index:10>👇</div>
<div id='wheel' style='width:100%;height:100%;border-radius:50%;border:8px solid #facc15;background:white;overflow:hidden;transform:rotate(0deg)'><svg viewBox="0 0 200 200" style=width:100%;height:100%>{svg}<circle cx="100" cy="100" r="20" fill="#0f172a" stroke="white" stroke-width="3"/></svg></div>
</div>
<div id='lastWin' style=font-weight:900>Last: -</div>
<div id='myBetBox' style=background:#fef9c3;padding:8px;border-radius:10px;font-weight:800;margin:6px 0>Next bet: -</div>
<div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px>
<button class='color-btn' style=background:#dc2626;color:white onclick="pick('RED',2,this)">RED x2</button>
<button class='color-btn' style=background:#facc15;color:black onclick="pick('YEL',3,this)">YEL x3</button>
<button class='color-btn' style=background:#16a34a;color:white onclick="pick('GREEN',2.5,this)">GREEN</button>
<button class='color-btn' style=background:#2563eb;color:white onclick="pick('BLUE',2.5,this)">BLUE</button>
<button class='color-btn' style=background:#f97316;color:white onclick="pick('ORG',3,this)">ORG x3</button>
<button class='color-btn' style=background:#ec4899;color:white onclick="pick('PINK',4,this)">PINK x4</button>
<button class='color-btn' style=background:#7c3aed;color:white onclick="pick('PURP',6,this)">PURP x6</button>
<button class='color-btn' style=background:#0891b2;color:white onclick="pick('CYAN',8,this)">CYAN x8</button>
</div>
<div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px>
<button class='btn btn-dark' onclick="setS(2)">R2</button><button class='btn btn-dark' onclick="setS(5)">R5</button><button class='btn btn-dark' onclick="setS(10)">R10</button><button class='btn btn-dark' onclick="setS(20)">R20</button></div>
<input id='stake' type='hidden' value='5'><div id='stakeShow' style=font-size:12px;font-weight:800;margin:6px 0>Stake: R5</div>
<button id='betBtn' class='btn btn-gold' style=opacity:0.5 onclick="placeBet()">PICK COLOR</button>
<button class='btn btn-purple' style=margin-top:8px onclick="doSpin()">🔥 TEST SPIN NOW (if timer stuck)</button>
<div id='winBox' style=font-weight:900;font-size:20px;min-height:28px></div>
<button class='btn' style=background:#e2e8f0;margin-top:8px onclick="location.href='/live'">BACK</button>
<script>
var sel=null, mult=2, timeLeft=10, spinning=false, cr=0;
function setS(v){{document.getElementById('stake').value=v; document.getElementById('stakeShow').innerText='Stake: R'+v; if(sel) enable();}}
function pick(c,m,el){{sel=c; mult=m; document.querySelectorAll('.color-btn').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); enable();}}
function enable(){{var b=document.getElementById('betBtn'); b.style.opacity='1'; b.innerText='LOCK R'+document.getElementById('stake').value+' ON '+sel+' x'+mult;}}
function placeBet(){{if(!sel)return; var s=document.getElementById('stake').value; fetch('/wheel_place_next?color='+sel+'&stake='+s+'&mult='+mult).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);return;}} document.getElementById('myBetBox').innerText='Locked: R'+s+' on '+sel; document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);}});}}
setInterval(function(){{
  if(spinning) return;
  timeLeft--; if(timeLeft<0) timeLeft=0;
  var cd=document.getElementById('countdown');
  if(cd) cd.innerText=timeLeft;
  if(timeLeft<=0) doSpin();
}},1000);
function doSpin(){{
  if(spinning) return;
  spinning=true;
  timeLeft=0;
  document.getElementById('countdown').innerText='0 - SPINNING!';
  var wheel=document.getElementById('wheel');
  fetch('/wheel_spin_next').then(r=>r.json()).then(d=>{{
    var center=d.index*30+15;
    var target=(360-center+360)%360;
    var start=cr;
    var total=1800+target;
    var finalRot=start+total;
    var startTime=null;
    var duration=3500;
    function easeOut(t){{return 1-Math.pow(1-t,4);}}
    function animate(now){{
      if(!startTime) startTime=now;
      var p=Math.min((now-startTime)/duration,1);
      var e=easeOut(p);
      var cur=start+total*e;
      wheel.style.transform='rotate('+cur+'deg)';
      if(p<1) requestAnimationFrame(animate);
      else{{
        cr=finalRot%360;
        wheel.style.transform='rotate('+cr+'deg)';
        document.getElementById('lastWin').innerText='Last: '+d.landed;
        document.getElementById('winBox').innerText=d.win>0?'YOU WON R'+d.win+'!':'LOST - '+d.landed;
        document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);
        timeLeft=10;
        spinning=false;
      }}
    }}
    requestAnimationFrame(animate);
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
    if stake>user.balance: return {"error":"No balance"}
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
    if bet and bet['color']==landed:
        win=round(bet['stake']*bet['mult'],2)
        user.balance+=win
        db.session.commit()
    return {"landed":landed,"index":idx,"win":win,"balance":round(user.balance,2)}

@app.route('/play')
def play(): return STYLE+"<div class=card>PLAY</div>"
@app.route('/coin')
def coin(): return STYLE+f"<div class=card><h2>COIN</h2><button class='btn btn-green' onclick=\"fetch('/wheel_spin_next').then(r=>r.json()).then(d=>alert(d.landed))\">TEST</button><button class='btn' onclick=\"location.href='/live'\">BACK</button></div>"
@app.route('/slots')
def slots(): return STYLE+"<div class=card>SLOTS</div>"
@app.route('/dice')
def dice(): return STYLE+"<div class=card>DICE</div>"
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
