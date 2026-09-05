from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>MOCHAINA LOTTO LIVE 🔥</h1>
    <p>Welcome! Vouchers: MOCHA-100</p>
    <a href="/admin">Admin</a>
    '''

@app.route('/admin')
def admin():
    return '<h2>Admin Panel - Create vouchers here</h2>'

if __name__ == '__main__':
    app.run()
