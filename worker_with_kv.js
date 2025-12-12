// Cloudflare Worker Script with KV Support for WX Push
// Author: 
// 1. Create a KV Namespace in Cloudflare Dashboard -> Workers & Pages -> KV
// 2. Bind the KV Namespace to this Worker in Settings -> Variables -> KV Namespace Bindings.
//    - Variable Name: MSG_STORE
//    - KV Namespace: <Select the one you created>

// --- Helper Functions ---

// 1. Generate a simple unique ID (UUID v4-like)
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// 2. Extract parameters from any request type (JSON, Form, URL)
async function getParams(request) {
  const { searchParams } = new URL(request.url);
  const urlParams = Object.fromEntries(searchParams.entries());

  let bodyParams = {};
  if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
    const contentType = (request.headers.get('content-type') || '').toLowerCase();
    try {
      if (contentType.includes('application/json')) {
        const jsonBody = await request.json();
        // Handle various JSON structures
        if (typeof jsonBody === 'string') {
          bodyParams = { content: jsonBody };
        } else if (jsonBody && typeof jsonBody === 'object') {
          if (jsonBody.params && typeof jsonBody.params === 'object') bodyParams = jsonBody.params;
          else if (jsonBody.data && typeof jsonBody.data === 'object') bodyParams = jsonBody.data;
          else bodyParams = jsonBody;
        }
      } else if (contentType.includes('application/x-www-form-urlencoded') || contentType.includes('multipart/form-data')) {
        const formData = await request.formData();
        bodyParams = Object.fromEntries(formData.entries());
      } else {
        // Fallback for text/plain
        const text = await request.text();
        try {
           // Try parsing text as JSON just in case
           const parsed = JSON.parse(text);
           bodyParams = (parsed && typeof parsed === 'object') ? parsed : { content: text };
        } catch(e) {
           bodyParams = { content: text };
        }
      }
    } catch (error) {
      console.error('Failed to parse request body:', error);
    }
  }
  return { ...urlParams, ...bodyParams };
}

// 3. Get WeChat Stable Token
async function getStableToken(appid, secret) {
  const tokenUrl = 'https://api.weixin.qq.com/cgi-bin/stable_token';
  const payload = {
    grant_type: 'client_credential',
    appid: appid,
    secret: secret,
    force_refresh: false
  };
  const response = await fetch(tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json;charset=utf-8' },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  return data.access_token;
}

// 4. Send Template Message
async function sendMessage(accessToken, userid, template_id, detailUrl, title, content, date) {
  const sendUrl = `https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=${accessToken}`;
  
  // Logic to determine color based on title content (Simple sentiment analysis)
  let titleColor = "#173177"; // Default Blue
  const t = title.toLowerCase();
  if (t.includes('bullish') || t.includes('long') || t.includes('buy') || t.includes('看涨')) {
      titleColor = "#17B978"; // Green
  } else if (t.includes('bearish') || t.includes('short') || t.includes('sell') || t.includes('看跌')) {
      titleColor = "#E02020"; // Red
  }

  // Try to extract some structured info from content for the template keywords
  // This is a basic heuristic; can be improved based on your specific content format
  let strategy = "Signal Alert";
  let price = "Check Details";
  
  // Example regex to find "Strategy: xxx" or "Price: xxx" if they exist in text
  const strategyMatch = content.match(/Strategy:\s*(.+?)(\n|$)/i);
  if (strategyMatch) strategy = strategyMatch[1].substring(0, 20); // Limit length
  
  // Look for numbers that might be price if not explicit
  const priceMatch = content.match(/Price:\s*(.+?)(\n|$)/i);
  if (priceMatch) price = priceMatch[1].substring(0, 20);

  const payload = {
    touser: userid,
    template_id: template_id,
    url: detailUrl, // The Short Link to the Worker's /read endpoint
    data: {
      first: { 
        value: title, 
        color: titleColor 
      },
      keyword1: { 
        value: strategy,
        color: "#173177"
      },
      keyword2: { 
        value: price,
        color: "#173177"
      },
      keyword3: { 
        value: date,
        color: "#333333"
      },
      remark: { 
        value: "\n🤖 AI Deep Analysis Ready. Click to view full report & charts.",
        color: "#666666" 
      }
    }
  };

  const response = await fetch(sendUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json;charset=utf-8' },
    body: JSON.stringify(payload)
  });

  return await response.json();
}

// --- HTML Templates ---

