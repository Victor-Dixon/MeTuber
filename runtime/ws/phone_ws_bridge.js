const fs = require("fs");
const path = require("path");
const http = require("http");
const { WebSocketServer } = require("ws");

const PORT = process.env.METUBER_WS_PORT || 8787;
const HOST = process.env.METUBER_WS_HOST || "0.0.0.0";

const server = http.createServer((req, res) => {
  if (req.url === "/" || req.url === "/index.html") {
    const file = path.join(process.cwd(), "public", "index.html");
    res.writeHead(200, {"content-type":"text/html"});
    res.end(fs.readFileSync(file));
    return;
  }

  if (req.url === "/health") {
    res.writeHead(200, {"content-type":"application/json"});
    res.end(JSON.stringify({ ok: true, service: "metuber-ws", port: Number(PORT) }));
    return;
  }

  res.writeHead(404, {"content-type":"application/json"});
  res.end(JSON.stringify({ ok: false, error: "not_found" }));
});

const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ type: "hello", service: "metuber-ws" }));
  ws.on("message", (raw) => {
    ws.send(JSON.stringify({
      type: "echo",
      body: raw.toString(),
      at: new Date().toISOString()
    }));
  });
});

server.listen(PORT, HOST, () => {
  console.log(`METUBER_WS_READY host=${HOST} port=${PORT}`);
});
