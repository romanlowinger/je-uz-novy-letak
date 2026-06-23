javascript:(async()=>{
  const TOKEN='VLOZ_TOKEN';
  const REPO='romanlowinger/je-uz-novy-letak';
  const FILE='urls.json';

  const url=prompt('URL letáku k sledování:',location.href);
  if(!url||!url.startsWith('http'))return;

  const api=`https://api.github.com/repos/${REPO}/contents/${FILE}`;
  const h={'Authorization':`Bearer ${TOKEN}`,'Accept':'application/vnd.github+json'};

  const r=await fetch(api,{headers:h});
  if(!r.ok){alert('❌ Chyba při načítání urls.json: '+r.status);return;}
  const d=await r.json();

  const j=JSON.parse(atob(d.content.replace(/\n/g,'')));
  if(j.urls.includes(url)){alert('Tato URL je už sledována.');return;}
  j.urls.push(url);

  const body=JSON.stringify(j,null,2)+'\n';
  const u=await fetch(api,{method:'PUT',headers:{...h,'Content-Type':'application/json'},
    body:JSON.stringify({message:`feat: přidána URL ${url}`,
      content:btoa(unescape(encodeURIComponent(body))),sha:d.sha})});

  if(u.ok){alert(`✅ Přidáno a začnu sledovat za max 15 min:\n${url}`);}
  else{const e=await u.json();alert('❌ Chyba: '+(e.message||u.status));}
})();
