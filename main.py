import os
import re
import json
import asyncio
import subprocess
import urllib.parse
import edge_tts
from flask import Flask, render_template_string, request, jsonify, send_file
from groq import Groq

app = Flask(__name__)

GROQ_API_KEY = "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".strip()
client = Groq(api_key=GROQ_API_KEY)

VOICE = "hi-IN-SwaraNeural"
VOICE_FILE = "/data/data/com.termux/files/home/neko_voice.mp3"

APP_MAP = {
    "instagram": {"pkg": "com.instagram.android", "scheme": "instagram://app"},
    "insta": {"pkg": "com.instagram.android", "scheme": "instagram://app"},
    "whatsapp": {"pkg": "com.whatsapp", "scheme": "whatsapp://"},
    "youtube": {"pkg": "com.google.android.youtube", "scheme": "vnd.youtube://"},
    "chrome": {"pkg": "com.android.chrome", "scheme": "googlechrome://"}
}

chat_history = [
    {
        "role": "system",
        "content": (
            "You are Ada, an affectionate, sweet anime companion. "
            "Always call user 'Boss'. Keep replies soft, sweet, caring in 1 short Hinglish sentence without emojis or symbols."
        )
    }
]

async def generate_voice(text):
    clean = re.sub(r'[^a-zA-Z0-9\s,.]', '', text).strip()
    if not clean:
        return
    communicate = edge_tts.Communicate(clean, VOICE, rate="+16%", pitch="+11Hz")
    await communicate.save(VOICE_FILE)

def get_latest_messages():
    try:
        res = subprocess.run(["termux-notification-list"], capture_output=True, text=True, timeout=4)
        notifs = json.loads(res.stdout) if res.stdout else []
        found = []
        for n in notifs:
            pkg = n.get("packageName", "").lower()
            title = n.get("title", "")
            content = n.get("content", "")
            if not title or not content:
                continue
            if "whatsapp" in pkg:
                found.append(f"WhatsApp par {title} ka message aaya hai: {content}")
            elif "instagram" in pkg:
                found.append(f"Instagram par {title} ka message aaya hai: {content}")
        if found:
            return "Boss, " + ". Aur ".join(found[:2])
        return "Boss, WhatsApp ya Instagram par abhi koi naya message nahi hai."
    except Exception:
        return "Boss, notification access check kar lijiye."

def reply_whatsapp(msg):
    os.system(f'am start -a android.intent.action.SEND -t text/plain -e android.intent.extra.TEXT "{msg}" com.whatsapp > /dev/null 2>&1 &')
    return f"Boss, WhatsApp reply draft ready kar diya hai: {msg}"

def reply_instagram(user, msg):
    target = f"https://ig.me/m/{user}" if user else "https://instagram.com/direct/inbox/"
    os.system(f'termux-open-url "{target}" > /dev/null 2>&1 &')
    return f"Boss, Instagram Direct open kar diya hai, message bhej dijiye: {msg}"

def launch_target_app(name):
    info = APP_MAP.get(name)
    if not info:
        return None
    pkg = info["pkg"]
    os.system(f"am start --user 0 -n {pkg}/.MainActivity > /dev/null 2>&1 || monkey -p {pkg} -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1 &")
    return info["scheme"]

