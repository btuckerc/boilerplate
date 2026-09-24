# Local decision skill

Read `input.txt`. If the line beginning `status=` is `ready`, write
`{"action":"continue","reason":"ready"}` to `decision.json`; for any other
status write `{"action":"hold","reason":"not-ready"}`. Use JSON, with no
extra keys or prose.
