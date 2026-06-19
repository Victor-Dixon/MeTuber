const fs = require("fs");
const path = require("path");
const http = require("http");
const { WebSocketServer } = require("ws");

const PORT = process.env.METUBER_WS_PORT || 8787;
const HOST = process.env.METUBER_WS_HOST || "0.0.0.0";
const ROOT = process.cwd();
const UPLOAD_DIR = path.join(ROOT, "public", "uploads");
const PROJECT_DIR = path.join(ROOT, "data", "projects");

fs.mkdirSync(UPLOAD_DIR, { recursive: true });
fs.mkdirSync(PROJECT_DIR, { recursive: true });

function sendJson(res, status, payload) {
  res.writeHead(status, {"content-type":"application/json"});
  res.end(JSON.stringify(payload));
}

function serveFile(res, file, type) {
  res.writeHead(200, {"content-type": type});
  res.end(fs.readFileSync(file));
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/index.html")) {
    return serveFile(res, path.join(ROOT, "public", "index.html"), "text/html");
  }

  if (req.method === "GET" && url.pathname.startsWith("/plugins/")) {
    const file = path.join(ROOT, "public", path.normalize(url.pathname));
    if (!file.startsWith(path.join(ROOT, "public"))) return sendJson(res, 403, { ok:false, error:"forbidden" });
    if (!fs.existsSync(file)) return sendJson(res, 404, { ok:false, error:"not_found" });
    return serveFile(res, file, "application/javascript");
  }

  if (req.method === "GET" && url.pathname.startsWith("/uploads/")) {
    const file = path.join(ROOT, "public", path.normalize(url.pathname));
    if (!file.startsWith(UPLOAD_DIR)) return sendJson(res, 403, { ok:false, error:"forbidden" });
    if (!fs.existsSync(file)) return sendJson(res, 404, { ok:false, error:"not_found" });
    return serveFile(res, file, "video/webm");
  }

  if (req.method === "GET" && url.pathname === "/api/videos") {
    const videos = fs.readdirSync(UPLOAD_DIR)
      .filter(name => /\.(webm|mp4|mov)$/i.test(name))
      .sort()
      .reverse()
      .map(name => ({ name, url: `/uploads/${name}` }));
    return sendJson(res, 200, { ok:true, videos });
  }

  if (req.method === "POST" && url.pathname === "/api/upload") {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => {
      const ext = url.searchParams.get("ext") || "webm";
      const room = (url.searchParams.get("room") || "main-room").replace(/[^a-z0-9_-]/gi, "_");
      const user = (url.searchParams.get("user") || "creator").replace(/[^a-z0-9_-]/gi, "_");
      const safeExt = ext.replace(/[^a-z0-9]/gi, "").toLowerCase() || "webm";
      const name = `${room}_${user}_${Date.now()}.${safeExt}`;
      fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.concat(chunks));
      sendJson(res, 200, { ok:true, name, url:`/uploads/${name}` });
    });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/project") {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => {
      let project;
      try { project = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
      catch { return sendJson(res, 400, { ok:false, error:"invalid_json" }); }

      const name = `project_${Date.now()}.json`;
      fs.writeFileSync(path.join(PROJECT_DIR, name), JSON.stringify(project, null, 2));
      sendJson(res, 200, { ok:true, name });
    });
    return;
  }

  if (req.method === "GET" && url.pathname === "/health") {
    return sendJson(res, 200, { ok:true, service:"metuber-team-studio", port:Number(PORT) });
  }

  sendJson(res, 404, { ok:false, error:"not_found" });
});

const rooms = new Map();

const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  ws.room = "lobby";
  ws.user = "guest";
  ws.send(JSON.stringify({ type:"hello", service:"metuber-team-studio" }));

  ws.on("message", (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); }
    catch { msg = { type:"text", body:raw.toString() }; }

    if (msg.type === "join") {
      ws.room = msg.room || "lobby";
      ws.user = msg.user || "guest";
      if (!rooms.has(ws.room)) rooms.set(ws.room, new Set());
      rooms.get(ws.room).add(ws);
      broadcast(ws.room, { type:"presence", room:ws.room, user:ws.user, event:"join" });
      return;
    }

    broadcast(ws.room, { ...msg, from:ws.user, at:new Date().toISOString() });
  });

  ws.on("close", () => {
    if (rooms.has(ws.room)) rooms.get(ws.room).delete(ws);
    broadcast(ws.room, { type:"presence", room:ws.room, user:ws.user, event:"leave" });
  });
});

function broadcast(room, payload) {
  const clients = rooms.get(room);
  if (!clients) return;
  const body = JSON.stringify(payload);
  for (const client of clients) {
    if (client.readyState === 1) client.send(body);
  }
}

server.listen(PORT, HOST, () => {
  console.log(`METUBER_TEAM_STUDIO_READY host=${HOST} port=${PORT}`);
});
