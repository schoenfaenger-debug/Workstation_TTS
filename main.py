from __future__ import annotations
import json, os, queue, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlencode
import websocket
from core import EventFilter, EventNormalizer, LiveEvent, LocalEventBus, SettingsStore, speech_for
from secure_store import load_key, save_key
from tts import TTSQueue

APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "Workstation_TTS"
DEFAULTS = {"username":"", "language":"de-DE", "voice":"", "volume":100, "rate":0, "pitch":0, "say_username":True, "max_nickname_length":24, "cooldown":3, "max_comment_length":220, "blocked_words":"", "like_threshold":100, "sounds":{}}

class TikTokConnector:
    """Euler WebSocket transport. It ONLY emits raw provider messages."""
    def __init__(self, raw_callback, state_callback): self.raw_callback, self.state_callback, self.ws = raw_callback, state_callback, None
    def connect(self, username, api_key):
        uid = username.strip().lstrip("@")
        if not uid or not api_key: raise ValueError("TikTok-Benutzername und Euler API-Key sind erforderlich.")
        url = "wss://ws.eulerstream.com?" + urlencode({"uniqueId":uid, "apiKey":api_key})
        self.ws = websocket.WebSocketApp(url, on_open=lambda _:self.state_callback("Verbunden"), on_message=lambda _,m:self.raw_callback(json.loads(m)), on_error=lambda _,e:self.state_callback("Fehler: " + str(e)), on_close=lambda *_:self.state_callback("Getrennt"))
        threading.Thread(target=lambda:self.ws.run_forever(), daemon=True).start(); self.state_callback("Verbinde …")
    def disconnect(self):
        if self.ws: self.ws.close(); self.ws = None

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Workstation TTS v1"); self.geometry("1100x760"); self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.store=SettingsStore(APP_DIR/"settings.json"); self.settings={**DEFAULTS, **self.store.load()}; self.bus=LocalEventBus(); self.normalizer=EventNormalizer(); self.filter=EventFilter(); self.tts=TTSQueue(); self.event_queue=queue.Queue(); self.connector=TikTokConnector(self.event_queue.put, lambda x:self.event_queue.put(("state",x))); self.vars={}
        self._build(); self.bus.subscribe(self.handle_event); self.after(100,self.drain)
    def field(self, parent, key, label, value=None, kind="entry"):
        ttk.Label(parent,text=label).pack(anchor="w"); v=tk.BooleanVar(value=self.settings.get(key,False)) if kind=="check" else tk.StringVar(value=str(self.settings.get(key,"" if value is None else value)))
        self.vars[key]=v
        if kind=="check": ttk.Checkbutton(parent,variable=v,command=self.autosave).pack(anchor="w")
        elif kind=="combo": ttk.Combobox(parent,textvariable=v,values=value,state="readonly").pack(fill="x")
        else: ttk.Entry(parent,textvariable=v,show="•" if key=="api_key" else "").pack(fill="x")
        v.trace_add("write",lambda *_:self.autosave()); return v
    def _build(self):
        root=ttk.Frame(self,padding=10); root.pack(fill="both",expand=True); left=ttk.Frame(root); left.pack(side="left",fill="y"); right=ttk.Frame(root); right.pack(side="right",fill="both",expand=True)
        self.field(left,"username","TikTok-Benutzername"); self.field(left,"api_key","Euler API-Key"); self.vars["api_key"].set(load_key(APP_DIR/"euler.key")); ttk.Button(left,text="Verbinden",command=self.connect).pack(fill="x",pady=(8,2)); ttk.Button(left,text="Trennen",command=self.connector.disconnect).pack(fill="x")
        self.status=tk.StringVar(value="Getrennt"); ttk.Label(left,textvariable=self.status,font=("Segoe UI",11,"bold")).pack(pady=8)
        self.field(left,"language","Sprache",["de-DE","en-US","fr-FR"],"combo"); self.field(left,"voice","Stimme (Token-Teil)");
        for key,label,val in [("volume","Lautstärke 0–100",100),("rate","Geschwindigkeit -10–10",0),("pitch","Pitch (für spätere Engine)",0),("max_nickname_length","Max. Nickname-Länge",24),("cooldown","User-Cooldown Sekunden",3),("max_comment_length","Max. Kommentarlänge",220),("like_threshold","Likes ab",100)]: self.field(left,key,label,val)
        self.field(left,"say_username","Username + Kommentar vorlesen",kind="check"); self.field(left,"blocked_words","Spam- / Schimpfwörter (Komma getrennt)")
        ttk.Separator(left).pack(fill="x",pady=8); ttk.Label(left,text="Eigene Sounds (Datei je Ereignis)").pack(anchor="w")
        for typ in ("join","follow","share","like","gift"):
            ttk.Button(left,text=f"Sound: {typ}",command=lambda t=typ:self.pick_sound(t)).pack(fill="x")
        ttk.Button(left,text="ALLES BEENDEN",command=self.shutdown).pack(fill="x",pady=12)
        ttk.Label(right,text="Diagnose – normalisierte Events",font=("Segoe UI",12,"bold")).pack(anchor="w")
        self.log=tk.Text(right,height=30,state="disabled"); self.log.pack(fill="both",expand=True)
        tests=ttk.LabelFrame(right,text="Test-Events",padding=8); tests.pack(fill="x",pady=8)
        for typ in ("comment","join","follow","share","like","gift","room"): ttk.Button(tests,text=typ,command=lambda t=typ:self.test(t)).pack(side="left",padx=3)
    def current(self):
        out={k:v.get() for k,v in self.vars.items() if k!="api_key"}; out["sounds"]=self.settings.get("sounds",{}); return out
    def autosave(self):
        if hasattr(self,"store"): self.settings.update(self.current()); self.store.save(self.settings)
    def connect(self):
        try: save_key(APP_DIR/"euler.key",self.vars["api_key"].get()); self.autosave(); self.connector.connect(self.vars["username"].get(),self.vars["api_key"].get())
        except Exception as e: messagebox.showerror("Verbindung",str(e))
    def drain(self):
        while not self.event_queue.empty():
            payload=self.event_queue.get()
            if isinstance(payload,tuple): self.status.set(payload[1]); continue
            for event in self.normalizer.normalize(payload): self.bus.publish(event)
        self.after(100,self.drain)
    def test(self, typ):
        e=LiveEvent(type=typ,nickname="Testfahrer",userId="test",comment="Das ist ein Test-Kommentar.",likeCount=100,giftName="Rose",giftCount=1,viewerCount=42,roomId="Test-Raum"); self.bus.publish(e)
    def handle_event(self,e):
        self.write(json.dumps(e.__dict__,ensure_ascii=False)); s=self.current()
        if self.filter.allow(e,s): self.tts.say(speech_for(e,s),int(s["rate"]),int(s["volume"]),s["voice"],s["language"])
        sound=s.get("sounds",{}).get(e.type)
        if sound and os.name=="nt":
            try: import winsound; winsound.PlaySound(sound,winsound.SND_FILENAME|winsound.SND_ASYNC)
            except RuntimeError: pass
    def write(self,text): self.log.configure(state="normal"); self.log.insert("end",text+"\n"); self.log.see("end"); self.log.configure(state="disabled")
    def pick_sound(self,typ):
        f=filedialog.askopenfilename(filetypes=[("Audio","*.wav")]);
        if f: self.settings.setdefault("sounds",{})[typ]=f; self.autosave()
    def shutdown(self): self.autosave(); self.connector.disconnect(); self.tts.stop(); self.destroy()
if __name__=="__main__": App().mainloop()
