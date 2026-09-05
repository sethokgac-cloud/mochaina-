import os, random, string, datetime
from flask import Flask, render_template_string, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "mochaina-secret-2026"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mochaina.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    balance = db.Column(db.Float, default=0)
    is_admin = db.Column(db.Boolean, default=False)

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)
    amount = db.Column(db.Float)
    used = db.Column(db.Boolean, default=False)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    game = db.Column(db.String(50))
    numbers = db.Column(db.String(100))
    amount = db.Column(db.Float)
    win = db.Column(db.Float, default=0)
    date = db.Column(db.String(50))

class Withdraw(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    amount = db.Column(db.Float)
    method = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Pending")

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", balance=10000, is_admin=True))
        db.session.commit()
    if not Voucher.query.first():
        for amt in [20,50,100,200]:
            for _ in range(3):
                c=f"MOCHA-{amt}-{''.join(random.choices(string.ascii_uppercase+string.digits, k=4))}"
                db.session.add(Voucher(code=c, amount=amt))
        db.session.commit()

GAMES=[
 {"id":"quick5","name":"Daily Quick 5","desc":"Pick 5 numbers 1-36","price":5,"win":500,"color":"#16a34a"},
 {"id":"lucky3","name":"Lucky 3","desc":"Pick 3 numbers 1-10 - Win Fast!","price":2,"win":100,"color":"#eab308"},
 {"id":"jackpot","name":"MoChaina JACKPOT","desc":"Pick 6 numbers 1-49 - BIG WIN","price":10,"win":10000,"color":"#dc2626"},
]

BASE="""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoChaina Lotto</title>
<style>
body{font-family:Arial;background:#0f172a;color:white;margin:0}
.header{background:linear-gradient(90deg,#16a34a,#eab308);padding:15px;text-align:center;font-weight:bold;font-size:22px;color:#000}
.nav{display:flex;justify-content:space-around;background:#1e293b;padding:10px;position:sticky;top:0}
.nav a{color:white;text-decoration:none;font-weight:bold}
.card{background:#1e293b;margin:12px;border-radius:12px;padding:15px;border-left:5px solid #16a34a}
.btn{background:linear-gradient(90deg,#16a34a,#22c55e);border:none;padding:12px 20px;border-radius:8px;color:white;font-weight:bold;width:100%;font-size:16px;margin-top:8px}
.btn-gold{background:linear-gradient(90deg,#eab308,#facc15);color:black}
.input{width:100%;padding:12px;margin:6px 0;border-radius:8px;border:none;box-sizing:border-box}
.balance{background:#16a34a;padding:10px;border-radius:8px;text-align:center;margin:10px;font-size:16px}
</style></head><body>
<div class="header">🔥 MOCHAINA LOTTO - LIMPOPO #1 🔥</div>
<div class="balance">👤 {{session.get('user','Guest')}} | 💰 R{{ "%.2f"|format(balance) }} | <a href="/logout" style="color:white">Logout</a></div>
<div class="nav"><a href="/">Games</a><a href="/history">History</a><a href="/voucher">Voucher</a><a href="/withdraw">Withdraw</a><a href="/admin">Admin</a></div>
{{content|safe}}</body></html>
"""

@app.route('/')
def home():
    if 'user' not in session: return redirect('/login')
    u=User.query.filter_by(username=session['user']).first()
    content=""
    for g in GAMES:
        content+=f"<div class='card' style='border-left-color:{g['color']}'><h3>{g['name']}</h3><p>{g['desc']}</p><p>Bet R{g['price']} | Win R{g['win']}</p><a href='/play/{g['id']}'><button class='btn' style='background:{g['color']}'>PLAY NOW</button></a></div>"
    return render_template_string(BASE, content=content, balance=u.balance if u else 0)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username'].strip().lower()
        u=User.query.filter_by(username=username).first()
        if not u:
            u=User(username=username, balance=0)
            db.session.add(u); db.session.commit()
        session['user']=username
        return redirect('/')
    content="<div class='card'><h2>Welcome MoChaina Lotto</h2><form method='post'><input name='username' class='input' placeholder='Phone / Username' required><button class='btn'>ENTER & PLAY</button></form></div>"
    return render_template_string(BASE, content=content, balance=0)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

@app.route('/voucher', methods=['GET','POST'])
def voucher():
    if 'user' not in session: return redirect('/login')
    u=User.query.filter_by(username=session['user']).first()
    msg=""
    if request.method=='POST':
        code=request.form['code'].strip().upper()
        v=Voucher.query.filter_by(code=code, used=False).first()
        if v:
            u.balance+=v.amount; v.used=True; db.session.commit()
            msg=f"<p style='color:lightgreen'>Success! R{v.amount} added!</p>"
        else:
            msg="<p style='color:tomato'>Invalid / used!</p>"
    vouchers=Voucher.query.filter_by(used=False).limit(5).all() if u.is_admin else []
    vlist="<br>".join([f"{v.code} = R{v.amount}" for v in vouchers])
    content=f"<div class='card'><h3>💳 Redeem Voucher</h3>{msg}<form method='post'><input name='code' class='input' placeholder='MOCHA-100-XXXX' required><button class='btn btn-gold'>REDEEM</button></form><p>Admin vouchers:<br>{vlist}</p></div>"
    return render_template_string(BASE, content=content, balance=u.balance)

@app.route('/play/<game_id>', methods=['GET','POST'])
def play(game_id):
    if 'user' not in session: return redirect('/login')
    game=next((g for g in GAMES if g['id']==game_id), None)
    u=User.query.filter_by(username=session['user']).first()
    if request.method=='POST':
        if u.balance < game['price']:
            return render_template_string(BASE, content=f"<div class='card'><h3>Low Balance! Need R{game['price']}</h3><a href='/voucher'><button class='btn'>Buy Voucher</button></a></div>", balance=u.balance)
        nums=request.form['numbers']
        win=0
        if random.random() < 0.25:
            win=game['win'] if random.random()<0.1 else game['price']*5
            u.balance+=win-game['price']
            result=f"<h2 style='color:gold'>🎉 YOU WON R{win}!!!</h2>"
        else:
            u.balance-=game['price']
            result=f"<h2 style='color:tomato'>😢 Try Again!</h2>"
        t=Ticket(username=u.username, game=game['name'], numbers=nums, amount=game['price'], win=win, date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        db.session.add(t); db.session.commit()
        content=f"<div class='card'>{result}<p>{game['name']} - {nums}</p><a href='/'><button class='btn'>Play Again</button></a><a href='/history'><button class='btn btn-gold'>History</button></a></div>"
        return render_template_string(BASE, content=content, balance=u.balance)
    content=f"<div class='card'><h3>{game['name']}</h3><p>{game['desc']}</p><form method='post'><input name='numbers' class='input' placeholder='e.g 5,12,23,31,35' required><p>Price R{game['price']} | Bal R{u.balance:.2f}</p><button class='btn'>BET R{game['price']}</button></form></div>"
    return render_template_string(BASE, content=content, balance=u.balance)

@app.route('/history')
def history():
    if 'user' not in session: return redirect('/login')
    u=User.query.filter_by(username=session['user']).first()
    tickets=Ticket.query.filter_by(username=u.username).order_by(Ticket.id.desc()).limit(20).all()
    rows="".join([f"<tr><td>{t.game}</td><td>{t.numbers}</td><td>{t.amount}</td><td>{t.win}</td><td>{t.date}</td></tr>" for t in tickets])
    content=f"<div class='card'><h3>Your Tickets</h3><table style='width:100%;font-size:12px'><tr><th>Game</th><th>Nums</th><th>Bet</th><th>Win</th><th>Date</th></tr>{rows}</table></div>"
    return render_template_string(BASE, content=content, balance=u.balance)

@app.route('/withdraw', methods=['GET','POST'])
def withdraw():
    if 'user' not in session: return redirect('/login')
    u=User.query.filter_by(username=session['user']).first()
    msg=""
    if request.method=='POST':
        amt=float(request.form['amount']); method=request.form['method']
        if amt>u.balance: msg="<p style='color:tomato'>Insufficient</p>"
        else:
            u.balance-=amt; db.session.add(Withdraw(username=u.username, amount=amt, method=method)); db.session.commit()
            msg=f"<p style='color:lightgreen'>Withdraw R{amt} requested!</p>"
    content=f"<div class='card'><h3>💸 Withdraw</h3>{msg}<form method='post'><input name='amount' type='number' class='input' placeholder='Amount' required><input name='method' class='input' placeholder='Capitec number' required><button class='btn'>REQUEST</button></form></div>"
    return render_template_string(BASE, content=content, balance=u.balance)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if 'user' not in session: return redirect('/login')
    u=User.query.filter_by(username=session['user']).first()
    if not u.is_admin and session['user']!='admin':
        return render_template_string(BASE, content="<div class='card'><h3>Admin only</h3></div>", balance=u.balance)
    if request.method=='POST' and 'gen' in request.form:
        amt=float(request.form['amt']); qty=int(request.form['qty'])
        for _ in range(qty):
            c=f"MOCHA-{int(amt)}-{''.join(random.choices(string.ascii_uppercase+string.digits,k=5))}"
            db.session.add(Voucher(code=c, amount=amt))
        db.session.commit()
    vouchers=Voucher.query.filter_by(used=False).all()
    withdraws=Withdraw.query.filter_by(status="Pending").all()
    vlist="<br>".join([f"{v.code} - R{v.amount}" for v in vouchers[:30]])
    wlist="<br>".join([f"{w.username} R{w.amount} to {w.method} <a href='/admin/pay/{w.id}'>PAY</a>" for w in withdraws])
    content=f"<div class='card'><h3>ADMIN</h3><form method='post'><input type='hidden' name='gen' value='1'><input name='amt' class='input' placeholder='Amount 100'><input name='qty' class='input' placeholder='Qty 5'><button class='btn'>Generate</button></form><h4>Vouchers ({len(vouchers)})</h4><p style='font-size:12px'>{vlist}</p><h4>Withdraws</h4><p>{wlist}</p></div>"
    return render_template_string(BASE, content=content, balance=u.balance)

@app.route('/admin/pay/<int:id>')
def admin_pay(id):
    w=Withdraw.query.get(id)
    if w: w.status="Paid"; db.session.commit()
    return redirect('/admin')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
