from flask import Flask, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
import random, math, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mochaina_final_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mochaina.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    balance = db.Column(db.Float, default=100.0)

with app.app_context():
    db.create_all()

wheel_bets = {}

STYLE = """<meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0}.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:400px;margin:15px auto}input{width:100%;padding:12px;margin:6px 0;border-radius:10px;border:2px solid #e2e8f0;box-sizing:border-box}.btn{border:none;padding:12px;border-radius:10px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}.btn-green{background:#16a34a;color:white}.btn-gold{background:linear-gradient(90deg,#facc15,#f97316);color:black}.btn-purple{background:#9333ea;color:white}.btn-dark{background:#14532d;color:white}.color-btn{padding:12px 6px;border-radius:12px;border:3px solid white;font-weight:900;font-size:12px;cursor:pointer}.color-btn.selected{border-color:black;transform:scale(1.08)}</style>"""

@app.route('/')
def home():
    if 'uid' in session: return redirect('/menu')
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        user=User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            session['uid']=user.id; session['uname']=u; return redirect('/menu')
        return STYLE+"<div class=card><p style=color:red>Wrong</p><button class='btn' onclick=\"location.href='/login'\">Back</button></div>"
    return STYLE+"""<div class=card><h2>LOGIN</h2><form method='post'><input name='username' placeholder='Username' required><input name='password' type='password' required><button class='btn btn-green'>LOGIN</button></form><button class='btn btn-gold' onclick="location.href='/register'">REGISTER</button></div>"""

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        if User.query.filter_by(username=u).first():
            return STYLE+"<div class=card><p>Exists</p><button onclick=\"location.href='/register'\">Back</button></div>"
        user=User(username=u,password=generate_password_hash(p),balance=100.0)
        db.session.add(user); db.session.commit()
        session['uid']=user.id; session['uname']=u; return redirect('/menu')
    return STYLE+"""<div class=card><h2>REGISTER R100 FREE</h2><form method='post'><input name='username' placeholder='Full Name' required><input name='password' type='password' placeholder='Password' required><button class='btn btn-gold'>REGISTER</button></form></div>"""

@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>⭐ MOCHAINA STAR ⭐</h2><p style=color:green;font-weight:900>Balance: R{user.balance:.2f}</p><button class='btn btn-gold' style=padding:18px onclick="location.href='/live'">🔴 LIVE GAMES - TEST WHEEL</button><button class='btn' style=background:gray;color:white onclick="location.href='/logout'">LOGOUT</button></div>"""

@app.route('/live')
def live():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🔴 LIVE GAMES</h2><p>Balance: R{user.balance:.2f}</p><div style="border:3px solid #facc15;border-radius:16px;padding:16px;margin:12px 0;background:#fffbeb;cursor:pointer" onclick="location.href='/wheel'"><b>🎡 WHEEL - FAST SPIN TEST</b></div><button class='btn' style=background:#e2e8f0 onclick="location.href='/menu'">BACK</button></div>"""

