# Workstation TTS v1

Eigenständige Windows-11-App für TikTok-LIVE-Ereignisse und Text-to-Speech.
`MobileTTS` wird nicht verwendet oder verändert.

## Architektur

`TikTokConnector → EventNormalizer → LocalEventBus → Workstation TTS`

Der Connector überträgt ausschließlich rohe Euler-Stream-WebSocket-Nachrichten. Erst der Normalizer erzeugt die einheitlichen Events `comment`, `join`, `follow`, `share`, `like`, `gift` und `room`. Dadurch können spätere Module (GPT Co-Moderator, Spielleiter, Pferderennen, Zahlraten, Abstimmungen) direkt den LocalEventBus abonnieren, ohne eine zweite TikTok-Verbindung aufzubauen.

## Sicherheit

Der Euler-Key wird unter Windows getrennt von den Einstellungen mit DPAPI für den aktuellen Windows-Benutzer verschlüsselt gespeichert. Er ist nicht im Quellcode und nicht in `settings.json`.

## Windows-Build

Auf einem Windows-11-PC `build_windows.bat` doppelklicken. Alternativ erzeugt der GitHub-Workflow bei jedem Push ein Download-Artefakt `Workstation_TTS_v1.zip` mit `Workstation_TTS_v1.exe`.

## Hinweis zu v1

Die echte Verbindung nutzt `wss://ws.eulerstream.com?uniqueId=…&apiKey=…`. Für einen funktionierenden LIVE-Test muss der TikTok-Account gerade live sein und ein gültiger Euler-Key eingegeben werden.
