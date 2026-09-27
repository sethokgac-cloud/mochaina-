from flask import Flask, request, session, redirect, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
import random, json, os, math, sqlite3, threading, time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mochaina_fixed_silent_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mochaina_pwa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

with app.app_context():
    db.create_all()

STYLE = """<meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0}.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:400px;margin:15px auto}input{width:100%;padding:12px;margin:6px 0;border-radius:10px;border:2px solid #e2e8f0;box-sizing:border-box}.btn{border:none;padding:12px;border-radius:10px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}.btn-green{background:#16a34a;color:white}.btn-blue{background:#2563eb;color:white}.btn-gold{background:#facc15;color:black}.btn-dark{background:#14532d;color:white}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin:10px 0}.num-btn{padding:10px;background:white;border:2px solid #e2e8f0;border-radius:8px}.num-btn.selected{background:#86efac}.wing-btn{padding:10px 15px;background:white;border:2px solid #e2e8f0;border-radius:8px;margin:2px}.wing-btn.selected{background:#fde047}.game-card{border:2px solid #fde68a;border-radius:16px;padding:14px;margin:10px 0;background:#fffbeb;color:#000;cursor:pointer;text-align:left}</style><script>let sel=[];function toggle(n,el){if(sel.includes(n)){sel=sel.filter(x=>x!=n);el.classList.remove('selected')}else{if(sel.length<4){sel.push(n);el.classList.add('selected')}}document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}function pickWing(n,el){document.querySelectorAll('.wing-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');document.getElementById('yourW').innerText='Wing: W'+n;document.getElementById('wing_input').value=n;}function autoPick(){sel=[];document.querySelectorAll('.num-btn').forEach(b=>b.classList.remove('selected'));let nums=[];while(nums.length<4){let r=Math.floor(Math.random()*36)+1;if(!nums.includes(r))nums.push(r)}nums.forEach(n=>{sel.push(n);document.getElementById('btn'+n).classList.add('selected')});let rw=Math.floor(Math.random()*4)+1;pickWing(rw,document.getElementById('wbtn'+rw));document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}</script>"""

@app.route('/')
def home(): return redirect('/login')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        user=User.query.filter_by(username=u).first()
        if user and (check_password_hash(user.password, p) or user.password==p):
            session['uid']=user.id; session['uname']=u; return redirect('/menu')
        return STYLE+"<div class=card>Wrong</div>"
    return STYLE+"""<div class=card><h2>LOGIN</h2><form method='post'><input name='username' required><input name='password' type='password' required><button class='btn btn-green'>Login</button></form><a href='/register'>Register</a></div>"""
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['full_name']; p=request.form['password']
        if User.query.filter_by(username=name).first(): return STYLE+"<div class=card>Exists</div>"
        user=User(username=name,password=generate_password_hash(p)); db.session.add(user); db.session.commit()
        session['uid']=user.id; session['uname']=name; return redirect('/menu')
    return STYLE+"""<div class=card><h2>Register</h2><form method='post'><input name='full_name' required><input name='password' type='password' required><button class='btn btn-gold'>Register</button></form></div>"""
@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>⭐ MOCHAINA STAR ⭐ SILENT</h2><p>Balance: R{user.balance:.2f}</p>
<button class='btn btn-green' onclick="location.href='/play'">1. PLAY LOTTO 4/36</button>
<button class='btn btn-green' onclick="location.href='/play610'">1b. PLAY 6/10</button>
<button class='btn btn-blue' onclick="location.href='/live'">7. LIVE GAMES - SILENT NO SOUND</button>
<button class='btn' style=background:gray;color:white onclick="location.href='/logout'">LOGOUT</button></div>"""
@app.route('/live')
def live_games():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>LIVE GAMES SILENT 🔇</h2><p>Balance: R{user.balance:.2f}</p>
<div class='game-card' onclick="location.href='/coin'"><b>🪙 COIN FLIP</b></div>
<div class='game-card' onclick="location.href='/wheel'"><b>🎡 WHEEL</b></div>
<div class='game-card' onclick="location.href='/slots'"><b>🎰 SLOTS</b></div>
<div class='game-card' onclick="location.href='/dice'"><b>🎲 DICE</b></div>
<button class='btn' style=background:#e2e8f0 onclick="location.href='/menu'">BACK</button></div>"""
@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>WHEEL - SILENT</h2><p>R{user.balance:.0f}</p><button class='btn btn-gold' onclick="fetch('/wheel_spin?stake=2&color=red').then(r=>r.json()).then(d=>{{alert(d.win>0?'WON R'+d.win:'LOST '+d.landed_label); location.reload();}})">SPIN RED R2 TEST</button><button class='btn' onclick="location.href='/live'">BACK</button></div>"""
@app.route('/wheel_spin')
def wheel_spin():
    user=User.query.get(session['uid']); stake=2
    if stake>user.balance: return jsonify(win=0, index=0, landed_label="NO BAL", balance=user.balance)
    user.balance-=stake; cols=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"]; idx=random.randint(0,11); landed=cols[idx]; win=0
    if landed=="RED": win=stake*2; user.balance+=win
    db.session.commit(); return jsonify(win=win, index=idx, landed_label=landed, balance=user.balance)
@app.route('/play')
def play():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    grid="".join([f"<button id='btn{i}' class='num-btn' onclick='toggle({i},this)'>{i}</button>" for i in range(1,37)])
    return STYLE+f"""<div class=card><h2>PLAY 4/36 - SILENT</h2><p>R{user.balance:.2f}</p><input id='bet_input' value='10' type='number' style=width:80px><button class='btn btn-green' onclick='autoPick()'>Auto</button><div class=grid>{grid}</div><button id='wbtn1' class='wing-btn' onclick='pickWing(1,this)'>W1</button><button id='wbtn2' class='wing-btn' onclick='pickWing(2,this)'>W2</button><button id='wbtn3' class='wing-btn' onclick='pickWing(3,this)'>W3</button><button id='wbtn4' class='wing-btn' onclick='pickWing(4,this)'>W4</button><p id='your4'>Your 4: []</p><p id='yourW'>Wing: -</p><form method='post' action='/buy'><input type='hidden' name='numbers' id='nums_input' required><input type='hidden' name='wing' id='wing_input' required><input type='hidden' name='bet' id='bet_hidden'><button class='btn btn-gold' onclick="document.getElementById('bet_hidden').value=document.getElementById('bet_input').value">PLACE BET</button></form><button class='btn' style=background:gray onclick="location.href='/menu'">BACK</button></div>"""
@app.route('/buy', methods=['POST'])
def buy():
    user=User.query.get(session['uid']); nums_str=request.form['numbers']; wing=int(request.form['wing']); bet=int(float(request.form['bet']))
    user.balance-=bet; t=Ticket(user_id=user.id, username=user.username, numbers=nums_str, wing=wing, bet=bet); db.session.add(t); db.session.commit()
    return STYLE+f"<div class=card><h2>Ticket #{t.id} OK</h2><button class='btn btn-gold' onclick=\"location.href='/play'\">BACK</button></div>"
@app.route('/coin')
def coin():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>COIN SILENT</h2><button class='btn btn-green' onclick="fetch('/coin_flip?choice=heads').then(r=>r.json()).then(d=>{{alert(d.result+' WIN '+d.win); location.reload()}})">HEADS</button><button class='btn btn-blue' onclick="fetch('/coin_flip?choice=tails').then(r=>r.json()).then(d=>{{alert(d.result+' WIN '+d.win); location.reload()}})">TAILS</button><button class='btn' onclick="location.href='/live'">BACK</button></div>"""
@app.route('/coin_flip')
def coin_flip():
    user=User.query.get(session['uid']); result=random.choice(['heads','tails']); choice=request.args.get('choice','heads'); win=2 if result==choice else 0
    if win>0: user.balance+=win; db.session.commit()
    return jsonify(result=result, win=win)
