import os, random
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET','mochaina-limpopo-2026-secret-key')
db_path = os.path.join(os.path.dirname(__file__), 'mochaina.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120))
    id_number = db.Column(db.String(20), unique=True)
    phone = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(200))
    balance = db.Column(db.Float, default=1000.0)
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_type = db.Column(db.String(30))
    numbers = db.Column(db.String(200))
    stake = db.Column(db.Float)
    win = db.Column(db.Float, default=0)
    result = db.Column(db.String(200))
    created = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(phone='admin').first():
        u = User(full_name='Admin', id_number='0000000000000', phone='admin', password_hash=generate_password_hash('admin'), balance=50726.71)
        db.session.add(u)
        db.session.commit()

HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Mochaina Lotto - Limpopo #1</title><style>*{box-sizing:border-box;font-family:Arial,sans-serif}body{margin:0;background:#0a0e1f;color:#fff}.header{background:#0a0e1f;padding:12px;text-align:center;border-bottom:2px solid #ffb700}.header h1{color:#ffb700;margin:0;font-size:28px}.nav{display:flex;gap:8px;justify-content:center;padding:10px;background:#111;flex-wrap:wrap}.nav button{padding:10px 16px;border-radius:20px;border:none;background:#222;color:#fff;font-weight:bold}.nav button.active{background:#ffb700;color:#000}.card{background:#fff;color:#000;border-radius:24px;padding:18px;margin:12px;max-width:500px;margin-left:auto;margin-right:auto}.balance{color:#0a7a2e;font-weight:bold;text-align:center;font-size:18px}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin:12px 0}.grid button{padding:12px 0;border-radius:10px;border:1px solid #ccc;background:#fff;font-weight:bold}.grid button.sel{background:#ffb700;color:#000;border-color:#ffb700}.input-stake{width:100px;margin:0 auto;display:block;padding:10px;border-radius:10px;border:1px solid #ccc;text-align:center;font-size:18px}.btn-green{background:#0a9d4a;color:#fff;border:none;width:100%;padding:14px;border-radius:14px;font-weight:bold;font-size:16px;margin:8px 0}.btn-gold{background:linear-gradient(90deg,#ffb700,#ff6a00);color:#000;border:none;width:100%;padding:14px;border-radius:14px;font-weight:bold;font-size:16px;margin:8px 0}.btn-live{background:#fffbe0;border:1px solid #ffe58f;color:#000;padding:12px;border-radius:14px;width:100%;text-align:left;margin:6px 0;font-weight:bold;display:flex;justify-content:space-between}input[type=text],input[type=password],input[type=number]{width:100%;padding:12px;border-radius:10px;border:1px solid #ddd;margin:6px 0}.small{font-size:12px;color:#666}.result-box{text-align:center;padding:10px;font-weight:bold}.w-badge{background:#eee;padding:6px 12px;border-radius:10px;border:1px solid #ccc}</style></head><body><div class="header"><h1>🏆 MOCHAINA LOTTO</h1><p style="margin:4px;color:#ffb700">Limpopo #1 - Tonight 21:00 Draw</p><div id="balTop" class="balance" style="color:#fff"></div></div><div class="nav"><button id="n-play" class="active" onclick="showTab('play')">PLAY</button><button id="n-live" onclick="showTab('live')">LIVE GAMES 🔴</button><button id="n-history" onclick="showTab('history')">HISTORY</button><button id="n-admin" onclick="showTab('admin')">ADMIN</button><button onclick="logout()">Logout</button></div><div id="auth" class="card"><h2 style="color:#b77900" id="authTitle">Register • Create your account</h2><div id="regFields"><input id="fullName" placeholder="Enter your full name e.g. Thabo Mthembu"><input id="idNumber" placeholder="e.g. 9001015000081"><input id="phone" placeholder="+27 • Enter phone number"><input id="pass" type="password" placeholder="Create a password"><input id="pass2" type="password" placeholder="Confirm your password"><label class="small"><input type="checkbox" id="terms"> I agree to Terms & Conditions • 18+ Only</label><button class="btn-gold" onclick="register()">REGISTER NOW</button><p style="text-align:center">Already have an account? <a href="#" onclick="toggleAuth()">Login</a></p></div><div id="loginFields" style="display:none"><input id="loginPhone" placeholder="Phone or admin"><input id="loginPass" type="password" placeholder="Password"><button class="btn-gold" onclick="login()">LOGIN</button><p style="text-align:center">No account? <a href="#" onclick="toggleAuth()">Register</a></p></div><div id="authMsg" class="small" style="color:red;text-align:center"></div></div><div id="play" class="card" style="display:none"><div class="balance" id="balPlay"></div><p style="text-align:center">Stake (R)</p><input id="stake" class="input-stake" value="10" type="number"><button class="btn-green" onclick="autoPick()">Auto Pick</button><div class="grid" id="numGrid"></div><div style="display:flex;gap:6px;justify-content:center"><button class="w-badge" id="w1" onclick="toggleW('W1')">W1</button><button class="w-badge" id="w2" onclick="toggleW('W2')">W2</button><button class="w-badge" id="w3" onclick="toggleW('W3')">W3</button><button class="w-badge" id="w4" onclick="toggleW('W4')">W4</button></div><div class="result-box"><div>Your 4: <span id="your4">[]</span></div><div>Wing: <span id="wing">-</span></div></div><button class="btn-gold" onclick="placeBet()">PLACE BET</button><div id="betResult" class="result-box"></div></div><div id="live" class="card" style="display:none"><h2 style="text-align:center">🔴 LIVE GAMES 💕</h2><p style="background:#ffe0f0;padding:6px 12px;border-radius:20px;text-align:center;font-size:12px">🎹 Romantic music + low sounds inside</p><div class="balance" id="balLive"></div><audio id="romantic" loop><source src="https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a83a51.mp3?filename=romantic-piano-112199.mp3" type="audio/mpeg"></audio><button class="btn-live" onclick="playLive('coin')">🪙 COIN FLIP <span>▶️</span></button><button class="btn-live" onclick="playLive('wheel')">🎡 WHEEL COLOR <span>▶️</span></button><button class="btn-live" onclick="playLive('slots')">🎰 SLOTS ONE BY ONE <span>▶️</span></button><button class="btn-live" onclick="playLive('dice')">🎲 DICE THROW <span>▶️</span></button><div id="liveResult" class="result-box"></div><button class="btn-green" onclick="document.getElementById('romantic').play()">Play Romantic Music</button><button style="background:#e5e7eb;width:100%;padding:10px;border-radius:10px;border:none;margin-top:8px" onclick="showTab('play')">BACK TO MENU</button></div><div id="history" class="card" style="display:none"><h3>Bet History</h3><div id="histList"></div></div><div id="admin" class="card" style="display:none"><h3>Admin Panel</h3><div id="adminStats"></div><button class="btn-green" onclick="addMoney()">Add R1000 to all users (Test)</button></div><script>
let selected=[];let wSelected=[];let isLogin=false;let user=null;
function buildGrid(){let g=document.getElementById('numGrid');g.innerHTML='';for(let i=1;i<=36;i++){let b=document.createElement('button');b.innerText=i;b.id='n'+i;b.onclick=()=>toggleNum(i);g.appendChild(b);}}buildGrid();
function toggleAuth(){isLogin=!isLogin;document.getElementById('regFields').style.display=isLogin?'none':'block';document.getElementById('loginFields').style.display=isLogin?'block':'none';document.getElementById('authTitle').innerText=isLogin?'Login to Mochaina':'Register • Create your account';}
function toggleNum(n){let idx=selected.indexOf(n);if(idx>-1){selected.splice(idx,1);document.getElementById('n'+n).classList.remove('sel')}else{if(selected.length>=4){alert('Pick only 4 numbers!');return}selected.push(n);document.getElementById('n'+n).classList.add('sel')}document.getElementById('your4').innerText='['+selected.join(',')+']';}
function toggleW(w){let idx=wSelected.indexOf(w);let el=document.getElementById(w.toLowerCase());if(idx>-1){wSelected.splice(idx,1);el.style.background='#eee'}else{wSelected.push(w);el.style.background='#ffb700'}document.getElementById('wing').innerText=wSelected.join(',')||'-';}
function autoPick(){selected=[];document.querySelectorAll('.grid button').forEach(b=>b.classList.remove('sel'));while(selected.length<4){let n=Math.floor(Math.random()*36)+1;if(!selected.includes(n)) toggleNum(n);}}
async function register(){let data={full_name:fullName.value,id_number:idNumber.value,phone:phone.value,password:pass.value,confirm:pass2.value,terms:terms.checked};let r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let j=await r.json();document.getElementById('authMsg').innerText=j.msg;if(j.ok){toggleAuth()}}
async function login(){let data={phone:loginPhone.value,password:loginPass.value};let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let j=await r.json();document.getElementById('authMsg').innerText=j.msg;if(j.ok){user=j.user;startApp();}}
async function checkSession(){let r=await fetch('/api/me');let j=await r.json();if(j.logged){user=j.user;startApp();}}
function startApp(){document.getElementById('auth').style.display='none';showTab('play');updateBal();loadHistory();}
function showTab(t){['play','live','history','admin'].forEach(x=>{document.getElementById(x).style.display='none';document.getElementById('n-'+x).classList.remove('active');});document.getElementById(t).style.display='block';document.getElementById('n-'+t).classList.add('active');if(t=='history') loadHistory();if(t=='admin') loadAdmin();}
function updateBal(){if(!user) return;let txt='Balance: R'+(user.balance).toFixed(2);document.getElementById('balTop').innerText=txt;document.getElementById('balPlay').innerText=txt;document.getElementById('balLive').innerText=txt;}
async function placeBet(){if(selected.length!=4){alert('Pick 4 numbers (1-36)');return}let stake=parseFloat(document.getElementById('stake').value)||10;let r=await fetch('/api/bet',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({numbers:selected,w:wSelected,stake})});let j=await r.json();document.getElementById('betResult').innerHTML=j.msg;if(j.user){user=j.user;updateBal();}loadHistory();}
async function playLive(type){let stake=prompt('Stake amount R?','10');if(!stake) return;let r=await fetch('/api/live',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type, stake:parseFloat(stake)})});let j=await r.json();document.getElementById('liveResult').innerHTML=j.msg;if(j.user){user=j.user;updateBal();}}
async function loadHistory(){let r=await fetch('/api/history');let j=await r.json();let h=document.getElementById('histList');h.innerHTML='';j.forEach(b=>{h.innerHTML+=`<div style="border-bottom:1px solid #eee;padding:6px 0">${b.created} - ${b.game_type} ${b.numbers} R${b.stake} => R${b.win} [${b.result}]</div>`})}
async function loadAdmin(){let r=await fetch('/api/admin/stats');let j=await r.json();document.getElementById('adminStats').innerHTML=`Users: ${j.users} | Total Bets: ${j.bets} | Total Balance: R${j.total_bal.toFixed(2)}`;}
async function addMoney(){await fetch('/api/admin/addmoney',{method:'POST'});alert('Added!');let r=await fetch('/api/me');let j=await r.json();if(j.logged){user=j.user;updateBal();}}
async function logout(){await fetch('/api/logout',{method:'POST'});location.reload();}
checkSession();
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/register', methods=['POST'])
def api_register():
    d=request.json
    if not d.get('terms'): return jsonify(ok=False,msg='Agree to Terms')
    if d['password']!=d['confirm']: return jsonify(ok=False,msg='Passwords no match')
    if User.query.filter_by(phone=d['phone']).first(): return jsonify(ok=False,msg='Phone exists')
    if User.query.filter_by(id_number=d['id_number']).first(): return jsonify(ok=False,msg='ID exists')
    u=User(full_name=d['full_name'],id_number=d['id_number'],phone=d['phone'],password_hash=generate_password_hash(d['password']),balance=1000.0)
    db.session.add(u); db.session.commit()
    return jsonify(ok=True,msg='Registered! Now login')