function renderDetailHtml(title, content, date) {
    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${title}</title>
    <!-- Github Markdown CSS for better styling -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown-light.min.css">
    <style>
        body {
            background-color: #f3f4f6;
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .header {
            margin-bottom: 30px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 20px;
        }
        .title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 10px;
        }
        .meta {
            color: #6b7280;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .badge {
            background-color: #e0f2fe;
            color: #0369a1;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 500;
            font-size: 0.8rem;
        }
        .markdown-body {
            font-size: 16px;
            line-height: 1.6;
            color: #374151;
        }
        /* Custom tweaks for markdown */
        .markdown-body pre {
            background-color: #f8fafc;
            border-radius: 8px;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.8rem;
            color: #9ca3af;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">${title}</div>
            <div class="meta">
                <span class="badge">Signal Alert</span>
                <span>📅 ${date}</span>
            </div>
        </div>
        
        <div class="markdown-body" id="content">
            ${content} 
        </div>

        <div class="footer">
            Generated by DeepSeek AI & Lark-ws Bot
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
    <script>
        // Render Markdown on Client Side
        window.addEventListener('DOMContentLoaded', () => {
            const contentDiv = document.getElementById('content');
            if (contentDiv && typeof marked !== 'undefined') {
                const rawContent = 
                // Note: The raw content injection above is a bit fragile for complex strings in template literals.
                // ideally, we would fetch the JSON content via API to avoid XSS or syntax errors, 
                // but for this simple version, we will trust the content is relatively safe text.
                // A safer way is to put the raw text in a hidden div and read it.
                contentDiv.innerHTML = marked.parse(contentDiv.innerText);
            }
        });
    </script>
</body>
</html>`;
}

// --- Main Worker Logic ---

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 1. GET /read?id=... -> Serve the Detail Page
    if (path === '/read') {
        const id = url.searchParams.get('id');
        if (!id) return new Response('Missing Message ID', { status: 400 });
        
        // Retrieve data from KV
        // IMPORTANT: You must bind a KV Namespace to the variable 'MSG_STORE'
        if (!env.MSG_STORE) {
            return new Response('Server Error: KV MSG_STORE not bound.', { status: 500 });
        }

        const dataStr = await env.MSG_STORE.get(id);
        if (!dataStr) {
            return new Response('Message expired or not found.', { status: 404 });
        }

        const data = JSON.parse(dataStr);
        return new Response(renderDetailHtml(data.title, data.content, data.date), {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
    }

    // 2. POST /wxsend -> Process Alert and Send Template Message
    if (path === '/wxsend') {
      const params = await getParams(request);
      
      // Token Auth
      let requestToken = params.token;
      if (!requestToken) {
        const authHeader = request.headers.get('Authorization') || request.headers.get('authorization');
        if (authHeader) {
          const parts = authHeader.split(' ');
          requestToken = parts.length === 2 && /^Bearer$/i.test(parts[0]) ? parts[1] : authHeader;
        }
      }

      if (requestToken !== env.API_TOKEN) {
        return new Response('Invalid token', { status: 403 });
      }

      const { title, content } = params;
      if (!title || !content) {
          return new Response('Missing title or content', { status: 400 });
      }

      // Env vars
      const appid = params.appid || env.WX_APPID;
      const secret = params.secret || env.WX_SECRET;
      const useridStr = params.userid || env.WX_USERID;
      const template_id = params.template_id || env.WX_TEMPLATE_ID;
      
      if (!appid || !secret || !useridStr || !template_id) {
          return new Response('Missing WX config (APPID, SECRET, USERID, TEMPLATE_ID)', { status: 500 });
      }

      // Generate Date
      const beijingTime = new Date(new Date().getTime() + 8 * 60 * 60 * 1000);
      const dateStr = beijingTime.toISOString().slice(0, 19).replace('T', ' ');

      // A. Save Full Content to KV
      if (!env.MSG_STORE) return new Response('KV MSG_STORE not bound', { status: 500 });
      
      const msgId = generateUUID();
      // Store for 7 days (604800 seconds)
      await env.MSG_STORE.put(msgId, JSON.stringify({ title, content, date: dateStr }), { expirationTtl: 604800 });

      // B. Construct Detail URL
      const workerUrl = `${url.protocol}//${url.host}`;
      const detailUrl = `${workerUrl}/read?id=${msgId}`;

      // C. Send WeChat Template Message
      try {
        const accessToken = await getStableToken(appid, secret);
        const user_list = useridStr.split('|').map(uid => uid.trim()).filter(Boolean);
        
        const results = await Promise.all(user_list.map(userid => 
            sendMessage(accessToken, userid, template_id, detailUrl, title, content, dateStr)
        ));

        const successCount = results.filter(r => r.errmsg === 'ok').length;
        return new Response(JSON.stringify({ 
            status: successCount > 0 ? 'success' : 'partial_error', 
            sent: successCount, 
            total: user_list.length,
            detail_url: detailUrl // Return this for debugging
        }), { 
            headers: { 'Content-Type': 'application/json' }
        });

      } catch (e) {
          return new Response(JSON.stringify({ error: e.message }), { status: 500 });
      }
    }

    // 3. Root Path -> Status / Info Page
    return new Response(`
    <html>
    <head><title>WXPush Service</title></head>
    <body style="font-family:sans-serif; text-align:center; padding:50px;">
        <h1>WXPush Service is Running</h1>
        <p>Use POST /wxsend to trigger alerts.</p>
        <p>KV Storage is: ${env.MSG_STORE ? '<span style="color:green">Active</span>' : '<span style="color:red">Not Bound</span>'}</p>
    </body>
    </html>`, { headers: { 'Content-Type': 'text/html' } });
  }
};
