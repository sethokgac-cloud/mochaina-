from flask import Flask, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
import random, json, os, hashlib, urllib.parse, math, time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
app.secret_key = 'mochaina_business_pro_2026_final'
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
class Payment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer); username=db.Column(db.String(50))
    amount=db.Column(db.Integer); ref=db.Column(db.String(100)); status=db.Column(db.String(20), default="Pending"); method=db.Column(db.String(20))
class Voucher(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    code=db.Column(db.String(100), unique=True); amount=db.Column(db.Integer); is_used=db.Column(db.Boolean, default=False); used_by=db.Column(db.String(50))

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
        except Exception as e: print("init error:", e)

PAYFAST_MERCHANT_ID = "10000100"
PAYFAST_MERCHANT_KEY = "46f0cd694581a"
PAYFAST_PASSPHRASE = ""
PAYFAST_URL = "https://www.payfast.co.za/eng/process"

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

safe_init()

STYLE="""<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="manifest" href="/static/manifest.json"><meta name="theme-color" content="#facc15"><script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/static/sw.js')}</script><style>body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0}.header{padding:15px}.header h1{color:#facc15;font-size:26px;font-weight:900;margin:0}.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:400px;margin:15px auto}input,select{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:10px;border:2px solid #e2e8f0}.btn{border:none;padding:12px;border-radius:10px;font-weight:900;width:100%;cursor:pointer;margin:5px 0}.btn-green{background:#16a34a;color:white}.btn-dark{background:#14532d;color:white}.btn-blue{background:#2563eb;color:white}.btn-orange{background:#f97316;color:white}.btn-purple{background:#9333ea;color:white}.btn-red{background:#dc2626;color:white}.btn-gold{background:linear-gradient(90deg,#facc15,#f97316);color:black}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin:10px 0}.num-btn{padding:10px;background:white;border:2px solid #e2e8f0;border-radius:8px;font-weight:700}.num-btn.selected{background:#86efac;border-color:#16a34a}.wing-btn{padding:10px 15px;background:white;border:2px solid #e2e8f0;border-radius:8px;margin:2px}.wing-btn.selected{background:#fde047;border-color:#eab308}.jackpot{background:black;color:gold;font-size:22px;font-weight:900;padding:8px 16px;border-radius:8px;display:inline-block;border:2px solid #facc15}.timer-box{background:#fee2e2;color:#dc2626;font-weight:900;padding:8px 12px;border-radius:10px;display:inline-block;margin:6px 0;white-space:nowrap;letter-spacing:1px;font-family:monospace;font-size:16px;border:1px solid #fecaca}.tabs{display:flex;gap:4px;margin:10px 0}.tab{flex:1;padding:8px;background:#e2e8f0;border-radius:8px;cursor:pointer;font-weight:700;font-size:10px}.tab.active{background:#2563eb;color:white}.tabcontent{border:1px solid #eee;padding:10px;border-radius:10px}.install-banner{background:#facc15;color:black;padding:10px;border-radius:10px;margin:10px;font-weight:900;display:none}.game-card{border:2px solid #fde68a;border-radius:16px;padding:14px;margin:10px 0;background:linear-gradient(135deg,#fffbeb,#fef3c7);cursor:pointer;text-align:left;color:#000}.reel-box{width:80px;height:90px;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.2);border:3px solid white;display:flex;align-items:center;justify-content:center}.reel{font-size:42px;font-weight:900;transition:0.1s}.reel.spinning{filter:blur(3px);transform:scaleY(1.2)}.table{background:#0f172a;border-radius:20px;height:340px;position:relative;overflow:hidden}.dice{width:68px;height:68px;background:linear-gradient(145deg,#fff,#f1e9de);border-radius:14px;position:absolute;left:50%;bottom:40px;transform:translateX(-50%);display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);padding:7px;gap:2px;box-shadow:0 8px 20px rgba(0,0,0,0.6);z-index:20;border:2px solid #e8dcc8;opacity:0}.dice2{z-index:21}.dot{width:11px;height:11px;background:#0f172a;border-radius:50%;justify-self:center;align-self:center}.hidden{visibility:hidden}.hand{position:absolute;bottom:25px;left:50%;transform:translateX(-50%);font-size:82px;z-index:10}@keyframes throw1{0%{bottom:45px;transform:translateX(-50%) rotate(0deg) scale(0.5);opacity:0}30%{bottom:190px;transform:translateX(-75px) rotate(360deg) scale(1.2);opacity:1}60%{bottom:245px;transform:translateX(-85px) rotate(720deg) scale(1.1);opacity:1}100%{bottom:115px;transform:translateX(-78px) rotate(1080deg) scale(1);opacity:1}}@keyframes throw2{0%{bottom:45px;transform:translateX(-50%) rotate(0deg) scale(0.5);opacity:0}35%{bottom:200px;transform:translateX(30px) rotate(-360deg) scale(1.2);opacity:1}65%{bottom:255px;transform:translateX(38px) rotate(-720deg) scale(1.1);opacity:1}100%{bottom:115px;transform:translateX(28px) rotate(-1080deg) scale(1);opacity:1}}@keyframes handOut{0%{transform:translateX(-50%) scale(1);opacity:1}100%{transform:translateX(-50%) translateY(130px) scale(0.3);opacity:0}}.throw1{animation:throw1 1.5s cubic-bezier(0.2,0.8,0.3,1) forwards}.throw2{animation:throw2 1.6s cubic-bezier(0.2,0.8,0.3,1) forwards}.handThrow{animation:handOut 0.5s ease 0.3s forwards}.coinBox{height:280px;background:radial-gradient(at center,#1e293b,#020617);border-radius:20px;display:flex;align-items:center;justify-content:center;border:3px solid #1e293b;perspective:800px}.coin{width:150px;height:150px;border-radius:50%;background:linear-gradient(145deg,#facc15,#f97316);display:flex;align-items:center;justify-content:center;font-size:55px;font-weight:900;color:#000;box-shadow:0 0 30px #facc15aa,inset 0 0 20px #fff8;border:4px solid #fde047}.color-btn{padding:14px 6px;border-radius:12px;border:3px solid white;font-weight:900;font-size:12px;cursor:pointer;transition:0.2s}.color-btn.selected{border-color:black;transform:scale(1.08);box-shadow:0 6px 15px rgba(0,0,0,0.4)}.music-tag{background:linear-gradient(90deg,#fce7f3,#f5d0fe);color:#831843;padding:6px 12px;border-radius:20px;font-size:11px;font-weight:900;display:inline-block;margin-bottom:8px;border:1px solid #f9a8d4}</style><script>let sel=[];let w=null;function toggle(n,el){if(sel.includes(n)){sel=sel.filter(x=>x!=n);el.classList.remove('selected')}else{if(sel.length<4){sel.push(n);el.classList.add('selected')}}document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}function pickWing(n,el){w=n;document.querySelectorAll('.wing-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');document.getElementById('yourW').innerText='Wing: W'+n;document.getElementById('wing_input').value=n;}function autoPick(){sel=[];document.querySelectorAll('.num-btn').forEach(b=>b.classList.remove('selected'));let nums=[];while(nums.length<4){let r=Math.floor(Math.random()*36)+1;if(!nums.includes(r))nums.push(r)}nums.forEach(n=>{sel.push(n);document.getElementById('btn'+n).classList.add('selected')});let rw=Math.floor(Math.random()*4)+1;pickWing(rw,document.getElementById('wbtn'+rw));document.getElementById('your4').innerText='Your 4: '+sel.join(',');document.getElementById('nums_input').value=sel.join(',');}function showTab(t){document.querySelectorAll('.tabcontent').forEach(c=>c.style.display='none');document.getElementById(t).style.display='block';document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');}let deferredPrompt;window.addEventListener('beforeinstallprompt',(e)=>{e.preventDefault();deferredPrompt=e;document.getElementById('installBanner').style.display='block';});function installApp(){if(deferredPrompt){deferredPrompt.prompt();deferredPrompt.userChoice.then(()=>{deferredPrompt=null;document.getElementById('installBanner').style.display='none';});}}function dots(n){let m={1:[[1,1]],2:[[0,0],[2,2]],3:[[0,0],[1,1],[2,2]],4:[[0,0],[0,2],[2,0],[2,2]],5:[[0,0],[0,2],[1,1],[2,0],[2,2]],6:[[0,0],[0,2],[1,0],[1,2],[2,0],[2,2]]};let p={};m[n].forEach(a=>p[a[0]+'-'+a[1]]=1);let h='';for(let r=0;r<3;r++){for(let c=0;c<3;c++){h+=p[r+'-'+c]?'<div class="dot"></div>':'<div class="dot hidden"></div>';}}return h;}function setDice(id,n){let el=document.getElementById(id);if(el)el.innerHTML=dots(n);}function startLiveCountdown(targetMs,elementId){function update(){let now=new Date().getTime();let diff=targetMs-now;if(diff<=0){let el=document.getElementById(elementId);if(el)el.innerText="00:00:00";setTimeout(()=>{location.reload();},2000);return;}let h=Math.floor(diff/1000/3600);let m=Math.floor((diff/1000%3600)/60);let s=Math.floor(diff/1000%60);let el=document.getElementById(elementId);if(el)el.innerText=String(h).padStart(2,'0')+":"+String(m).padStart(2,'0')+":"+String(s).padStart(2,'0');}setInterval(update,1000);update();}let audioCtx=null;let musicGain=null;let musicInterval=null;let musicStarted=false;function getAudio(){if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();return audioCtx;}function beep(freq,dur,vol,type='sine'){try{let ctx=getAudio();let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=freq;o.type=type;o.connect(g);g.connect(ctx.destination);g.gain.setValueAtTime(vol,ctx.currentTime);g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);}catch(e){}}function playChord(freqs,dur){let ctx=getAudio();if(!musicGain)return;freqs.forEach(f=>{let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=f;o.type='triangle';o.connect(g);g.connect(musicGain);g.gain.setValueAtTime(0,ctx.currentTime);g.gain.linearRampToValueAtTime(0.09,ctx.currentTime+0.8);g.gain.linearRampToValueAtTime(0,ctx.currentTime+dur);o.start();o.stop(ctx.currentTime+dur);});}function startRomanticAuto(){if(musicStarted)return;let ctx=getAudio();if(!musicGain){musicGain=ctx.createGain();musicGain.connect(ctx.destination);musicGain.gain.value=0.30;}musicStarted=true;let chords=[[261.63,329.63,392.00],[220.00,261.63,329.63],[174.61,220.00,261.63],[196.00,246.94,293.66],[261.63,392.00,493.88],[220.00,329.63,440.00],[174.61,261.63,329.63],[196.00,293.66,392.00]];let melody=[523.25,659.25,783.99,1046.50,783.99,659.25,587.33,523.25];let idx=0;function loop(){playChord(chords[idx%8],3.8);setTimeout(()=>{beep(melody[idx%8],2.0,0.06,'sine');},600);idx=(idx+1)%8;musicInterval=setTimeout(loop,3500);}loop();}function soundWheelSpin(){let t=0;let iv=setInterval(()=>{beep(90+t*12,0.28,0.15,'sawtooth');t++;if(t>16)clearInterval(iv);},130);}function soundWheelWin(){beep(440,0.3,0.12);setTimeout(()=>beep(554,0.3,0.12),200);setTimeout(()=>beep(659,0.6,0.15),400);}function soundWheelLose(){beep(220,0.5,0.08,'triangle');setTimeout(()=>beep(150,0.8,0.08,'triangle'),400);}function soundSlotsSpin(){let c=0;let iv=setInterval(()=>{beep(500+Math.random()*500,0.09,0.06,'square');c++;if(c>18)clearInterval(iv);},85);}function soundSlotTick(n){if(n==1)beep(750,0.12,0.10,'square');if(n==2)beep(950,0.12,0.10,'square');if(n==3)beep(1150,0.18,0.12,'square');}function soundSlotsWin(){beep(523,0.2,0.10);setTimeout(()=>beep(659,0.2,0.10),120);setTimeout(()=>beep(784,0.2,0.10),240);setTimeout(()=>beep(1046,0.6,0.15),360);}function soundSlotsLose(){beep(280,0.4,0.06,'sawtooth');}function soundDiceShake(){let c=0;let iv=setInterval(()=>{beep(180+Math.random()*700,0.06,0.06,'square');c++;if(c>16)clearInterval(iv);},70);}function soundDiceWin(){beep(700,0.2,0.10);setTimeout(()=>beep(900,0.4,0.12),180);}function soundDiceLose(){beep(170,0.6,0.06,'sawtooth');}function soundCoinFlip(){let r=0;let iv=setInterval(()=>{beep(r%2==0?850:1150,0.11,0.08,'sine');r++;if(r>10)clearInterval(iv);},95);}function soundCoinWin(){beep(800,0.25,0.10);setTimeout(()=>beep(1200,0.5,0.12),200);}function soundCoinLose(){beep(190,0.5,0.06,'triangle');}</script>"""

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
    return STYLE+"""<div class=header><h1 style=color:#facc15>⭐ Mochaina Lotto 🇿🇦</h1></div><div style=background:linear-gradient(90deg,#facc15,#f97316);color:black;padding:12px;border-radius:12px;margin:10px;font-weight:900>🏆 JACKPOT NOW • R5,000,000 • Next draw Tonight 21:00</div><div id='installBanner' class='install-banner'>📱 INSTALL APP - Tap Here! <button onclick='installApp()' class='btn btn-dark' style=width:auto;padding:5px 15px>INSTALL</button></div><div class=card><h2>LOGIN</h2><form method='post'><div style=text-align:left;font-size:12px;font-weight:700;margin-top:8px>Full Name / Username</div><input name='username' placeholder='Enter your full name' required><div style=text-align:left;font-size:12px;font-weight:700>Password</div><input name='password' type='password' placeholder='Enter your password' required><button class='btn btn-green' style=margin-top:12px>Login</button></form><button class='btn btn-blue' onclick="location.href='/register'">Register R100 FREE</button></div>"""

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        try:
            full_name=request.form.get('full_name','').strip()
            p=request.form.get('password',''); p2=request.form.get('confirm_password',''); id_num=request.form.get('id_number','')
            if id_num and (len(id_num)!=13 or not id_num.isdigit()):
                return STYLE+"<div class=card><p style=color:red>❌ ID must be 13 digits</p><button class='btn btn-red' onclick=\"location.href='/register'\">Back</button></div>"
            if p2 and p!=p2:
                return STYLE+"<div class=card><p style=color:red>❌ Passwords don't match</p><button class='btn btn-red' onclick=\"location.href='/register'\">Back</button></div>"
            if len(p)<4:
                return STYLE+"<div class=card><p style=color:red>❌ Password min 4</p><button class='btn btn-red' onclick=\"location.href='/register'\">Back</button></div>"
            if User.query.filter_by(username=full_name).first():
                return STYLE+"<div class=card><p>Username exists</p><button class='btn' onclick=\"location.href='/register'\">Back</button></div>"
            user=User(username=full_name,password=generate_password_hash(p)); db.session.add(user); db.session.commit()
            session['uid']=user.id; session['uname']=full_name; return redirect('/menu')
        except Exception as e: return STYLE+f"<div class=card><p style=color:red>Error {e}</p><button onclick=\"location.href='/register'\">Back</button></div>"
    return STYLE+"""<div class=header><h1 style=color:#facc15>⭐ Mochaina Lotto 🇿🇦</h1></div><div style=background:linear-gradient(90deg,#facc15,#f97316);color:black;padding:12px;border-radius:12px;margin:10px;font-weight:900>🏆 JACKPOT NOW • R5,000,000 • Next draw Tonight 21:00</div><div class=card><h2 style=color:#ca8a04;margin:5px 0;font-weight:900;font-size:18px>Register • Create your account</h2><form method='post'><div style=text-align:left;font-size:12px;font-weight:700;margin-top:8px>Full Name</div><input name='full_name' placeholder='Enter your full name e.g. Thabo Mthembu' required><div style=text-align:left;font-size:12px;font-weight:700>ID Number</div><input name='id_number' placeholder='e.g. 9001015000081' maxlength='13' inputmode='numeric' required><div style=text-align:left;font-size:12px;font-weight:700>Phone Number</div><input name='phone' placeholder='+27 • Enter phone number' inputmode='tel' required><div style=text-align:left;font-size:12px;font-weight:700>Password</div><input name='password' type='password' placeholder='Create a password' required><div style=text-align:left;font-size:12px;font-weight:700>Confirm Password</div><input name='confirm_password' type='password' placeholder='Confirm your password' required><label style=font-size:11px;display:flex;gap:6px;align-items:center;margin:12px 0;text-align:left><input type='checkbox' required style=width:18px> I agree to Terms & Conditions • 18+ Only</label><button class='btn btn-gold'>REGISTER NOW</button></form><p style=font-size:12px;margin-top:12px>Already have an account? <a href='/login' style=color:#2563eb;font-weight:900;text-decoration:none>Login</a></p></div>"""

@app.route('/menu')
def menu():
    if 'uid' not in session: return redirect('/login')
    try: auto_draw_if_due()
    except: pass
    user=User.query.get(session['uid'])
    if not user: session.clear(); return redirect('/login')
    ts=get_next_draw_timestamp()
    return STYLE+f"""<div class=header><h1>⭐ MOCHAINA STAR ⭐</h1><p>Welcome, {session['uname']}</p></div><div id='installBanner' class='install-banner'>📱 INSTALL APP - Tap Here! <button onclick='installApp()' class='btn btn-dark' style=width:auto;padding:5px 15px>INSTALL</button></div><div class=card><p style=margin:4px 0>💰 JACKPOT 💰</p><div class=jackpot>R{get_jackpot():,.2f}</div><p style=color:green;font-weight:900;margin:8px 0>Balance: R{user.balance:.2f}</p><div style=margin:8px 0><span style=color:#475569;font-size:12px;font-weight:800>NEXT DRAW: </span><span id='liveTimer' class='timer-box'>{next_draw_str()}</span></div><script>startLiveCountdown({ts}, 'liveTimer')</script><button class='btn btn-green' onclick="location.href='/play'">1. PLAY LOTTO</button><button class='btn btn-dark' onclick="location.href='/my_tickets'">2. MY TICKETS</button><button class='btn btn-blue' onclick="location.href='/load'">3. LOAD FUNDS</button><button class='btn btn-orange' onclick="location.href='/withdraw'">4. WITHDRAW</button><button class='btn btn-purple' onclick="location.href='/results'">5. RESULTS</button><button class='btn btn-red' onclick="location.href='/admin?key=mochaina123'">6. ADMIN</button><button class='btn' style=background:linear-gradient(90deg,#ef4444,#9333ea);color:white;padding:18px;margin-top:6px' onclick="location.href='/live'">7. 🔴 LIVE GAMES - COIN WHEEL SLOTS DICE</button><button class='btn' style=background:gray;color:white onclick="location.href='/logout'">LOGOUT</button></div>"""

@app.route('/live')
def live_games():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🔴 LIVE GAMES 💕</h2><div class='music-tag'>🎹 Romantic music inside</div><p style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div class='game-card' onclick="location.href='/coin'" style=border-left:6px solid #facc15><b>🪙 COIN FLIP</b><span style=float:right>▶️</span></div><div class='game-card' onclick="location.href='/wheel'" style=border-left:6px solid #9333ea><b>🎡 AUTO WHEEL - BET WHILE SPIN!</b><span style=float:right>▶️</span></div><div class='game-card' onclick="location.href='/slots'" style=border-left:6px solid #2563eb><b>🎰 SLOTS ONE BY ONE</b><span style=float:right>▶️</span></div><div class='game-card' onclick="location.href='/dice'" style=border-left:6px solid #16a34a><b>🎲 DICE THROW</b><span style=float:right>▶️</span></div><button class='btn' style=background:#e2e8f0;color:#475569;margin-top:16px onclick="location.href='/menu'">BACK TO MENU</button></div>"""

# ================= FINAL: BET WHILE SPINNING =================
WHEEL_ROUND_FILE="wheel_round.json"
WHEEL_TOTAL = 12
WHEEL_CLOSE = 1
SPIN_TRIGGER = 8

def get_wheel_round():
    try:
        with open(WHEEL_ROUND_FILE,"r") as f: data=json.load(f)
        if time.time() > data['end_time']: raise Exception("expired")
        return data
    except:
        labels=["RED","YELLOW","GREEN","BLUE","ORANGE","PINK","PURPLE","CYAN"]*2
        data={"round_id":int(time.time()),"end_time":time.time()+WHEEL_TOTAL,"winning_index":random.randint(0,15),"labels":labels}
        with open(WHEEL_ROUND_FILE,"w") as f: json.dump(data,f)
        return data

@app.route('/wheel')
def wheel():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    colors = ["#dc2626","#eab308","#16a34a","#2563eb","#ea580c","#db2777","#7c3aed","#0891b2"]*2
    svg=""
    for i in range(16):
        a1=math.radians(i*22.5-90); a2=math.radians((i+1)*22.5-90)
        x1=100+95*math.cos(a1); y1=100+95*math.sin(a1)
        x2=100+95*math.cos(a2); y2=100+95*math.sin(a2)
        svg+=f'<path d="M100,100 L{x1:.1f},{y1:.1f} A95,95 0 0,1 {x2:.1f},{y2:.1f} Z" fill="{colors[i]}" stroke="white" stroke-width="3"/>'
    return STYLE+f"""<div class=card><h2>🎡 WHEEL - BET WHILE SPIN ⚡</h2><div id='roundInfo' style=background:#0f172a;color:#facc15;padding:12px;border-radius:12px;font-weight:900;font-size:22px>⏳ BET: 12s</div><div style=background:#dcfce7;color:#166534;padding:8px;border-radius:8px;margin:8px 0;font-weight:900;font-size:14px id='betStatus'>✅ BET NOW!</div><p id='bal' style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div style=position:relative><div style=position:absolute;top:-8px;left:50%;transform:translateX(-50%);font-size:42px;z-index:10>👇</div><div id='wheel' style='width:300px;height:300px;margin:10px auto;border-radius:50%;border:10px solid #facc15;overflow:hidden;transform:rotate(0deg);background:white;box-shadow:0 0 30px #facc15aa'><svg viewBox="0 0 200 200" style=width:100%;height:100%>{svg}<circle cx="100" cy="100" r="22" fill="#0f172a" stroke="#facc15" stroke-width="4"/><circle cx="100" cy="100" r="10" fill="#facc15"/></svg></div></div><div id='lastWin' style=font-weight:900;font-size:18px;min-height:24px>Last: -</div><div style=text-align:left;font-weight:900;font-size:12px;margin:8px 0>BET FOR NEXT WHILE SPINNING:</div><div style=display:grid;grid-template-columns:repeat(4,1fr);gap:8px><button class='color-btn' style=background:#dc2626;color:white onclick="pickColor('red','RED',this)">🔴 RED x2</button><button class='color-btn' style=background:#eab308;color:black onclick="pickColor('yellow','YELLOW',this)">🟡 YEL x3</button><button class='color-btn' style=background:#16a34a;color:white onclick="pickColor('green','GREEN',this)">🟢 GREEN x2.5</button><button class='color-btn' style=background:#2563eb;color:white onclick="pickColor('blue','BLUE',this)">🔵 BLUE x2.5</button><button class='color-btn' style=background:#ea580c;color:white onclick="pickColor('orange','ORANGE',this)">🟠 ORANGE x4</button><button class='color-btn' style=background:#db2777;color:white onclick="pickColor('pink','PINK',this)">🩷 PINK x4</button><button class='color-btn' style=background:#7c3aed;color:white onclick="pickColor('purple','PURPLE',this)">🟣 PURPLE x5</button><button class='color-btn' style=background:#0891b2;color:white onclick="pickColor('cyan','CYAN',this)">🔷 CYAN x5</button></div><div id='picked' style=font-weight:900;margin:10px 0;color:#9333ea>Pick color!</div><div id='myBets' style=text-align:left;font-size:12px;background:#f8fafc;padding:8px;border-radius:8px;min-height:20px>Your bets for NEXT: none</div><div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px><button class='btn btn-dark' onclick="setStake(1)">R1</button><button class='btn btn-dark' onclick="setStake(2)">R2</button><button class='btn btn-dark' onclick="setStake(5)">R5</button><button class='btn btn-dark' onclick="setStake(10)">R10</button></div><input id='wheel_stake' type='hidden' value='2'><div id='stakeShow' style=text-align:left;font-size:13px;font-weight:800>Stake: R2</div><button id='betBtn' class='btn btn-purple' style=padding:18px;font-size:18px;opacity:0.5;pointer-events:none onclick="placeBet()">PICK COLOR</button><button class='btn' style=background:#e2e8f0;color:#475569 onclick="location.href='/live'">BACK</button><script>
let selectedColor=null;let cr=0;let myBetsForRound=[];let currentRoundId=0;let canBet=true;
function setStake(v){{document.getElementById('wheel_stake').value=v;document.getElementById('stakeShow').innerText='Stake: R'+v;}}
function pickColor(c,l,el){{if(!canBet){{if(document.getElementById('roundInfo').innerText.includes('STOP')){{alert('Wait 1 sec showing win!');}}return;}}selectedColor=c;document.querySelectorAll('.color-btn').forEach(b=>b.classList.remove('selected'));el.classList.add('selected');document.getElementById('picked').innerText='Picked '+l+' FOR NEXT';let btn=document.getElementById('betBtn');btn.style.opacity='1';btn.style.pointerEvents='auto';btn.innerText='BET R'+document.getElementById('wheel_stake').value+' ON '+l+' (NEXT)';beep(600,0.1,0.10);}}
function placeBet(){{if(!selectedColor||!canBet)return;let stake=document.getElementById('wheel_stake').value;fetch('/wheel_auto_bet?color='+selectedColor+'&stake='+stake+'&round='+currentRoundId).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);return;}}document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);myBetsForRound.push(d.bet);let h='Bets for NEXT #'+d.bet.round_id+':<br>';myBetsForRound.forEach(b=>{{h+=b.color.toUpperCase()+' R'+b.stake+' -> Win R'+b.potential+'<br>';}});document.getElementById('myBets').innerHTML=h;}});}}
function updateRound(){{fetch('/wheel_auto_status').then(r=>r.json()).then(d=>{{currentRoundId=d.round_id;let left=Math.max(0,Math.floor(d.time_left));document.getElementById('roundInfo').innerText='⏳ '+(left>8?'BET NEXT: ':'SPIN+BET: ')+left+'s | #'+d.round_id;if(left<=8 && left>1 &&!window.spinningNow){{window.spinningNow=true;document.getElementById('betStatus').innerText='🔴 SPINNING LONG 8s... BET FOR NEXT NOW! ⚡';document.getElementById('betStatus').style.background='#fef3c7';document.getElementById('betStatus').style.color='#92400e';let w=document.getElementById('wheel');let center=d.winning_index*22.5+11.25;let target=(360-center+360)%360;let finalRot=cr+(6*360)+target+720;w.style.transition='transform 7.5s cubic-bezier(0.15,0.85,0.25,1)';w.style.transform='rotate('+finalRot+'deg)';setTimeout(()=>{{cr=finalRot%360;w.style.transition='none';w.style.transform='rotate('+cr+'deg)';window.spinningNow=false;}},7600);}} if(left<=1){{canBet=false;document.getElementById('betStatus').innerText='⏸️ STOP 1 SEC - SHOW WIN/LOSE!';document.getElementById('betStatus').style.background='#fee2e2';document.getElementById('betStatus').style.color='#dc2626';document.getElementById('betBtn').innerText='STOP - SHOWING WIN...';document.getElementById('betBtn').style.opacity='0.3';document.getElementById('betBtn').style.pointerEvents='none';}} else {{canBet=true;document.getElementById('betStatus').innerText='✅ BET FOR NEXT WHILE SPINNING! '+left+'s left';document.getElementById('betStatus').style.background='#dcfce7';document.getElementById('betStatus').style.color='#166534';if(selectedColor){{document.getElementById('betBtn').style.opacity='1';document.getElementById('betBtn').style.pointerEvents='auto';}}}} if(d.just_finished){{if(d.my_win>0){{document.getElementById('lastWin').innerText='🎉 YOU WON R'+d.my_win+'! Landed '+d.last_label;document.getElementById('lastWin').style.color='#16a34a';soundWheelWin();}} else {{document.getElementById('lastWin').innerText='Landed '+d.last_label+(myBetsForRound.length>0?' - YOU LOST':'');document.getElementById('lastWin').style.color='#ef4444';if(myBetsForRound.length>0) soundWheelLose();}} document.getElementById('bal').innerText='Balance: R'+d.balance.toFixed(2);myBetsForRound=[];document.getElementById('myBets').innerHTML='Your bets for NEXT: none';}} }});}}
setInterval(updateRound,400);updateRound();
window.addEventListener('load',()=>{{setTimeout(()=>{{try{{startRomanticAuto();}}catch(e){{}}}},400);}});
</script></div>"""

@app.route('/wheel_auto_status')
def wheel_auto_status():
    if 'uid' not in session: return {"error":"login"}
    data=get_wheel_round()
    time_left=data['end_time']-time.time()
    status="BETTING" if time_left>WHEEL_CLOSE else "SPINNING"
    just_finished=False
    if time_left<=0:
        labels=data['labels']
        win_idx=data['winning_index']
        win_label=labels[win_idx]
        bets=session.get('wheel_bets',[])
        my_win=0
        for b in bets:
            if b['round_id']==data['round_id']:
                if b['color'].lower()==win_label.lower():
                    my_win+=b['potential']
        if my_win>0:
            user=User.query.get(session['uid'])
            user.balance+=my_win
            db.session.commit()
        session['wheel_bets']=[]
        session['last_win_label']=win_label
        session['last_win_amount']=my_win
        session.modified=True
        try: os.remove(WHEEL_ROUND_FILE)
        except: pass
        data=get_wheel_round()
        time_left=data['end_time']-time.time()
        just_finished=True
    user=User.query.get(session['uid'])
    return {"round_id":data['round_id'],"time_left":time_left,"status":status,"winning_index":data['winning_index'],"last_win":session.get('last_win_label','-'),"last_label":session.get('last_win_label','-'),"just_finished":just_finished,"my_win":session.get('last_win_amount',0) if just_finished else 0,"balance":user.balance}

@app.route('/wheel_auto_bet')
def wheel_auto_bet():
    if 'uid' not in session: return {"error":"login"}
    data=get_wheel_round()
    time_left=data['end_time']-time.time()
    if time_left<WHEEL_CLOSE: return {"error":"Stop 1 sec! Showing win... wait next!"}
    try: stake=int(float(request.args.get('stake',2)))
    except: stake=2
    color=request.args.get('color','red').lower()
    payouts={'red':2,'yellow':3,'green':2.5,'blue':2.5,'orange':4,'pink':4,'purple':5,'cyan':5}
    if color not in payouts: return {"error":"Invalid color"}
    user=User.query.get(session['uid'])
    if stake>user.balance: return {"error":"No balance R%.2f"%user.balance}
    user.balance-=stake
    potential=round(stake*payouts[color],2)
    bet={"round_id":data['round_id'],"color":color,"stake":stake,"potential":potential}
    if 'wheel_bets' not in session: session['wheel_bets']=[]
    session['wheel_bets'].append(bet)
    session.modified=True
    db.session.commit()
    return {"balance":user.balance,"bet":bet}

@app.route('/wheel_spin')
def wheel_spin(): return redirect('/wheel')

@app.route('/slots')
def slots():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🎰 SLOTS 💕</h2><div class='music-tag'>🎹 Music inside</div><p id='slotBal' style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div style=background:#0f172a;padding:18px;border-radius:20px><div style=display:flex;justify-content:center;gap:10px><div class='reel-box'><div id='r1' class='reel'>🍒</div></div><div class='reel-box'><div id='r2' class='reel'>🍋</div></div><div class='reel-box'><div id='r3' class='reel'>🔔</div></div></div></div><div id='slot_res' style=font-weight:900;margin:12px 0;min-height:22px;font-size:18px></div><div id='slot_win' style=font-weight:900;font-size:24px;min-height:30px></div><div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px><button class='btn btn-dark' onclick="setSlotStake(1)">R1</button><button class='btn btn-dark' onclick="setSlotStake(2)">R2</button><button class='btn btn-dark' onclick="setSlotStake(5)">R5</button><button class='btn btn-dark' onclick="setSlotStake(10)">R10</button></div><input id='slot_stake' type='hidden' value='1'><div id='slotStakeShow' style=text-align:left;font-size:13px;font-weight:800;margin:6px 0>Stake: R1</div><button id='spinBtn' class='btn btn-blue' style=padding:16px;font-size:18px onclick="spinSlot()">🎰 SPIN</button><button class='btn' style=background:#e2e8f0;color:#475569 onclick="location.href='/live'">BACK</button></div><script>
    window.addEventListener('load', function(){{ setTimeout(function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }},400); document.body.addEventListener('click', function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }}, {{once:true}}); }});
    let slotSymbols=["🍒","🍋","🔔","7️⃣","⭐","💎","🍉","🍇"];
    function setSlotStake(v){{document.getElementById('slot_stake').value=v;document.getElementById('slotStakeShow').innerText='Stake: R'+v;}}
    function spinSlot(){{let stake=document.getElementById('slot_stake').value;let btn=document.getElementById('spinBtn');if(btn.disabled)return;btn.disabled=true;btn.innerText='SPINNING...';let r1=document.getElementById('r1'),r2=document.getElementById('r2'),r3=document.getElementById('r3');r1.classList.add('spinning');r2.classList.add('spinning');r3.classList.add('spinning');soundSlotsSpin();let inter1=setInterval(function(){{r1.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},60);let inter2=setInterval(function(){{r2.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},70);let inter3=setInterval(function(){{r3.innerText=slotSymbols[Math.floor(Math.random()*slotSymbols.length)];}},80);fetch('/slots_spin?stake='+stake).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);clearInterval(inter1);clearInterval(inter2);clearInterval(inter3);r1.classList.remove('spinning');r2.classList.remove('spinning');r3.classList.remove('spinning');btn.disabled=false;btn.innerText='SPIN';return;}}setTimeout(function(){{clearInterval(inter1);r1.classList.remove('spinning');r1.innerText=d.reels[0];soundSlotTick(1);}},1000);setTimeout(function(){{clearInterval(inter2);r2.classList.remove('spinning');r2.innerText=d.reels[1];soundSlotTick(2);}},1900);setTimeout(function(){{clearInterval(inter3);r3.classList.remove('spinning');r3.innerText=d.reels[2];soundSlotTick(3);document.getElementById('slot_res').innerText=d.msg;document.getElementById('slotBal').innerText='Balance: R'+d.balance.toFixed(2);if(d.win>0){{document.getElementById('slot_win').innerText='WIN R'+d.win+'!';document.getElementById('slot_win').style.color='#16a34a';soundSlotsWin();}}else{{document.getElementById('slot_win').innerText=d.reels.join(' - ');document.getElementById('slot_win').style.color='#ef4444';soundSlotsLose();}}btn.disabled=false;btn.innerText='SPIN AGAIN';}},2800);}});}}
    </script>"""

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
    if win>0: user.balance+=win
    db.session.commit()
    return {"reels":reels,"msg":msg,"win":win,"balance":round(user.balance,2)}

@app.route('/dice')
def dice_page():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🎲 DICE THROW 💕</h2><div class='music-tag'>🎹 Music inside</div><p style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div class="table"><div id="num" style=position:absolute;top:30px;left:0;right:0;font-size:56px;font-weight:900;color:#facc15>?</div><div id="d1" class="dice"></div><div id="d2" class="dice dice2"></div><div id="hand" class="hand">✋🏾</div></div><div id="diceRes" style=font-weight:900;font-size:15px;min-height:22px;margin:12px 0></div><input id='dice_stake' type='hidden' value='2'><div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px><button class='btn btn-dark' onclick="setStake(1)">R1</button><button class='btn btn-dark' onclick="setStake(2)">R2</button><button class='btn btn-dark' onclick="setStake(5)">R5</button><button class='btn btn-dark' onclick="setStake(10)">R10</button></div><div id='stakeShow' style=text-align:left;font-size:13px;font-weight:800>Stake: R2</div><div style=display:grid;gap:8px><button id='low' class='btn btn-green' onclick="playDice('low')">📉 LOW 0-39</button><button id='high' class='btn btn-blue' onclick="playDice('high')">📈 HIGH 61-100</button></div><button class='btn' style=background:#e2e8f0;color:#475569;margin-top:8px onclick="location.href='/live'">BACK</button></div><script>
    window.addEventListener('load', function(){{ setTimeout(function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }},400); document.body.addEventListener('click', function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }}, {{once:true}}); }});
    function setStake(v){{document.getElementById('dice_stake').value=v;document.getElementById('stakeShow').innerText='Stake: R'+v;}}
    setDice('d1',2);setDice('d2',5);
    function playDice(choice){{let stake=document.getElementById('dice_stake').value;soundDiceShake();let d1=document.getElementById('d1'),d2=document.getElementById('d2'),hand=document.getElementById('hand');document.getElementById('low').disabled=true;document.getElementById('high').disabled=true;document.getElementById('diceRes').innerText='Shaking...';d1.className='dice';d2.className='dice dice2';hand.className='hand';void d1.offsetWidth;d1.classList.add('throw1');d2.classList.add('throw2');hand.classList.add('handThrow');d1.style.opacity=1;d2.style.opacity=1;let t=0,inter=setInterval(function(){{setDice('d1',Math.floor(Math.random()*6)+1);setDice('d2',Math.floor(Math.random()*6)+1);document.getElementById('num').innerText=Math.floor(Math.random()*101);if(++t>16)clearInterval(inter);}},70);setTimeout(function(){{fetch('/dice_roll?stake='+stake+'&choice='+choice).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);location.reload();return;}}clearInterval(inter);setDice('d1',d.d1);setDice('d2',d.d2);document.getElementById('num').innerText=d.roll;document.getElementById('diceRes').innerText=d.msg;if(d.win>0)soundDiceWin();else soundDiceLose();setTimeout(function(){{location.reload();}},1600);}});}},1500);}}
    </script>"""