@app.route('/dice')
def dice_page():
    if 'uid' not in session: return redirect('/login')
    return STYLE+"""<div class=card><h2>DICE SILENT</h2><button class='btn btn-green' onclick="fetch('/dice_roll?choice=low').then(r=>r.json()).then(d=>alert(d.msg))">LOW</button><button class='btn btn-blue' onclick="fetch('/dice_roll?choice=high').then(r=>r.json()).then(d=>alert(d.msg))">HIGH</button><button class='btn' onclick="location.href='/live'">BACK</button></div>"""
@app.route('/dice_roll')
def dice_roll():
    user=User.query.get(session['uid']); rn=random.randint(0,100); win=2 if rn<40 else 0
    if win>0: user.balance+=win; db.session.commit()
    return jsonify(roll=rn, msg=f"Roll {rn} {'WIN' if win else 'LOSE'}", win=win, d1=2, d2=5, balance=user.balance)
@app.route('/slots')
def slots():
    if 'uid' not in session: return redirect('/login')
    return STYLE+"""<div class=card><h2>SLOTS SILENT</h2><button class='btn btn-blue' onclick="fetch('/slots_spin?stake=2').then(r=>r.json()).then(d=>alert(d.msg))">SPIN</button><button class='btn' onclick="location.href='/live'">BACK</button></div>"""
@app.route('/slots_spin')
def slots_spin():
    user=User.query.get(session['uid']); win=10 if random.random()>0.7 else 0
    if win>0: user.balance+=win; db.session.commit()
    return jsonify(reels=["🍒","🍒","🍒"], msg=f"{'WIN R'+str(win) if win else 'LOSE'}", win=win, balance=user.balance)

# 6/10 SIMPLE WORKING
DB610="lotto_profit.db"
def init610():
    con=sqlite3.connect(DB610); con.execute("CREATE TABLE IF NOT EXISTS tickets610(id INTEGER PRIMARY KEY, user_id INTEGER, picks TEXT, left4 TEXT, draw_time TEXT, date TEXT, status TEXT, win_amount INTEGER, matched INTEGER)"); con.commit(); con.close()
init610()
@app.route('/play610')
def play610():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>6/10 SILENT</h2><p>R{user.balance:.2f}</p><button class='btn btn-gold' onclick="fetch('/buy610',{{
method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{picks:[1,2,3,4,5,6], draw_time:'12:00'}})}}).then(r=>r.json()).then(d=>alert(d.ok?'OK':'Error'))">BUY TEST 1-6</button><button class='btn' onclick="location.href='/menu'">BACK</button></div>"""
@app.route('/buy610', methods=['POST'])
def buy610():
    if 'uid' not in session: return jsonify(error="login"),401
    user=User.query.get(session['uid']); data=request.get_json(); picks=data.get("picks",[1,2,3,4,5,6]); left=[n for n in range(1,11) if n not in picks]
    user.balance-=10; db.session.commit()
    con=sqlite3.connect(DB610); con.execute("INSERT INTO tickets610(user_id,picks,left4,draw_time,date,status,win_amount,matched) VALUES(?,?,?,?,?,?,?,?)",(user.id,",".join(map(str,picks)),",".join(map(str,left)),"12:00","2026-09-07","pending",0,0)); con.commit(); con.close()
    return jsonify(ok=1)
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
