#!/usr/bin/env python3
"""
lgtv.py — Bedien je EIGEN LG webOS smart-tv via het officiele webOS-protocol.

Gebruik dit alleen op een tv die van jou is, op je eigen netwerk.
De tv vraagt bij de eerste verbinding op het scherm om toestemming; je moet
daar met de echte afstandsbediening op "Toestaan" klikken. Zonder die fysieke
bevestiging werkt er niets — dat is de ingebouwde beveiliging van webOS.

Werkt op moderne LG webOS-tv's (ongeveer 2014 en nieuwer).

Afhankelijkheid:
    pip install websocket-client

Voorbeelden:
    python3 lgtv.py --host 192.168.0.168 pair
    python3 lgtv.py --host 192.168.0.168 info
    python3 lgtv.py --host 192.168.0.168 volume 12
    python3 lgtv.py --host 192.168.0.168 mute on
    python3 lgtv.py --host 192.168.0.168 app com.webos.app.netflix
    python3 lgtv.py --host 192.168.0.168 notify "Hallo vanaf mijn laptop"
    python3 lgtv.py --host 192.168.0.168 off
"""

import argparse
import json
import os
import ssl
import sys
import uuid

try:
    import websocket  # van het pakket 'websocket-client'
except ImportError:
    sys.exit("Ontbrekende dependency. Installeer met:  pip install websocket-client")


# Waar de client-key wordt bewaard na het eenmalig koppelen.
KEYSTORE = os.path.join(os.path.expanduser("~"), ".lgtv_keys.json")

# Standaard registratie-payload voor webOS. Dit is de set rechten die de tv
# je vraagt goed te keuren wanneer je voor het eerst koppelt.
REGISTER_PAYLOAD = {
    "type": "register",
    "id": "register_0",
    "payload": {
        "forcePairing": False,
        "pairingType": "PROMPT",
        "manifest": {
            "manifestVersion": 1,
            "appVersion": "1.1",
            "signed": {
                "created": "20140509",
                "appId": "com.lge.test",
                "vendorId": "com.lge",
                "localizedAppNames": {"": "LG Remote (eigen gebruik)"},
                "localizedVendorNames": {"": "LG Electronics"},
                "permissions": [
                    "TEST_SECURE",
                    "CONTROL_INPUT_TEXT",
                    "CONTROL_MOUSE_AND_KEYBOARD",
                    "READ_INSTALLED_APPS",
                    "READ_LGE_SDX",
                    "READ_NOTIFICATIONS",
                    "SEARCH",
                    "WRITE_SETTINGS",
                    "WRITE_NOTIFICATION_ALERT",
                    "CONTROL_POWER",
                    "READ_CURRENT_CHANNEL",
                    "READ_RUNNING_APPS",
                    "READ_UPDATE_INFO",
                    "UPDATE_FROM_REMOTE_APP",
                    "READ_TV_CURRENT_TIME",
                ],
                "serial": "2f930e2d2cfe083771f68e4fe7bb07",
            },
            "permissions": [
                "LAUNCH",
                "LAUNCH_WEBAPP",
                "APP_TO_APP",
                "CLOSE",
                "TEST_OPEN",
                "TEST_PROTECTED",
                "CONTROL_AUDIO",
                "CONTROL_DISPLAY",
                "CONTROL_INPUT_JOYSTICK",
                "CONTROL_INPUT_MEDIA_RECORDING",
                "CONTROL_INPUT_MEDIA_PLAYBACK",
                "CONTROL_INPUT_TV",
                "CONTROL_POWER",
                "READ_APP_STATUS",
                "READ_CURRENT_CHANNEL",
                "READ_INPUT_DEVICE_LIST",
                "READ_NETWORK_STATE",
                "READ_RUNNING_APPS",
                "READ_TV_CHANNEL_LIST",
                "WRITE_NOTIFICATION_TOAST",
                "READ_POWER_STATE",
                "READ_COUNTRY_INFO",
            ],
        },
    },
}