@app.route('/api/login', methods=['POST'])
def api_login():
    d=request.json
    u=User.query.filter_by(phone=d['phone']).first()
    if not u or not check_password_hash(u.password_hash,d['password']): return jsonify(ok=False,msg='Invalid login')
    session['uid']=u.id
    return jsonify(ok=True,msg='Welcome '+u.full_name,user={'full_name':u.full_name,'balance':u.balance,'phone':u.phone})

@app.route('/api/me')
def api_me():
    uid=session.get('uid')
    if not uid: return jsonify(logged=False)
    u=User.query.get(uid)
    return jsonify(logged=True,user={'full_name':u.full_name,'balance':u.balance,'phone':u.phone})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear(); return jsonify(ok=True)

@app.route('/api/bet', methods=['POST'])
def api_bet():
    uid=session.get('uid')
    if not uid: return jsonify(msg='Login first')
    u=User.query.get(uid)
    d=request.json
    stake=float(d.get('stake',10))
    nums=d.get('numbers',[])
    if u.balance < stake: return jsonify(msg='Insufficient balance R%.2f'%u.balance,user={'balance':u.balance})
    winning=random.sample(range(1,37),4)
    match=len(set(nums)&set(winning))
    win=0
    if match==4: win=stake*500
    elif match==3: win=stake*20
    elif match==2: win=stake*2
    u.balance = u.balance - stake + win
    b=Bet(user_id=u.id,game_type='Lotto 4/36',numbers=str(nums)+' W:'+str(d.get('w',[])),stake=stake,win=win,result=f'Win:{winning} Matched:{match}')
    db.session.add(b); db.session.commit()
    msg=f"Your: {nums} | Draw: {winning} | Matched: {match}/4 | {'WIN R%.2f'%win if win>0 else 'LOST'}"
    return jsonify(msg=msg,user={'full_name':u.full_name,'balance':u.balance})

