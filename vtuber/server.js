// 몽글이 버추얼 스트리머 - 로컬 실행 서버
// (카메라 권한 때문에 http://localhost 로 열어야 해서 필요해요)
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 8977;
const ROOT = __dirname;
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".png": "image/png" };

http.createServer((req, res) => {
  // 개발용: 캔버스 스냅샷 저장
  if (req.method === "POST" && req.url === "/snapshot") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      const b64 = body.replace(/^data:image\/png;base64,/, "");
      fs.writeFileSync(path.join(ROOT, "_snapshot.png"), Buffer.from(b64, "base64"));
      res.writeHead(200); res.end("ok");
    });
    return;
  }
  let file = req.url.split("?")[0];
  if (file === "/") file = "/index.html";
  const full = path.join(ROOT, file);
  if (!full.startsWith(ROOT) || !fs.existsSync(full)) {
    res.writeHead(404); res.end("Not found"); return;
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(full)] || "application/octet-stream" });
  fs.createReadStream(full).pipe(res);
}).listen(PORT, () => {
  console.log("몽글이 실행 중! 브라우저에서 http://localhost:" + PORT + " 를 여세요");
});
