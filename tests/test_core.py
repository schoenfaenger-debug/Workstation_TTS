import tempfile, unittest
from pathlib import Path
from core import EventFilter, EventNormalizer, LiveEvent, SettingsStore, speech_for

class CoreTests(unittest.TestCase):
 def test_normalizes_comment(self):
  e=EventNormalizer().normalize({"messages":[{"type":"chat","user":{"nickname":"Anna","id":"1"},"text":"Hallo"}]})[0]
  self.assertEqual((e.type,e.nickname,e.comment),("comment","Anna","Hallo"))
 def test_settings_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   s=SettingsStore(Path(d)/"settings.json"); s.save({"volume":80}); self.assertEqual(s.load()["volume"],80)
 def test_filter_and_speech(self):
  settings={"max_comment_length":20,"cooldown":0,"blocked_words":"böse","say_username":True,"max_nickname_length":4,"like_threshold":10}
  self.assertTrue(EventFilter().allow(LiveEvent(type="comment",nickname="Anna",comment="Hallo"),settings)); self.assertFalse(EventFilter().allow(LiveEvent(type="comment",comment="böse"),settings)); self.assertEqual(speech_for(LiveEvent(type="comment",nickname="Anna",comment="Hi"),settings),"Anna schreibt: Hi")
if __name__=="__main__": unittest.main()
