<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Color Wheel - GitHub</title>
<style>
*{box-sizing:border-box}
body{background:#020617;color:white;font-family:Arial;text-align:center;margin:0;padding:10px}
.card{background:white;color:#0f172a;border-radius:20px;padding:18px;max-width:420px;margin:10px auto;box-shadow:0 10px 30px rgba(0,0,0,0.5)}
.btn{border:none;padding:14px;border-radius:12px;font-weight:900;width:100%;cursor:pointer;margin:6px 0;font-size:14px}
.btn-gold{background:linear-gradient(90deg,#facc15,#f97316);color:black}
.btn-purple{background:#9333ea;color:white}
.btn-dark{background:#14532d;color:white}
.color-btn{padding:14px 4px;border-radius:12px;border:3px solid white;font-weight:900;font-size:12px;cursor:pointer;color:white;text-shadow:0 1px 2px black}
.color-btn.selected{border-color:#000;transform:scale(1.08);box-shadow:0 4px 12px rgba(0,0,0,0.4)}
#wheel{will-change:transform}
</style>
</head>
<body>
<div class="card">
<h2 style="margin:0 0 6px 0">🎡 COLOR WHEEL - GITHUB</h2>
<div style="background:#0f172a;color:#facc15;padding:10px;border-radius:12px;font-weight:900;margin:8px 0">⏳ AUTO SPIN: <span id="countdown">8</span>s | Balance: R<span id="bal">100</span></div>

<div style="position:relative;width:300px;height:300px;margin:12px auto">
<div style="position:absolute;top:-12px;left:50%;transform:translateX(-50%);font-size:38px;z-index:10;line-height:1">👇</div>
<div id="wheel" style="width:100%;height:100%;border-radius:50%;border:8px solid #facc15;background:white;overflow:hidden;transform:rotate(0deg)">
<svg viewBox="0 0 200 200" style="width:100%;height:100%" id="wheelSvg"></svg>
</div>
</div>

<div id="lastWin" style="font-weight:900;font-size:14px;margin:6px 0">Last: -</div>
<div id="myBet" style="background:#fef9c3;padding:8px;border-radius:10px;font-weight:800;margin:6px 0;font-size:13px">Bet: -</div>

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px">
<button class="color-btn" style="background:#dc2626" onclick="pick('RED',2,this)">RED x2</button>
<button class="color-btn" style="background:#facc15;color:#000;text-shadow:none" onclick="pick('YEL',3,this)">YEL x3</button>
<button class="color-btn" style="background:#16a34a" onclick="pick('GREEN',2.5,this)">GREEN x2.5</button>
<button class="color-btn" style="background:#2563eb" onclick="pick('BLUE',2.5,this)">BLUE x2.5</button>
<button class="color-btn" style="background:#f97316" onclick="pick('ORG',3,this)">ORG x3</button>
<button class="color-btn" style="background:#ec4899" onclick="pick('PINK',4,this)">PINK x4</button>
<button class="color-btn" style="background:#7c3aed" onclick="pick('PURP',6,this)">PURP x6</button>
<button class="color-btn" style="background:#0891b2" onclick="pick('CYAN',8,this)">CYAN x8</button>
</div>

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px">
<button class="btn btn-dark" onclick="setS(2)">R2</button>
<button class="btn btn-dark" onclick="setS(5)">R5</button>
<button class="btn btn-dark" onclick="setS(10)">R10</button>
<button class="btn btn-dark" onclick="setS(20)">R20</button>
</div>

<div id="stakeShow" style="font-weight:800;margin:6px 0;font-size:13px">Stake: R5</div>
<button id="betBtn" class="btn btn-gold" style="opacity:0.5" onclick="placeBet()">PICK COLOR FIRST</button>
<button class="btn btn-purple" onclick="doSpin()">🔥 SPIN NOW - 8 SPINS IN 2.2s</button>
<div id="winBox" style="font-weight:900;font-size:20px;min-height:28px;margin-top:8px"></div>
<div style="font-size:10px;color:#64748b;margin-top:10px">GitHub Pages Ready - No Server Needed</div>
</div>

<script>
const cols=["#dc2626","#facc15","#16a34a","#2563eb","#ea580c","#ec4899","#7c3aed","#06b6d4","#16a34a","#facc15","#dc2626","#06b6d4"];
const labels=["RED","YEL","GREEN","BLUE","ORG","PINK","PURP","CYAN","GREEN","YEL","RED","CYAN"];
let svg="";
for(let i=0;i<12;i++){
  let a1=(i*30-90)*Math.PI/180, a2=((i+1)*30-90)*Math.PI/180;
  let x1=100+95*Math.cos(a1), y1=100+95*Math.sin(a1);
  let x2=100+95*Math.cos(a2), y2=100+95*Math.sin(a2);
  svg+=`<path d="M100,100 L${x1.toFixed(1)},${y1.toFixed(1)} A95,95 0 0,1 ${x2.toFixed(1)},${y2.toFixed(1)} Z" fill="${cols[i]}" stroke="white" stroke-width="2.5"/>`;
  let mid=(i*30+15-90)*Math.PI/180;
  let tx=100+58*Math.cos(mid), ty=100+58*Math.sin(mid);
  svg+=`<text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" fill="white" font-size="9" font-weight="900" text-anchor="middle" dominant-baseline="middle" transform="rotate(${i*30+15} ${tx.toFixed(1)} ${ty.toFixed(1)})">${labels[i]}</text>`;
}
svg+=`<circle cx="100" cy="100" r="24" fill="#0f172a" stroke="white" stroke-width="3"/><circle cx="100" cy="100" r="10" fill="#facc15"/>`;
document.getElementById("wheelSvg").innerHTML=svg;

let sel=null, mult=2, stake=5, balance=100, timeLeft=8, spinning=false, cr=0, currentBet=null;

function setS(v){ stake=v; document.getElementById("stakeShow").innerText="Stake: R"+v+" on "+(sel||"-"); if(sel) enable(); }
function pick(c,m,el){ sel=c; mult=m; document.querySelectorAll(".color-btn").forEach(b=>b.classList.remove("selected")); el.classList.add("selected"); enable(); }
function enable(){ let b=document.getElementById("betBtn"); b.style.opacity="1"; b.innerText="LOCK R"+stake+" ON "+sel+" x"+mult; }
function placeBet(){
  if(!sel) return;
  if(stake>balance){ alert("No balance!"); return; }
  if(currentBet) balance+=currentBet.stake;
  balance-=stake;
  currentBet={color:sel,mult:mult,stake:stake};
  document.getElementById("bal").innerText=balance.toFixed(0);
  document.getElementById("myBet").innerText="Locked NEXT: R"+stake+" on "+sel+" x"+mult;
  document.getElementById("betBtn").innerText="BET LOCKED - GOOD LUCK!";
}

setInterval(()=>{ if(spinning) return; timeLeft--; if(timeLeft<0) timeLeft=0; document.getElementById("countdown").innerText=timeLeft; if(timeLeft<=0) doSpin(); },1000);

function doSpin(){
  if(spinning) return;
  spinning=true;
  let wheel=document.getElementById("wheel");
  let idx=Math.floor(Math.random()*12);
  let landed=labels[idx];
  let center=idx*30+15;
  let target=(360-center+360)%360;
  let start=cr;
  let total=2880+target; // 8 spins super fast
  let finalRot=start+total;
  let startTime=null;
  let duration=2200; // 2.2 seconds
  function easeOut(t){ return 1-Math.pow(1-t,3); }
  function animate(now){
    if(!startTime) startTime=now;
    let p=Math.min((now-startTime)/duration,1);
    let cur=start+total*easeOut(p);
    wheel.style.transform="rotate("+cur+"deg)";
    if(p<1) requestAnimationFrame(animate);
    else{
      cr=finalRot%360;
      wheel.style.transform="rotate("+cr+"deg)";
      document.getElementById("lastWin").innerText="Last: "+landed;
      if(currentBet && currentBet.color===landed){
        let win=currentBet.stake*currentBet.mult;
        balance+=win;
        document.getElementById("winBox").innerText="WON R"+win+"! 🎉 "+landed;
        document.getElementById("winBox").style.color="#16a34a";
      } else {
        document.getElementById("winBox").innerText=currentBet?"LOST - "+landed:"NO BET - "+landed;
        document.getElementById("winBox").style.color="#ef4444";
      }
      document.getElementById("bal").innerText=balance.toFixed(0);
      currentBet=null; sel=null;
      document.querySelectorAll(".color-btn").forEach(b=>b.classList.remove("selected"));
      document.getElementById("betBtn").style.opacity="0.5";
      document.getElementById("betBtn").innerText="PICK COLOR FIRST";
      document.getElementById("myBet").innerText="Bet: -";
      timeLeft=8;
      spinning=false;
    }
  }
  requestAnimationFrame(animate);
}
</script>
</body>
</html>