@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    cols=["#dc2626","#facc15","#16a34a","#2563eb","#ea580c","#ec4899","#7c3aed","#06b6d4","#16a34a","#facc15","#dc2626","#06b6d4"]
    labels=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]
    svg=""
    for i in range(12):
        a1=math.radians(i*30-90); a2=math.radians((i+1)*30-90)
        x1=100+95*math.cos(a1); y1=100+95*math.sin(a1)
        x2=100+95*math.cos(a2); y2=100+95*math.sin(a2)
        svg+=f'<path d="M100,100 L{x1:.1f},{y1:.1f} A95,95 0 0,1 {x2:.1f},{y2:.1f} Z" fill="{cols[i]}" stroke="white" stroke-width="2.5"/>'
    return STYLE+f"""
<div class=card>
<h2 style=margin:0>🎡 WHEEL - FAST TEST</h2>
<div style=background:#0f172a;color:#facc15;padding:10px;border-radius:12px;font-weight:900;margin:8px 0>⏳ SPIN IN: <span id='countdown'>10</span>s</div>
<p style=color:#16a34a;font-weight:900 id='bal'>Balance: R{user.balance:.2f}</p>
<div style=position:relative;width:300px;height:300px;margin:10px auto>
<div style=position:absolute;top:-10px;left:50%;transform:translateX(-50%);font-size:36px;z-index:10>👇</div>
<div id='wheel' style='width:100%;height:100%;border-radius:50%;border:8px solid #facc15;background:white;overflow:hidden;transform:rotate(0deg)'><svg viewBox="0 0 200 200" style=width:100%;height:100%>{svg}<circle cx="100" cy="100" r="22" fill="#0f172a" stroke="white" stroke-width="3"/></svg></div>
</div>
<div id='lastWin' style=font-weight:900>Last: -</div>
<div id='myBet' style=background:#fef9c3;padding:8px;border-radius:10px;font-weight:800;margin:6px 0>Next bet: -</div>
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
<button id='betBtn' class='btn btn-gold' style=opacity:0.5 onclick="placeBet()">PICK COLOR FIRST</button>
<button class='btn btn-purple' style=margin-top:8px onclick="doSpin()">🔥 FORCE SPIN NOW</button>
<div id='winBox' style=font-weight:900;font-size:20px;min-height:28px;margin-top:8px></div>
<button class='btn' style=background:#e2e8f0;margin-top:8px onclick="location.href='/live'">BACK</button>
<script>
var sel=null, mult=2, timeLeft=10, spinning=false, cr=0;
function setS(v){{document.getElementById('stake').value=v; document.getElementById('stakeShow').innerText='Stake: R'+v+' on '+(sel||'-'); if(sel) enable();}}
function pick(c,m,el){{sel=c; mult=m; document.querySelectorAll('.color-btn').forEach(b=>b.classList.remove('selected')); el.classList.add('selected'); enable();}}
function enable(){{var b=document.getElementById('betBtn'); b.style.opacity='1'; b.innerText='LOCK R'+document.getElementById('stake').value+' ON '+sel+' x'+mult;}}
function placeBet(){{if(!sel)return; var s=document.getElementById('stake').value; fetch('/wheel_place?color='+sel+'&stake='+s+'&mult='+mult).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);return;}} document.getElementById('myBet').innerText='Locked: R'+s+' on '+sel+' x'+mult; document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);}});}}
setInterval(function(){{if(spinning)return;timeLeft--;if(timeLeft<0)timeLeft=0;document.getElementById('countdown').innerText=timeLeft;if(timeLeft<=0)doSpin();}},1000);
function doSpin(){{
if(spinning)return; spinning=true;
var wheel=document.getElementById('wheel');
fetch('/wheel_spin').then(r=>r.json()).then(d=>{{
var center=d.index*30+15; var target=(360-center+360)%360; var start=cr; var total=1800+target; var finalRot=start+total; var startTime=null; var duration=4000;
function easeOut(t){{return 1-Math.pow(1-t,4);}}
function animate(now){{if(!startTime)startTime=now;var p=Math.min((now-startTime)/duration,1);var cur=start+total*easeOut(p);wheel.style.transform='rotate('+cur+'deg)';if(p<1)requestAnimationFrame(animate);else{{cr=finalRot%360;wheel.style.transform='rotate('+cr+'deg)';document.getElementById('lastWin').innerText='Last: '+d.landed;document.getElementById('winBox').innerText=d.win>0?'WON R'+d.win+'!':'LOST - '+d.landed;document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);timeLeft=10;spinning=false;}}}}
requestAnimationFrame(animate);
}});
}}
</script></div>"""

@app.route('/wheel_place')
def wheel_place():
    if 'uid' not in session: return {"error":"login"}
    uid=session['uid']; user=User.query.get(uid)
    try: stake=int(request.args.get('stake',5))
    except: stake=5
    try: mult=float(request.args.get('mult',2))
    except: mult=2
    color=request.args.get('color','RED')
    if stake>user.balance: return {"error":"No balance"}
    if uid in wheel_bets: user.balance+=wheel_bets[uid]['stake']
    user.balance-=stake
    wheel_bets[uid]={"color":color,"stake":stake,"mult":mult}
    db.session.commit()
    return {"balance":round(user.balance,2)}

@app.route('/wheel_spin')
def wheel_spin():
    if 'uid' not in session: return {"error":"login"}
    uid=session['uid']; user=User.query.get(uid)
    cols=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]
    idx=random.randint(0,11); landed=cols[idx]; win=0
    bet=wheel_bets.pop(uid, None)
    if bet and bet['color']==landed:
        win=round(bet['stake']*bet['mult'],2); user.balance+=win
    db.session.commit()
    return {"landed":landed,"index":idx,"win":win,"balance":round(user.balance,2)}

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
