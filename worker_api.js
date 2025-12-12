// Cloudflare Worker: API Sender (Backend)
// Function: Receives POST data, Saves to KV, Sends WeChat Template Message
//
// Required Bindings:
// 1. KV Namespace: MSG_STORE (Shared with View Worker)
// 2. Env Vars:
//    - API_TOKEN: Secret token for authentication
//    - WX_APPID, WX_SECRET, WX_USERID, WX_TEMPLATE_ID: WeChat configs
//    - VIEW_URL_BASE: The base URL of your View Worker (e.g., "https://view.your-domain.com")

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

async function getParams(request) {
  const { searchParams } = new URL(request.url);
  const urlParams = Object.fromEntries(searchParams.entries());
  let bodyParams = {};
  if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
    try {
      const contentType = (request.headers.get('content-type') || '').toLowerCase();
      if (contentType.includes('application/json')) {
        const jsonBody = await request.json();
        // Flatten nested structures if present
        if (jsonBody.params) bodyParams = jsonBody.params;
        else if (jsonBody.data) bodyParams = jsonBody.data;
        else bodyParams = jsonBody;
      } else {
        const text = await request.text();
        try { bodyParams = JSON.parse(text); } catch { bodyParams = { content: text }; }
      }
    } catch (e) { console.error(e); }
  }
  return { ...urlParams, ...bodyParams };
}

async function getStableToken(appid, secret) {
  const tokenUrl = 'https://api.weixin.qq.com/cgi-bin/stable_token';
  const resp = await fetch(tokenUrl, {
    method: 'POST',
    body: JSON.stringify({ grant_type: 'client_credential', appid, secret, force_refresh: false })
  });
  return (await resp.json()).access_token;
}

async function sendMessage(accessToken, userid, template_id, detailUrl, title, content, date) {
  let titleColor = "#173177";
  if (/bullish|long|buy|看涨/i.test(title)) titleColor = "#17B978"; 
  if (/bearish|short|sell|看跌/i.test(title)) titleColor = "#E02020";

  let strategy = "Signal Alert";
  let price = "Check Details";
  
  const strategyMatch = content.match(/Strategy:\s*(.+)(\n|$)/i);
  if (strategyMatch) strategy = strategyMatch[1].substring(0, 20);
  
  const priceMatch = content.match(/Price:\s*(.+)($|\n)/i);
  if (priceMatch) price = priceMatch[1].substring(0, 20);

  const payload = {
    touser: userid,
    template_id: template_id,
    url: detailUrl, 
    data: {
      first: { value: title, color: titleColor },
      keyword1: { value: strategy, color: "#173177" },
      keyword2: { value: price, color: "#173177" },
      keyword3: { value: date, color: "#333333" },
      remark: { value: "\n🤖 AI Deep Analysis Ready. Click to view full report.", color: "#666666" }
    }
  };

  return await fetch(`https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=${accessToken}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  }).then(r => r.json());
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Status Check
    if (request.method === 'GET') {
       return new Response(`API Worker Running.\nKV Status: ${!!(env.MSG_STORE || env.LARK_MSG_STORE) ? 'Bound' : 'Not Bound'}`, {status: 200});
    }

    if (url.pathname !== '/wxsend') return new Response('Not Found', { status: 404 });

    const params = await getParams(request);
    
    // Auth
    let token = params.token;
    if (!token) {
        const auth = request.headers.get('Authorization');
        if (auth) token = auth.replace(/^Bearer\s+/i, '');
    }
    if (token !== env.API_TOKEN) return new Response('Invalid Token', { status: 403 });

    // Validate Inputs
    const { title, content } = params;
    if (!title || !content) return new Response('Missing title/content', { status: 400 });

    const appid = params.appid || env.WX_APPID;
    const secret = params.secret || env.WX_SECRET;
    const useridStr = params.userid || env.WX_USERID;
    const template_id = params.template_id || env.WX_TEMPLATE_ID;
    // CRITICAL: This determines where the link points to
    const viewBaseUrl = params.base_url || env.VIEW_URL_BASE; 

    if (!appid || !secret || !useridStr || !template_id || !viewBaseUrl) {
        return new Response('Missing Config (Check WX_* vars and VIEW_URL_BASE)', { status: 500 });
    }

    // Process
    const kv = env.MSG_STORE || env.LARK_MSG_STORE;
    if (!kv) return new Response('KV not bound', { status: 500 });

    const msgId = generateUUID();
    const dateStr = new Date(new Date().getTime() + 8 * 3600000).toISOString().replace('T', ' ').slice(0, 19);

    // 1. Save to KV
    await kv.put(msgId, JSON.stringify({ title, content, date: dateStr }), { expirationTtl: 604800 });

    // 2. Construct View URL
    // Ensure viewBaseUrl doesn't have trailing slash for consistency
    const cleanBaseUrl = viewBaseUrl.replace(///$/, '');
    const detailUrl = `${cleanBaseUrl}/read?id=${msgId}`;

    // 3. Send WX
    try {
        const accessToken = await getStableToken(appid, secret);
        const users = useridStr.split('|').map(u => u.trim()).filter(Boolean);
        const results = await Promise.all(users.map(u => sendMessage(accessToken, u, template_id, detailUrl, title, content, dateStr)));
        
        return new Response(JSON.stringify({ status: 'success', sent: results.length, detail_url: detailUrl }), { 
            headers: { 'Content-Type': 'application/json' } 
        });
    } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500 });
    }
  }
};
