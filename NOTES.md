== curl ==
# GET  /api/profiles
# POST /api/profiles  {"activation_code":"LPA:1$SMDP.JIO.COM$ACI…"}
# POST /api/profiles/<iccid>/enable | /disable
# DELETE /api/profiles/<iccid>
# POST /api/discover  {"address":"lpa+ac:…"}
# GET  /api/eid
# CLI: lpac list / lpac install "LPA:1$…" / lpac enable <iccid>

== session plan ==
# Session 1: bridge (mock) + profiles state machine → tests
# Session 2: api + web templates → screenshots (mock data)
# Session 3: smdp discovery + QR + CLI → README → tag (hardware test on real modem)
