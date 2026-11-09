# LG webOS TV-bediening (eigen gebruik)

Een klein hulpmiddel om je **eigen** LG smart-tv te bedienen vanaf je laptop,
via het officiele webOS-protocol (WebSocket).

> Gebruik dit alleen op een tv die van jou is, op je eigen netwerk. De tv vraagt
> bij de eerste verbinding op het scherm om toestemming; je moet die met de echte
> afstandsbediening bevestigen. Zonder die fysieke bevestiging werkt er niets.

## Vereisten

- De tv staat aan en zit op **hetzelfde wifi/LAN** als je laptop.
- Op de tv: netwerk-bediening aan laten staan
  (Instellingen → Algemeen/Netwerk → *Mobile TV On* / *LG Connect Apps*).
- Python 3 en de websocket-library:

```bash
pip install websocket-client
```

## Gebruik

Eenmalig koppelen (bevestig op de tv met de afstandsbediening):

```bash
python3 lgtv.py --host 192.168.0.168 pair
```

Daarna, bijvoorbeeld:

```bash
python3 lgtv.py --host 192.168.0.168 info            # systeeminfo
python3 lgtv.py --host 192.168.0.168 apps            # geinstalleerde apps
python3 lgtv.py --host 192.168.0.168 volume 12       # volume op 12
python3 lgtv.py --host 192.168.0.168 mute on         # dempen
python3 lgtv.py --host 192.168.0.168 app com.webos.app.netflix
python3 lgtv.py --host 192.168.0.168 notify "Hoi!"   # melding op tv
python3 lgtv.py --host 192.168.0.168 off             # standby
```

De client-key wordt na het koppelen bewaard in `~/.lgtv_keys.json`, zodat je
daarna zonder pop-up kunt verbinden.

## Belangrijk

Dit draai je op **jouw eigen machine**, op je eigen netwerk. Het werkt niet
vanuit een cloud-sessie of van buitenaf — de tv is alleen bereikbaar binnen je
eigen lokale netwerk, en elke eerste koppeling vereist bevestiging op het scherm.
