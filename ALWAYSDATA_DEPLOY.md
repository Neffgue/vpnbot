neffgue313@ssh1:~$ curl -X POST https://neffgue313.alwaysdata.net/api/v1/auth/login -H "Content-Type: application/json" --data @/tmp/login.json 2>&1
{"detail":"Invalid curl -X POST https://neffgue313.alwaysdata.net/api/v1/auth/login \waysdata.net/api/v1/auth/login \
  -H "Content-Type: application/json" \
  --data @/tmp/login.json
{"detail":"Invalid credentials"}neffgue313@ssh1:~$ cat /tmp/login.json
{"username":"admin"cd ~/vpnbot/backendneffgue313@ssh1:~$ cd ~/vpnbot/backend
cat .env | grep -E "ADMIN_USERNAME|ADMIN_PASSWORD"
cat: .env: No such file or directory
neffgue313@ssh1:~/vpnbot/backend$ curl -X POST https://neffgue313.alwaysdata.net/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjE3NzI0Mzk4NTB9.V8f-XyP3oiH776N5TI2YbZWRyygAz91D1lInGMfScBc","refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjE3NzMwNDM3NTAsInR5cGUiOiJyZWZyZXNoIn0.67PjBbWIIHAATo1drppCeVRK288ZZ0CksHhkeefitzk","token_type":"bearer","user":{"id":"00000000-0000-0000-0000-000000000001","username":"admin","is_admin":true}}neffgue313@ssh1:~/vpnbot/backend$ 