@app.route('/dice_roll')
def dice_roll():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',2)))
    except: stake=2
    if stake<=0 or stake>1000: return {"error":"Invalid stake"}
    choice=request.args.get('choice','low')
    if stake>user.balance: return {"roll":0,"msg":"No bal","win":0,"d1":1,"d2":1}
    rn=random.randint(0,100); d1=random.randint(1,6); d2=random.randint(1,6); win=0
    if 40<=rn<=60: user.balance-=stake; msg=f"HOUSE {rn} LOSE"
    elif (choice=='low' and rn<=39) or (choice=='high' and rn>=61): win=stake*2; user.balance+=win-stake; msg=f"WON R{win} Roll {rn}"
    else: user.balance-=stake; msg=f"LOST Roll {rn}"
    db.session.commit(); return {"roll":rn,"msg":msg,"win":win,"d1":d1,"d2":d2}

@app.route('/coin')
def coin_page():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>🪙 COIN FLIP 💕</h2><div class='music-tag'>🎹 Music inside</div><p style=color:#16a34a;font-weight:900>Balance: R{user.balance:.2f}</p><div class="coinBox"><div class="coin" id="coin">R</div></div><div id="coinRes" style=font-weight:900;font-size:15px;min-height:22px;margin:12px 0>Soft flip</div><div style=display:grid;grid-template-columns:repeat(4,1fr);gap:6px><button class='btn btn-dark' onclick="setStake(1)">R1</button><button class='btn btn-dark' onclick="setStake(2)">R2</button><button class='btn btn-dark' onclick="setStake(5)">R5</button><button class='btn btn-dark' onclick="setStake(10)">R10</button></div><input id='coin_stake' type='hidden' value='2'><div id='stakeShow' style=text-align:left;margin:6px 4px;font-size:14px;font-weight:800>Stake: R2</div><div style=display:grid;grid-template-columns:1fr 1fr;gap:8px><button id='hBtn' class='btn btn-green' onclick="playCoin('heads')">👑 HEADS</button><button id='tBtn' class='btn btn-blue' onclick="playCoin('tails')">🦅 TAILS</button></div><button class='btn' style=background:#e2e8f0;color:#475569;margin-top:8px onclick="location.href='/live'">BACK</button></div><script>
    window.addEventListener('load', function(){{ setTimeout(function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }},400); document.body.addEventListener('click', function(){{ try{{ startRomanticAuto(); }}catch(e){{}} }}, {{once:true}}); }});
    function setStake(v){{document.getElementById('coin_stake').value=v;document.getElementById('stakeShow').innerText='Stake: R'+v;}}
    let busy=false;
    function playCoin(choice){{if(busy)return;busy=true;let stake=document.getElementById('coin_stake').value;let coin=document.getElementById('coin');let res=document.getElementById('coinRes');soundCoinFlip();let speed=55,rot=0;coin.innerText='?';res.innerText='Flipping...';document.getElementById('hBtn').disabled=true;document.getElementById('tBtn').disabled=true;let timer=setInterval(function(){{rot+=speed;coin.style.transform='rotateY('+rot+'deg) scale(1.2)';if(rot<800)speed=55;else if(rot<1600)speed=35;else if(rot<2400)speed=18;else if(rot<3000)speed=7;else{{clearInterval(timer);fetch('/coin_flip?stake='+stake+'&choice='+choice).then(r=>r.json()).then(d=>{{if(d.error){{alert(d.error);busy=false;document.getElementById('hBtn').disabled=false;document.getElementById('tBtn').disabled=false;coin.innerText='R';return;}}let finalRot=Math.ceil(rot/360)*360;coin.style.transition='transform 0.4s ease-out';coin.style.transform='rotateY('+finalRot+'deg) scale(1)';setTimeout(function(){{if(d.result=='heads'){{coin.innerText='👑';coin.style.background='linear-gradient(145deg,#4ade80,#16a34a)';}}else{{coin.innerText='🦅';coin.style.background='linear-gradient(145deg,#60a5fa,#2563eb)';}}if(d.win>0){{res.innerText='WON R'+d.win;res.style.color='#16a34a';soundCoinWin();}}else{{res.innerText='LOST '+d.result.toUpperCase();res.style.color='#ef4444';soundCoinLose();}}busy=false;document.getElementById('hBtn').disabled=false;document.getElementById('tBtn').disabled=false;setTimeout(function(){{coin.style.transition='none';coin.style.background='linear-gradient(145deg,#facc15,#f97316)';coin.innerText='R';res.style.color='#0f172a';coin.style.transform='rotateY(0deg)';location.reload();}},1500);}},400);}});}}}},16);}}
    </script>"""

@app.route('/coin_flip')
def coin_flip():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    try: stake=int(float(request.args.get('stake',2)))
    except: stake=2
    if stake<=0 or stake>1000: return {"error":"Invalid stake"}
    choice=request.args.get('choice','heads')
    if stake>user.balance: return {"error":"No balance","result":"none","win":0}
    result=random.choice(['heads','tails'])
    user.balance-=stake; win=0
    if result==choice: win=round(stake*1.9,2); user.balance+=win
    db.session.commit(); return {"result":result,"win":win}

@app.route('/play')
def play():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    grid="".join([f"<button id='btn{i}' class='num-btn' onclick='toggle({i},this)'>{i}</button>" for i in range(1,37)])
    return STYLE+f"""<div class=header><h1>PLAY</h1><p>Balance: R{user.balance:.2f}</p></div><div class=card><input id='bet_input' type='number' value='10' min='1' max='1000' style=width:80px><button class='btn btn-green' onclick='autoPick()'>Auto Pick</button><div class=grid>{grid}</div><button id='wbtn1' class='wing-btn' onclick='pickWing(1,this)'>W1</button><button id='wbtn2' class='wing-btn' onclick='pickWing(2,this)'>W2</button><button id='wbtn3' class='wing-btn' onclick='pickWing(3,this)'>W3</button><button id='wbtn4' class='wing-btn' onclick='pickWing(4,this)'>W4</button><p id='your4'>Your 4: []</p><p id='yourW'>Wing: -</p><form method='post' action='/buy'><input type='hidden' name='numbers' id='nums_input' required><input type='hidden' name='wing' id='wing_input' required><input type='hidden' name='bet' id='bet_hidden'><button class='btn btn-gold' onclick="document.getElementById('bet_hidden').value=document.getElementById('bet_input').value">PLACE BET</button></form><button class='btn' style=background:gray onclick="location.href='/menu'">BACK</button></div>"""

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
        return STYLE+f"<div class=card><p style=color:red>❌ Pick 4 unique 1-36 + Wing 1-4</p><button onclick=\"location.href='/play'\">Back</button></div>"
    if bet>user.balance: return STYLE+f"<div class=card>No balance R{user.balance:.2f}<br><button onclick=\"location.href='/play'\">Back</button></div>"
    user.balance-=bet; save_jackpot(get_jackpot()+bet*0.1)
    t=Ticket(user_id=user.id, username=user.username, numbers=nums_str, wing=wing, bet=bet); db.session.add(t); db.session.commit()
    return STYLE+f"<div class=card><h2>✅ Ticket #{t.id}</h2><p>{nums_str}+W{wing} R{bet}</p><button class='btn btn-gold' onclick=\"location.href='/menu'\">MENU</button></div>"

@app.route('/load')
def load_funds():
    if 'uid' not in session: return redirect('/login')
    user=User.query.get(session['uid'])
    return STYLE+f"""<div class=card><h2>LOAD FUNDS</h2><p>Balance: R{user.balance:.2f}</p><div class=tabs><div id='tab-voucher' class='tab active' onclick="showTab('voucher')">🎟️ Vouchers</div><div id='tab-payfast' class='tab' onclick="showTab('payfast')">💳 PayFast</div><div id='tab-eft' class='tab' onclick="showTab('eft')">🏦 EFT</div></div>
    <div id='voucher' class='tabcontent'><h3>🎟️ All Vouchers</h3><form method='post' action='/redeem_voucher'><select name='voucher_type'><option value='BLU'>Blu Voucher</option><option value='1VOUCHER'>1Voucher / 1ForYou</option><option value='OTT'>OTT Voucher</option><option value='MOCHA'>Mochaina Voucher</option></select><input name='code' placeholder='Enter 10-16 digit PIN' required minlength=10><button class='btn btn-green'>REDEEM NOW</button></form></div>
    <div id='payfast' class='tabcontent' style=display:none><h3>PayFast</h3><form method='post' action='/payfast_pay'><input name='amount' type='number' value='50' min='10' max='5000' required><button class='btn btn-blue'>PAY WITH PAYFAST</button></form></div>
    <div id='eft' class='tabcontent' style=display:none><h3>EFT TymeBank 51088331090</h3><form method='post' action='/load_eft'><button name='amount' value='50' class='btn btn-dark'>R50</button><button name='amount' value='100' class='btn btn-dark'>R100</button></form></div><br><button class='btn' style=background:gray;color:white onclick="location.href='/menu'">BACK</button></div>"""

@app.route('/redeem_voucher', methods=['POST'])
def redeem_voucher():
    if 'uid' not in session: return redirect('/login')
    raw=request.form['code'].strip()
    code=raw.replace(" ","").replace("-","")
    vtype=request.form.get('voucher_type','BLU')
    v=Voucher.query.filter_by(code=code.upper()).first()
    if v and not v.is_used:
        user=User.query.get(session['uid']); user.balance+=v.amount; v.is_used=True; v.used_by=user.username; db.session.commit()
        return STYLE+f"<div class=card><h2>✅ R{v.amount} ADDED!</h2><p>Balance: R{user.balance:.2f}</p><button class='btn btn-gold' onclick=\"location.href='/menu'\">MENU</button></div>"
    if v and v.is_used:
        return STYLE+f"<div class=card><p style=color:red>❌ Already used by {v.used_by}</p><button onclick=\"location.href='/load'\">Back</button></div>"
    if len(code)<8:
        return STYLE+f"<div class=card><p style=color:red>❌ PIN min 8 digits</p><button onclick=\"location.href='/load'\">Back</button></div>"
    amount=10
    if "1000" in code: amount=1000
    elif "500" in code: amount=500
    elif "200" in code: amount=200
    elif "100" in code: amount=100
    elif "50" in code: amount=50
    elif "20" in code: amount=20
    user=User.query.get(session['uid'])
    exist=Payment.query.filter_by(ref=f"{vtype}-{code}", status="Pending").first()
    if exist:
        return STYLE+f"<div class=card><p style=color:orange>⏳ Already submitted, waiting admin</p><button onclick=\"location.href='/menu'\">Menu</button></div>"
    p=Payment(user_id=user.id, username=user.username, amount=amount, ref=f"{vtype}-{code}", status="Pending", method=vtype)
    db.session.add(p); db.session.commit()
    return STYLE+f"<div class=card><h2>⏳ {vtype} Received!</h2><p>Claimed: R{amount}</p><p style=color:orange>Admin verifies in 5 mins.</p><button class='btn btn-gold' onclick=\"location.href='/menu'\">MENU</button></div>"

@app.route('/load_eft', methods=['POST'])
def load_eft():
    if 'uid' not in session: return redirect('/login')
    try: amt=int(request.form['amount'])
    except: amt=50
    if amt<10 or amt>5000: amt=50
    ref=f"MCHA-{random.randint(100000,999999)}"
    p=Payment(user_id=session['uid'], username=session['uname'], amount=amt, ref=ref, method="EFT"); db.session.add(p); db.session.commit()
    return STYLE+f"<div class=card><h2>EFT R{amt}</h2><p>Ref: <b>{ref}</b></p><p>Bank: TymeBank 51088331090<br>Use Ref.</p><button onclick=\"location.href='/menu'\">Menu</button></div>"

@app.route('/payfast_pay', methods=['POST'])
def payfast_pay():
    if 'uid' not in session: return redirect('/login')
    try: amount=float(request.form['amount'])
    except: amount=50
    if amount<10 or amount>5000: amount=50
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
def payfast_return(): return STYLE+"<div class=card><h2>✅ Payment Received!</h2><button class='btn btn-gold' onclick=\"location.href='/menu'\">Menu</button></div>"
@app.route('/payfast_cancel')
def payfast_cancel(): return STYLE+"<div class=card><h2>❌ Cancelled</h2><button onclick=\"location.href='/load'\">Back</button></div>"
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
    if request.method=='POST':
        try: amt=int(float(request.form['amount']))
        except: amt=0
        acc=request.form['account'].strip()
        if amt<50 or amt>user.balance or len(acc)<6:
            return STYLE+f"<div class=card><p style=color:red>Invalid - Min R50</p><button onclick=\"location.href='/withdraw'\">Back</button></div>"
        user.balance-=amt; p=Payment(user_id=user.id, username=user.username, amount=amt, ref=acc, status="Pending", method="Withdraw"); db.session.add(p); db.session.commit()
        return STYLE+f"<div class=card><h2>✅ Withdraw R{amt} pending</h2><button onclick=\"location.href='/menu'\">Menu</button></div>"
    return STYLE+f"""<div class=card><h2>WITHDRAW</h2><p>Balance R{user.balance:.2f}</p><form method='post'><input name='amount' type='number' min='50' max='{int(user.balance)}' required><input name='account' placeholder='Bank acc + name' required><button class='btn btn-orange'>Withdraw</button></form><button class='btn' style=background:gray onclick="location.href='/menu'">BACK</button></div>"""

@app.route('/my_tickets')
def my_tickets():
    if 'uid' not in session: return redirect('/login')
    tickets=Ticket.query.filter_by(user_id=session['uid']).order_by(Ticket.id.desc()).all()
    html="".join([f"<div style=text-align:left;padding:6px;border-bottom:1px solid #eee>#{t.id} {t.numbers}+W{t.wing} R{t.bet}</div>" for t in tickets]) or "No tickets"
    return STYLE+f"<div class=card><h2>My Tickets</h2><div>{html}</div><br><button class='btn btn-gold' onclick=\"location.href='/menu'\">Menu</button></div>"

@app.route('/results')
def results():
    draws=Draw.query.order_by(Draw.id.desc()).limit(10).all()
    html="".join([f"<div style=padding:6px;border-bottom:1px solid #eee>{d.date} - {d.numbers}+W{d.wing}</div>" for d in draws]) or "No results"
    return STYLE+f"<div class=card><h2>Results</h2><div>{html}</div><br><button onclick=\"location.href='/menu'\">Menu</button></div>"

@app.route('/admin')
def admin():
    if request.args.get('key')!='mochaina123': return STYLE+"<div class=card>Wrong key! Add?key=mochaina123</div>"
    pays=Payment.query.filter_by(status="Pending").order_by(Payment.id.desc()).all()
    vouchers=Voucher.query.filter_by(is_used=False).all()
    ph="".join([f"<div style=text-align:left;padding:8px;border:1px solid #eee;margin:4px>{p.id} {p.username} R{p.amount} {p.method} {p.ref} <a href='/approve/{p.id}?key=mochaina123' style=background:green;color:white;padding:4px 8px;border-radius:6px;text-decoration:none>APPROVE</a> <a href='/reject/{p.id}?key=mochaina123' style=background:red;color:white;padding:4px 8px;border-radius:6px;text-decoration:none>REJECT</a></div>" for p in pays]) or "No pending"
    vh="".join([f"<div>{v.code} = R{v.amount}</div>" for v in vouchers]) or "No vouchers"
    total_users=User.query.count()
    total_bal=db.session.query(db.func.sum(User.balance)).scalar() or 0
    return STYLE+f"""<div class=card><h2>ADMIN - R{get_jackpot():,.2f}</h2><p>Users: {total_users} | Total Bal: R{total_bal:.2f}</p><h3>Pending</h3><div>{ph}</div><h3>Unused Vouchers</h3><div>{vh}</div><br><form method='post' action='/admin_gen_voucher?key=mochaina123'><input name='code' placeholder='MOCHA-100-XXX' required><input name='amount' type='number' min='1' max='5000' required><button class='btn btn-blue'>CREATE VOUCHER</button></form><br><button class='btn btn-red' onclick="location.href='/admin_draw/now?key=mochaina123'">DO DRAW NOW</button><br><br><button class='btn' style=background:gray onclick="location.href='/menu'">Menu</button></div>"""

@app.route('/admin_gen_voucher', methods=['POST'])
def admin_gen_voucher():
    if request.args.get('key')!='mochaina123': return "key?"
    code=request.form['code'].upper().strip()
    try: amount=int(float(request.form['amount']))
    except: amount=0
    if amount>0 and amount<=5000 and not Voucher.query.filter_by(code=code).first(): db.session.add(Voucher(code=code, amount=amount)); db.session.commit()
    return redirect('/admin?key=mochaina123')

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

@app.route('/admin_draw/<t>')
def admin_draw(t):
    if request.args.get('key')!='mochaina123': return "key?"
    win=sorted(random.sample(range(1,37),4)); wing=random.randint(1,4)
    d=Draw(numbers=",".join(map(str,win)), wing=wing, date=datetime.now().strftime("%Y-%m-%d %H:%M")); db.session.add(d); db.session.commit()
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
    try:
        with open("last_draw.txt","w") as f: f.write(datetime.now().isoformat())
    except: pass
    return STYLE+f"<div class=card><h2>DRAW {','.join(map(str,win))}+W{wing}</h2><button onclick=\"location.href='/admin?key=mochaina123'\">Admin</button></div>"

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
