import queue, subprocess, threading

class TTSQueue:
    def __init__(self):
        self.items = queue.Queue(); self._stop = threading.Event(); threading.Thread(target=self._run, daemon=True).start()
    def say(self, text, rate, volume, voice, language):
        if text: self.items.put((text, rate, volume, voice, language))
    def _run(self):
        while not self._stop.is_set():
            try: text, rate, volume, voice, language = self.items.get(timeout=.2)
            except queue.Empty: continue
            # Windows SAPI runs in a separate process so the UI remains responsive.
            script = "$s=New-Object -ComObject SAPI.SpVoice; $s.Volume=%d; $s.Rate=%d; if('%s'){ $s.Voice=(Get-ChildItem 'HKLM:\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens' | Where-Object {$_.PSChildName -like '*%s*'} | Select-Object -First 1).PSPath }; $s.Speak('%s')" % (volume, rate, voice.replace("'", ""), voice.replace("'", ""), text.replace("'", "''"))
            subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)
    def stop(self): self._stop.set()
