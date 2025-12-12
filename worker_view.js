// Cloudflare Worker: View Renderer (Frontend)
// Function: Serves the HTML detail page by reading from KV
//
// Required Bindings:
// 1. KV Namespace: MSG_STORE (Shared with API Worker)

function renderHtml(title, content, date) {
    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown-light.min.css">
    <style>
        body { background-color: #f3f4f6; margin: 0; padding: 20px; font-family: sans-serif; }
        .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }
        .title { font-size: 1.5rem; font-weight: bold; color: #111; }
        .meta { color: #666; font-size: 0.9rem; margin-top: 5px; }
        .markdown-body { font-size: 16px; line-height: 1.6; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 0.8rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">${title}</div>
            <div class="meta">📅 ${date}</div>
        </div>
        <div class="markdown-body" id="content"></div>
        <div class="footer">DeepSeek AI Analysis</div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
    <script>
        const raw = ${JSON.stringify(content)}; 
        document.getElementById('content').innerHTML = marked.parse(raw);
    </script>
</body>
</html>`;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const id = url.searchParams.get('id');

    if (!id) {
        return new Response('<h1>View Worker Ready</h1><p>No Message ID provided.</p>', { 
            headers: { 'Content-Type': 'text/html' } 
        });
    }

    const kv = env.MSG_STORE || env.LARK_MSG_STORE;
    if (!kv) return new Response('KV MSG_STORE not bound', { status: 500 });

    const dataStr = await kv.get(id);
    if (!dataStr) return new Response('Message Not Found or Expired', { status: 404 });

    const data = JSON.parse(dataStr);
    return new Response(renderHtml(data.title, data.content, data.date), {
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
};