def resolve_command(cmd):
    c = cmd.lower().strip()
    if any(k in c for k in ["check", "padho", "kiska", "kis ka", "notification", "unread"]):
        if "whatsapp" in c or "instagram" in c or "insta" in c or "msg" in c or "message" in c:
            return get_latest_messages(), None
    if "reply" in c:
        if "insta" in c or "instagram" in c:
            user_match = re.search(r'(?:to|for|ko)\s+([a-zA-Z0-9._]+)', c)
            target_user = user_match.group(1) if user_match else ""
            return reply_instagram(target_user, "Theek hai Boss"), None
        else:
            parts = c.split("reply")
            reply_body = parts[-1].replace("do", "").replace("karo", "").strip() if len(parts) > 1 else "Theek hai Boss"
            return reply_whatsapp(reply_body), None
    for key in APP_MAP:
        if f"open {key}" in c or (key in c and any(w in c for w in ["khol", "chalao", "start"])):
            scheme = launch_target_app(key)
            return f"{key.capitalize()} open kar diya Boss!", scheme
    if c.startswith("play ") or "gana" in c:
        song = c.replace("play ", "").replace("gana", "").strip()
        q_enc = urllib.parse.quote(song)
        target_url = f"https://www.youtube.com/results?search_query={q_enc}"
        os.system(f'termux-open-url "{target_url}" > /dev/null 2>&1 &')
        return f"{song.capitalize()} chala diya Boss!", target_url
    if "torch on" in c or c == "torch":
        os.system("termux-torch on > /dev/null 2>&1")
        return "Torch on kar di hai Boss!", None
    if "torch off" in c:
        os.system("termux-torch off > /dev/null 2>&1")
        return "Torch band kar di hai Boss!", None
    return None, None

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Ada - Ultimate Voice AI Companion</title>
<script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
<script src="https://cdn.jsdelivr.net/gh/duskfallcrew/live2d-core@latest/dist/live2d.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/5.3.12/pixi.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/cubism4.min.js"></script>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body {
    margin: 0; padding: 0; width: 100%; height: 100dvh;
    background: radial-gradient(circle at 50% 30%, #2e163d 0%, #15091e 60%, #08030d 100%);
    color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden;
  }
  .hud-header {
    position: fixed; top: 0; left: 0; right: 0; height: 48px;
    display: flex; justify-content: space-between; align-items: center; padding: 0 10px; z-index: 100;
    background: rgba(14, 6, 20, 0.65); backdrop-filter: blur(8px);
  }
  .title-tag { font-size: 13px; font-weight: 800; color: #ff77a9; letter-spacing: 1.2px; }
  .control-group { display: flex; gap: 4px; }
  .action-btn {
    background: rgba(255, 119, 169, 0.18); border: 1px solid #ff77a9; color: #ffd1e3;
    padding: 3px 6px; border-radius: 10px; font-size: 10px; font-weight: 600; cursor: pointer;
  }
  .action-btn.active { background: #ff77a9; color: #1a0826; }
  .canvas-wrap {
    position: fixed; top: 48px; left: 0; right: 0; bottom: 125px;
    display: flex; align-items: center; justify-content: center; z-index: 1; overflow: hidden;
  }
  #live2dCanvas { width: 100%; height: 100%; display: block; }
  .bottom-container {
    position: fixed; bottom: 0; left: 0; right: 0; padding: 8px 12px 14px 12px;
    display: flex; flex-direction: column; align-items: center; gap: 6px; z-index: 100;
    background: linear-gradient(to top, rgba(8, 3, 13, 0.95) 75%, transparent);
  }
  .dialogue-box {
    width: 100%; max-width: 420px; min-height: 40px;
    background: rgba(20, 10, 32, 0.9); backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 119, 169, 0.45); border-radius: 14px;
    padding: 8px 12px; text-align: center; font-size: 13px; color: #fce4ec;
  }
  .input-bar { width: 100%; max-width: 420px; display: flex; gap: 6px; align-items: center; }
  input[type="text"] {
    flex: 1; background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 119, 169, 0.35);
    border-radius: 25px; padding: 10px 14px; color: #fff; font-size: 13.5px; outline: none;
  }
  button.send-btn {
    background: linear-gradient(135deg, #ff758c 0%, #ff7eb3 100%); border: none;
    border-radius: 25px; padding: 10px 16px; font-weight: 700; color: #1a0826; cursor: pointer;
  }
  button.mic-btn {
    border-radius: 50%; width: 40px; height: 40px; padding: 0; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; background: #00e5ff; color: #000; border: none;
  }
  button.mic-btn.listening { background: #ff1744; box-shadow: 0 0 15px #ff1744; }
</style>
</head>
<body>
<div class="hud-header">
  <div class="title-tag">ADA AI</div>
  <div class="control-group">
    <button class="action-btn" id="girlBtn" onclick="cycleGirl()">👧 Girl (1/6)</button>
    <button class="action-btn" id="dressBtn" onclick="cycleDress()">👗 Dress (1/10)</button>
    <button class="action-btn active" id="btnStand" onclick="setPose('stand')">Stand</button>
    <button class="action-btn" id="btnSit" onclick="setPose('sit')">Sit</button>
    <button class="action-btn" id="btnSleep" onclick="setPose('sleep')">Sleep</button>
  </div>
</div>
<div class="canvas-wrap"><canvas id="live2dCanvas"></canvas></div>
<div class="bottom-container">
  <div class="dialogue-box" id="msgBox">Hello Boss! Main Ada hoon. "Ada" boliye ya type kijiye!</div>
  <div class="input-bar">
    <input type="text" id="userInput" placeholder="Boliye 'Ada' ya type kijiye..." onkeydown="if(event.key==='Enter') sendAction()">
    <button class="send-btn" onclick="sendAction()">Send</button>
    <button class="mic-btn" id="micBtn" onclick="toggleMic()">🎤</button>
  </div>
</div>
<audio id="nekoAudio" crossorigin="anonymous" preload="auto"></audio>
<script>
  let nekoModel = null, appPixi = null, audioContext = null, analyser = null, audioSource = null;
  let isSpeaking = false, currentMouthY = 0, currentPose = 'stand', baseWidth = 0, baseHeight = 0, breathCounter = 0;
  const audioElement = document.getElementById('nekoAudio');
  const characters = [
    { name: "Hiyori", url: "https://fastly.jsdelivr.net/gh/Live2D/CubismWebSamples/Samples/Resources/Hiyori/Hiyori.model3.json", dresses: [{name:"Sailor", filter:"none"}, {name:"Pink", filter:"hue-rotate(330deg) saturate(1.8)"}] },
    { name: "Mao", url: "https://fastly.jsdelivr.net/gh/Live2D/CubismWebSamples/Samples/Resources/Mao/Mao.model3.json", dresses: [{name:"Hoodie", filter:"none"}, {name:"Neon", filter:"hue-rotate(180deg) saturate(2.4)"}] },
    { name: "Haru", url: "https://fastly.jsdelivr.net/gh/Live2D/CubismWebSamples/Samples/Resources/Haru/Haru.model3.json", dresses: [{name:"Kimono", filter:"none"}, {name:"Ruby", filter:"hue-rotate(340deg) saturate(2.5)"}] },
    { name: "Shizuku", url: "https://fastly.jsdelivr.net/gh/duskfallcrew/live2d-core@latest/Sample/assets/shizuku/shizuku.model.json", dresses: [{name:"Maid", filter:"none"}, {name:"Pink", filter:"hue-rotate(330deg) saturate(1.8)"}] },
    { name: "Koharu", url: "https://fastly.jsdelivr.net/gh/duskfallcrew/live2d-core@latest/Sample/assets/koharu/koharu.model.json", dresses: [{name:"Frock", filter:"none"}, {name:"Berry", filter:"hue-rotate(320deg) saturate(2.2)"}] },
    { name: "Natori", url: "https://fastly.jsdelivr.net/gh/Live2D/CubismWebSamples/Samples/Resources/Natori/Natori.model3.json", dresses: [{name:"Armor", filter:"none"}, {name:"Cyber", filter:"hue-rotate(180deg) saturate(2.3)"}] }
  ];
  let girlIndex = 0, dressIndex = 0;
  function updateDressUI() {
    const curGirl = characters[girlIndex], curDress = curGirl.dresses[dressIndex];
    document.getElementById('live2dCanvas').style.filter = curDress.filter;
    document.getElementById('dressBtn').innerText = "👗 Dress (" + (dressIndex + 1) + "/2)";
  }
  function cycleDress() {
    dressIndex = (dressIndex + 1) % characters[girlIndex].dresses.length;
    updateDressUI();
  }
  async function loadCharacter(index) {
    dressIndex = 0;
    document.getElementById('girlBtn').innerText = "👧 " + characters[index].name + " (" + (index + 1) + "/6)";
    if (nekoModel) { appPixi.stage.removeChild(nekoModel); nekoModel.destroy(); nekoModel = null; }
    try {
      nekoModel = await PIXI.live2d.Live2DModel.from(characters[index].url);
      appPixi.stage.addChild(nekoModel); nekoModel.anchor.set(0.5, 0.5);
      applyPoseTransform(currentPose); updateDressUI();
    } catch(e) {}
  }
  function cycleGirl() { girlIndex = (girlIndex + 1) % characters.length; loadCharacter(girlIndex); }
  function initAudioContext() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioContext.createAnalyser(); analyser.fftSize = 256;
      audioSource = audioContext.createMediaElementSource(audioElement);
      audioSource.connect(analyser); analyser.connect(audioContext.destination);
    }
    if (audioContext.state === 'suspended') audioContext.resume();
  }
  function applyPoseTransform(pose) {
    if (!nekoModel) return;
    if (pose === 'stand') { nekoModel.rotation = 0; nekoModel.x = baseWidth/2; nekoModel.y = baseHeight*0.48; nekoModel.scale.set(Math.min(baseWidth/nekoModel.width, (baseHeight*0.88)/nekoModel.height)); }
    else if (pose === 'sit') { nekoModel.rotation = 0.04; nekoModel.x = baseWidth/2; nekoModel.y = baseHeight*0.62; nekoModel.scale.set(Math.min(baseWidth/nekoModel.width, (baseHeight*0.88)/nekoModel.height)*1.25); }
    else if (pose === 'sleep') { nekoModel.rotation = -Math.PI/2.15; nekoModel.x = baseWidth*0.50; nekoModel.y = baseHeight*0.48; nekoModel.scale.set(Math.min(baseWidth/nekoModel.width, (baseHeight*0.88)/nekoModel.height)*0.95); }
  }
  function setPose(pose) {
    currentPose = pose;
    document.querySelectorAll('.control-group .action-btn').forEach(b => { if(b.id && b.id.startsWith('btn')) b.classList.remove('active'); });
    const btn = document.getElementById('btn' + pose.charAt(0).toUpperCase() + pose.slice(1));
    if (btn) btn.classList.add('active');
    applyPoseTransform(pose);
  }
  async function initLive2D() {
    const canvas = document.getElementById('live2dCanvas');
    baseWidth = canvas.parentElement.clientWidth; baseHeight = canvas.parentElement.clientHeight;
    appPixi = new PIXI.Application({ view: canvas, transparent: true, autoDensity: true, resolution: window.devicePixelRatio || 1, width: baseWidth, height: baseHeight });
    await loadCharacter(0);
    appPixi.ticker.add(() => {
      if (!nekoModel || !nekoModel.internalModel) return;
      breathCounter += 0.035;
      let targetMouth = 0;
      if (isSpeaking && analyser) {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        let sum = 0; for (let i = 0; i < 24; i++) sum += dataArray[i];
        let avg = sum / 24; if (avg > 10) targetMouth = Math.min(1.0, (avg - 10) / 38.0);
      }
      currentMouthY += (targetMouth - currentMouthY) * 0.45;
      try {
        const core = nekoModel.internalModel.coreModel;
        if (core && core.setParameterValueById) {
          core.setParameterValueById('ParamMouthOpenY', currentMouthY);
          core.setParameterValueById('PARAM_MOUTH_OPEN_Y', currentMouthY);
        }
      } catch(e) {}
    });
    setupSpeechRecognition();
  }
  window.addEventListener('DOMContentLoaded', initLive2D);
  function playAudioWithLipSync(url) {
    initAudioContext();
    audioElement.src = url + '?t=' + Date.now();
    audioElement.play().then(() => { isSpeaking = true; }).catch(e => {});
    audioElement.onended = () => { isSpeaking = false; currentMouthY = 0; if (isListening && recognition) try { recognition.start(); } catch(e){} };
  }
  let recognition = null, isListening = false;
  function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR(); recognition.continuous = true; recognition.interimResults = false; recognition.lang = 'hi-IN';
      recognition.onresult = (e) => {
        const text = e.results[e.results.length - 1][0].transcript.trim().toLowerCase();
        if (text.includes("ada") || text.includes("aada") || isListening) {
          let cmd = text.replace("ada", "").replace("aada", "").trim();
          if (cmd) { document.getElementById('userInput').value = cmd; sendAction(cmd); }
        }
      };
      recognition.onerror = () => { isListening = false; };
      recognition.onend = () => { if (isListening && !isSpeaking) try { recognition.start(); } catch(e){} };
    }
  }
  function toggleMic() {
    initAudioContext(); const btn = document.getElementById('micBtn');
    if (!recognition) return alert("Microphone support nahi hai");
    if (!isListening) { isListening = true; btn.classList.add('listening'); try { recognition.start(); } catch(e){} document.getElementById('msgBox').innerText = "Active! 'Ada' boliye..."; }
    else { isListening = false; btn.classList.remove('listening'); try { recognition.stop(); } catch(e){} document.getElementById('msgBox').innerText = "Paused."; }
  }
  async function sendAction(override) {
    initAudioContext();
    const input = document.getElementById('userInput');
    const val = override || input.value.trim();
    if (!val) return; input.value = '';
    const low = val.toLowerCase();
    if (low.includes("girl") || low.includes("ladki")) { cycleGirl(); return; }
    if (low.includes("dress")) { cycleDress(); return; }
    if (low.includes("baith") || low.includes("sit")) { setPose('sit'); return; }
    if (low.includes("let") || low.includes("sleep")) { setPose('sleep'); return; }
    if (low.includes("khadi") || low.includes("stand")) { setPose('stand'); return; }
    document.getElementById('msgBox').innerText = "Processing...";
    try {
      const res = await fetch('/ask', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({query: val}) });
      const data = await res.json();
      document.getElementById('msgBox').innerText = data.reply;
      playAudioWithLipSync('/audio');
      if (data.scheme) setTimeout(() => { window.location.href = data.scheme; }, 1200);
    } catch(e) { document.getElementById('msgBox').innerText = "Error."; }
  }
