const html = (title, msg, ok) => `<!DOCTYPE html>
<html lang="cs"><head><meta charset="utf-8"><title>${title}</title>
<style>body{font-family:sans-serif;max-width:500px;margin:4em auto;padding:1em}
h2{color:${ok ? '#2eb886' : '#e01e5a'}}</style></head>
<body><h2>${ok ? '✅' : '❌'} ${title}</h2><p>${msg}</p>
<p style="color:#888;font-size:.9em">Tuto záložku můžeš zavřít.</p></body></html>`;

async function removeUrl(letak_url, env) {
  const api = `https://api.github.com/repos/${env.GITHUB_REPO}/contents/urls.json`;
  const headers = {
    'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'je-uz-novy-letak',
  };

  const r = await fetch(api, { headers });
  if (!r.ok) throw new Error(`GitHub API: ${r.status}`);
  const d = await r.json();
  const data = JSON.parse(atob(d.content.replace(/\n/g, '')));

  const idx = data.urls.indexOf(letak_url);
  if (idx === -1) return false;
  data.urls.splice(idx, 1);

  const body = JSON.stringify(data, null, 2) + '\n';
  const u = await fetch(api, {
    method: 'PUT',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: `feat: odebrána URL ze sledování`,
      content: btoa(unescape(encodeURIComponent(body))),
      sha: d.sha,
    }),
  });
  if (!u.ok) throw new Error(`GitHub PUT: ${u.status}`);
  return true;
}

async function notifySlack(webhook, text) {
  await fetch(webhook, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

export default {
  async fetch(request, env) {
    const { searchParams } = new URL(request.url);
    const letak_url = searchParams.get('url');
    const token = searchParams.get('token');

    if (!letak_url || token !== env.SECRET_TOKEN) {
      return new Response(html('Neplatný požadavek', 'Odkaz je neplatný nebo vypršel.', false),
        { status: 403, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }

    try {
      const removed = await removeUrl(letak_url, env);
      if (removed) {
        await notifySlack(env.SLACK_WEBHOOK, `🛑 Sledování zastaveno: ${letak_url}`);
        return new Response(html('Sledování zastaveno', letak_url, true),
          { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      } else {
        return new Response(html('URL nenalezena', `${letak_url} není v seznamu sledovaných.`, false),
          { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      }
    } catch (e) {
      return new Response(html('Chyba', e.message, false),
        { status: 500, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }
  },
};