@app.route('/api/live', methods=['POST'])
def api_live():
    uid=session.get('uid')
    if not uid: return jsonify(msg='Login first')
    u=User.query.get(uid)
    d=request.json
    stake=float(d.get('stake',10))
    if u.balance < stake: return jsonify(msg='No balance',user={'balance':u.balance})
    t=d.get('type'); win=0; res=''
    if t=='coin':
        res=random.choice(['HEAD','TAIL'])
        if random.random()>0.5: win=stake*1.9
    elif t=='wheel':
        colors=['RED','GREEN','BLUE','YELLOW','PURPLE','GOLD']
        res=random.choice(colors)
        if res=='GOLD': win=stake*5
        elif res in ['RED','GREEN']: win=stake*1.5
    elif t=='slots':
        slots=[random.choice(['🍒','🍋','⭐','7️⃣','💎']) for _ in range(3)]
        res=' '.join(slots)
        if len(set(slots))==1: win=stake*10
        elif len(set(slots))==2: win=stake*1.2
    elif t=='dice':
        dice=random.randint(1,6); res=f'Dice {dice}'
        if dice>=5: win=stake*2
        elif dice>=3: win=stake*1.2
    u.balance = u.balance - stake + win
    b=Bet(user_id=u.id,game_type=t.upper(),numbers=str(stake),stake=stake,win=win,result=res)
    db.session.add(b); db.session.commit()
    msg=f"{t.upper()} -> {res} | {'WIN R%.2f'%win if win>0 else 'LOST R%.2f'%stake}"
    return jsonify(msg=msg,user={'balance':u.balance})

@app.route('/api/history')
def api_history():
    uid=session.get('uid')
    if not uid: return jsonify([])
    bets=Bet.query.filter_by(user_id=uid).order_by(Bet.id.desc()).limit(50).all()
    return jsonify([{'game_type':b.game_type,'numbers':b.numbers,'stake':b.stake,'win':b.win,'result':b.result,'created':b.created.strftime('%Y-%m-%d %H:%M')} for b in bets])

@app.route('/api/admin/stats')
def admin_stats():
    users=User.query.count(); bets=Bet.query.count(); total=db.session.query(db.func.sum(User.balance)).scalar() or 0
    return jsonify(users=users,bets=bets,total_bal=total)

@app.route('/api/admin/addmoney', methods=['POST'])
def admin_add():
    for u in User.query.all(): u.balance+=1000
    db.session.commit(); return jsonify(ok=True)

if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port)