</script>
</body>
</html>
"""

@app.route("/")
def index(): return render_template_string(HTML_PAGE)

@app.route("/audio")
def audio():
    if os.path.exists(VOICE_FILE): return send_file(VOICE_FILE, mimetype="audio/mpeg")
    return ("", 204)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    q = data.get("query", "").strip()
    if not q: return jsonify({"reply": "", "scheme": None})
    reply, scheme = resolve_command(q)
    if reply:
        asyncio.run(generate_voice(reply))
        return jsonify({"reply": reply, "scheme": scheme})
    chat_history.append({"role": "user", "content": q})
    if len(chat_history) > 6: chat_history[:] = [chat_history[0]] + chat_history[-4:]
    try:
        completion = client.chat.completions.create(model="llama3-8b-8192", messages=chat_history, max_tokens=55, temperature=0.75)
        ans = completion.choices[0].message.content.strip()
        chat_history.append({"role": "assistant", "content": ans})
    except Exception:
        ans = "Boss, main hamesha aapke saath hoon!"
    asyncio.run(generate_voice(ans))
    return jsonify({"reply": ans, "scheme": None})

if __name__ == "__main__":
    os.system("(sleep 1 && termux-open-url http://127.0.0.1:5000) &")
    app.run(host="0.0.0.0", port=5000, debug=False)