def load_key(host):
    try:
        with open(KEYSTORE) as fh:
            return json.load(fh).get(host)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_key(host, key):
    data = {}
    try:
        with open(KEYSTORE) as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    data[host] = key
    with open(KEYSTORE, "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"[i] Client-key opgeslagen in {KEYSTORE}")


class LGTV:
    def __init__(self, host, secure=False, timeout=12):
        scheme, port = ("wss", 3001) if secure else ("ws", 3000)
        self.host = host
        self.url = f"{scheme}://{host}:{port}"
        self.timeout = timeout
        self.ws = None

    def connect(self, client_key=None):
        sslopt = {"cert_reqs": ssl.CERT_NONE} if self.url.startswith("wss") else None
        self.ws = websocket.create_connection(
            self.url, timeout=self.timeout, sslopt=sslopt
        )
        payload = json.loads(json.dumps(REGISTER_PAYLOAD))
        if client_key:
            payload["payload"]["client-key"] = client_key
        self.ws.send(json.dumps(payload))

        # De tv kan eerst een "PROMPT" sturen (wachten op de gebruiker aan de tv),
        # daarna een "registered" met de client-key.
        while True:
            resp = json.loads(self.ws.recv())
            t = resp.get("type")
            if t == "response" and resp.get("payload", {}).get("pairingType"):
                print("[!] Kijk naar je tv en bevestig met de afstandsbediening "
                      '("Toestaan"/"Accept")...')
                continue
            if t == "registered":
                return resp["payload"].get("client-key")
            if t == "error":
                raise RuntimeError(f"Tv weigerde verbinding: {resp.get('error')}")

    def request(self, uri, payload=None):
        msg = {
            "id": uuid.uuid4().hex,
            "type": "request",
            "uri": f"ssap://{uri}",
            "payload": payload or {},
        }
        self.ws.send(json.dumps(msg))
        return json.loads(self.ws.recv())

    def close(self):
        if self.ws:
            self.ws.close()


def get_connected_tv(host, secure):
    tv = LGTV(host, secure=secure)
    key = load_key(host)
    try:
        new_key = tv.connect(client_key=key)
    except (ConnectionRefusedError, OSError) as exc:
        sys.exit(
            f"[x] Kan geen verbinding maken met {host}.\n"
            f"    - Staat de tv aan en op hetzelfde netwerk?\n"
            f"    - Staat 'Mobile TV On (Netwerk)' / 'LG Connect Apps' aan?\n"
            f"    Details: {exc}"
        )
    if new_key and new_key != key:
        save_key(host, new_key)
    return tv


def main():
    p = argparse.ArgumentParser(description="Bedien je eigen LG webOS-tv.")
    p.add_argument("--host", required=True, help="IP-adres van de tv, bv. 192.168.0.168")
    p.add_argument("--secure", action="store_true", help="Gebruik wss:// (poort 3001)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pair", help="Koppel met de tv (eenmalig, vraagt bevestiging op tv)")
    sub.add_parser("info", help="Toon software-info van de tv")
    sub.add_parser("apps", help="Lijst geinstalleerde apps")
    v = sub.add_parser("volume", help="Zet volume op niveau (0-100)")
    v.add_argument("level", type=int)
    m = sub.add_parser("mute", help="Mute aan/uit")
    m.add_argument("state", choices=["on", "off"])
    a = sub.add_parser("app", help="Start een app op app-id")
    a.add_argument("app_id")
    n = sub.add_parser("notify", help="Toon een melding op het scherm")
    n.add_argument("text")
    sub.add_parser("off", help="Zet de tv in standby")

    args = p.parse_args()

    if args.cmd == "pair":
        tv = LGTV(args.host, secure=args.secure)
        key = tv.connect(client_key=load_key(args.host))
        if key:
            save_key(args.host, key)
        print("[v] Gekoppeld. Je kunt nu de andere commando's gebruiken.")
        tv.close()
        return

    tv = get_connected_tv(args.host, args.secure)
    try:
        if args.cmd == "info":
            r = tv.request("system/getSystemInfo")
            print(json.dumps(r.get("payload", {}), indent=2, ensure_ascii=False))
        elif args.cmd == "apps":
            r = tv.request("com.webos.applicationManager/listApps")
            for app in r.get("payload", {}).get("apps", []):
                print(f"{app.get('id'):40} {app.get('title')}")
        elif args.cmd == "volume":
            tv.request("audio/setVolume", {"volume": max(0, min(100, args.level))})
            print(f"[v] Volume -> {args.level}")
        elif args.cmd == "mute":
            tv.request("audio/setMute", {"mute": args.state == "on"})
            print(f"[v] Mute -> {args.state}")
        elif args.cmd == "app":
            tv.request("system.launcher/launch", {"id": args.app_id})
            print(f"[v] App gestart: {args.app_id}")
        elif args.cmd == "notify":
            tv.request("system.notifications/createToast", {"message": args.text})
            print("[v] Melding verstuurd.")
        elif args.cmd == "off":
            tv.request("system/turnOff")
            print("[v] Tv naar standby.")
    finally:
        tv.close()


if __name__ == "__main__":
    main()
