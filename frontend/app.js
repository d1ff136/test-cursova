/* ================= config & helpers ================= */
const LS_API = 'orel_reshka_api_base';
const LS_MYID = 'orel_reshka_my_id';

function getApiBase(){
  return (localStorage.getItem(LS_API) || 'http://localhost:8000').replace(/\/+$/,'');
}
function setApiBase(v){
  try{ localStorage.setItem(LS_API, v); }catch(e){}
}

function esc(s){
  if(s===null||s===undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtDate(iso){
  if(!iso) return '—';
  try{
    const d = new Date(iso);
    return d.toLocaleString('uk-UA', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  }catch(e){ return iso; }
}
function toast(msg, type){
  const stack = document.getElementById('toastStack');
  const el = document.createElement('div');
  el.className = 'toast' + (type ? ' '+type : '');
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(()=>{ el.style.opacity='0'; el.style.transition='opacity .3s'; setTimeout(()=>el.remove(),300); }, 4200);
}

async function api(path, opts){
  opts = opts || {};
  const base = getApiBase();
  let res, data = null;
  try{
    res = await fetch(base + path, {
      method: opts.method || 'GET',
      headers: opts.body ? {'Content-Type':'application/json'} : undefined,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  }catch(networkErr){
    throw new Error("Не вдалося з'єднатися з API. Перевірте, що backend запущено (кнопка ⚙ у шапці) і дозволяє CORS-запити з цієї сторінки.");
  }
  const text = await res.text();
  try{ data = text ? JSON.parse(text) : null; }catch(e){ data = null; }

  if(!res.ok){
    let msg = 'Помилка ' + res.status;
    if(data && data.detail){
      if(Array.isArray(data.detail)){
        msg = data.detail.map(d => (d.loc ? d.loc.join('.')+': ' : '') + d.msg).join('; ');
      } else {
        msg = data.detail;
      }
    }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

/* ================= connection (URL hidden behind gear icon) ================= */
document.getElementById('apiUrlInput').value = getApiBase();

async function pingApi(){
  const dot = document.getElementById('connDot');
  const label = document.getElementById('connLabel');
  label.textContent = 'перевірка…';
  dot.className = 'dot';
  try{
    await api('/');
    dot.className = 'dot ok';
    label.textContent = "з'єднано";
  }catch(e){
    dot.className = 'dot bad';
    label.textContent = 'немає з\'єднання';
  }
}
document.getElementById('pingBtn').addEventListener('click', pingApi);
document.getElementById('advToggleBtn').addEventListener('click', ()=>{
  const panel = document.getElementById('advPanel');
  panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
});
document.getElementById('saveApiBtn').addEventListener('click', ()=>{
  setApiBase(document.getElementById('apiUrlInput').value.trim() || 'http://localhost:8000');
  toast('Адресу API збережено', 'ok');
  pingApi();
});
pingApi();

/* ================= "Мій акаунт" (ID + нік + роль) ================= */
const LS_MYNAME = 'orel_reshka_my_name';
const LS_MYROLE = 'orel_reshka_my_role';

function getMyId(){
  try{ return localStorage.getItem(LS_MYID) || ''; }catch(e){ return ''; }
}
function getMyName(){
  try{ return localStorage.getItem(LS_MYNAME) || ''; }catch(e){ return ''; }
}
function getMyRole(){
  try{ return localStorage.getItem(LS_MYROLE) || 'user'; }catch(e){ return 'user'; }
}
function setMyName(name){
  try{ localStorage.setItem(LS_MYNAME, name || ''); }catch(e){}
  renderMyId();
}
function setMyId(id, name, role){
  try{ localStorage.setItem(LS_MYID, id); }catch(e){}
  if(name !== undefined){
    try{ localStorage.setItem(LS_MYNAME, name || ''); }catch(e){}
  } else {
    try{ localStorage.removeItem(LS_MYNAME); }catch(e){}
    fetchAndStoreMyName(id);
  }
  try{ localStorage.setItem(LS_MYROLE, role || 'user'); }catch(e){}
  renderMyId();
  autofillMyId();
}
async function fetchAndStoreMyName(id){
  try{
    const user = await api('/users/' + encodeURIComponent(id));
    setMyName(user.username);
    try{ localStorage.setItem(LS_MYROLE, user.role || 'user'); }catch(e){}
  }catch(e){
    /* ID може бути ще не перевіреним - просто лишаємо нік порожнім */
  }
}
function renderMyId(){
  const id = getMyId();
  const name = getMyName();
  document.getElementById('myIdDisplay').textContent = id || '—';
  document.getElementById('myNameDisplay').textContent = name || (id ? 'нік невідомий' : 'не встановлено');
  document.getElementById('myIdInput').value = id;
}
function autofillMyId(){
  const id = getMyId();
  if(!id) return;
  const soloFind = document.getElementById('solo-find-id');
  if(soloFind && !soloFind.value) soloFind.value = id;
  const teamU1 = document.getElementById('team-u1');
  if(teamU1 && !teamU1.value) teamU1.value = id;
}
document.getElementById('myIdCopyBtn').addEventListener('click', ()=>{
  const id = getMyId();
  if(!id){ toast('Спочатку встановіть свій ID', 'err'); return; }
  try{ navigator.clipboard.writeText(id).then(()=>toast('Скопійовано', 'ok')); }catch(e){}
});
document.getElementById('myIdEditBtn').addEventListener('click', ()=>{
  const row = document.getElementById('myIdEditRow');
  row.style.display = row.style.display === 'none' ? 'flex' : 'none';
});
document.getElementById('myIdSaveBtn').addEventListener('click', ()=>{
  const val = document.getElementById('myIdInput').value.trim();
  if(!val){ toast('Введіть ID', 'err'); return; }
  setMyId(val);
  document.getElementById('myIdEditRow').style.display = 'none';
  toast('Ваш ID збережено, підвантажуємо нік…', 'ok');
});
renderMyId();

/* ================= PLAYERS: register / login toggle ================= */
document.getElementById('authModeSeg').addEventListener('click', (e)=>{
  const btn = e.target.closest('button');
  if(!btn) return;
  document.querySelectorAll('#authModeSeg button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const mode = btn.dataset.auth;
  document.getElementById('registerBlock').style.display = mode==='register' ? 'block' : 'none';
  document.getElementById('loginBlock').style.display = mode==='login' ? 'block' : 'none';
  document.getElementById('registerResult').classList.remove('show');
});

/* ================= tabs ================= */
document.querySelectorAll('.tab').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-'+btn.dataset.tab).classList.add('active');
    autofillMyId();
  });
});

/* ================= result rendering helpers ================= */
function showResult(el, html, isErr){
  el.innerHTML = html;
  el.classList.add('show');
  el.classList.toggle('err', !!isErr);
}
function idBoxHtml(label, id){
  return `<div class="field"><label>${esc(label)}</label>
    <div class="idbox"><code>${esc(id)}</code><button type="button" class="copybtn" data-copy="${esc(id)}">копіювати</button></div></div>`;
}
document.addEventListener('click', (e)=>{
  const t = e.target.closest('.copybtn');
  if(!t) return;
  const val = t.dataset.copy;
  try{
    navigator.clipboard.writeText(val).then(()=>toast('Скопійовано', 'ok'));
  }catch(err){ /* clipboard unavailable */ }
});

function rankNameToClass(name){
  if(!name) return 'rank-unranked';
  const n = name.toLowerCase();
  if(n.includes('bronze')) return 'rank-bronze';
  if(n.includes('silver')) return 'rank-silver';
  if(n.includes('gold')) return 'rank-gold';
  if(n.includes('diamond')) return 'rank-diamond';
  return 'rank-unranked';
}
function statusLabel(s){
  return {pending:'очікує', in_progress:'триває', finished:'завершено', cancelled:'скасовано'}[s] || s;
}

/* ================= PLAYERS: register ================= */
document.getElementById('registerForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('registerResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      username: document.getElementById('reg-username').value.trim(),
      email: document.getElementById('reg-email').value.trim(),
      password: document.getElementById('reg-password').value,
    };
    const user = await api('/users/', {method:'POST', body: payload});
    showResult(resultEl, `
      <div class="ok-msg" style="margin-bottom:10px;">Гравця «${esc(user.username)}» зареєстровано. Стартовий рейтинг: 1000 MMR (Solo та Party).</div>
      ${idBoxHtml('Ваш ID гравця', user.id)}
    `);
    document.getElementById('lookup-id').value = user.id;
    setMyId(user.id, user.username, user.role);
    e.target.reset();
    toast('Гравця зареєстровано, ваш нік і ID збережено вгорі', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

/* ================= PLAYERS: login ================= */
document.getElementById('loginForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('registerResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      username: document.getElementById('login-username').value.trim(),
      password: document.getElementById('login-password').value,
    };
    const user = await api('/users/login', {method:'POST', body: payload});
    showResult(resultEl, `
      <div class="ok-msg" style="margin-bottom:10px;">Вітаємо, «${esc(user.username)}»! Ви увійшли в акаунт.</div>
      ${idBoxHtml('Ваш ID гравця', user.id)}
    `);
    document.getElementById('lookup-id').value = user.id;
    setMyId(user.id, user.username, user.role);
    e.target.reset();
    toast('Успішний вхід, ваш нік і ID збережено вгорі', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

/* ================= PLAYERS: lookup ================= */
document.getElementById('lookupForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const id = document.getElementById('lookup-id').value.trim();
  const resultEl = document.getElementById('lookupResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const user = await api('/users/' + encodeURIComponent(id));
    let soloRating=null, partyRating=null;
    try{ soloRating = await api(`/users/${id}/rating/solo`); }catch(e2){}
    try{ partyRating = await api(`/users/${id}/rating/party`); }catch(e2){}

    document.getElementById('p-username').textContent = user.username;
    document.getElementById('p-email').textContent = user.email;
    document.getElementById('p-id').textContent = user.id;
    document.getElementById('p-set-mine').dataset.id = user.id;
    document.getElementById('p-role').textContent = user.role;
    document.getElementById('p-created').textContent = fmtDate(user.created_at);
    const activePill = document.getElementById('p-active');
    activePill.textContent = user.is_active ? 'активний' : 'деактивовано';
    activePill.style.color = user.is_active ? 'var(--green)' : 'var(--red)';

    // Адмінські дії видно, лише якщо ВХОДІВ поточний "Мій ID" з роллю admin
    // і йдеться не про власний профіль.
    const adminRow = document.getElementById('p-admin-actions');
    if(getMyRole() === 'admin' && getMyId() && getMyId() !== user.id){
      adminRow.style.display = 'flex';
      document.getElementById('p-reactivate-btn').style.display = user.is_active ? 'none' : 'block';
      document.getElementById('p-promote-btn').style.display = user.role === 'admin' ? 'none' : 'block';
      document.getElementById('p-promote-btn').textContent = 'Зробити admin';
    } else {
      adminRow.style.display = 'none';
    }

    fillRatingBox('solo', soloRating);
    fillRatingBox('party', partyRating);

    document.getElementById('profileCard').style.display = 'block';
    showResult(resultEl, `<div class="ok-msg">Профіль завантажено нижче ↓</div>`);
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    document.getElementById('profileCard').style.display = 'none';
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});
document.getElementById('p-set-mine').addEventListener('click', (e)=>{
  const id = e.target.dataset.id;
  const name = document.getElementById('p-username').textContent;
  if(!id) return;
  setMyId(id, name);
  toast('Збережено як ваш акаунт', 'ok');
});

/* ================= PLAYERS: update / deactivate ================= */
document.getElementById('p-edit-toggle').addEventListener('click', ()=>{
  const form = document.getElementById('editProfileForm');
  form.style.display = form.style.display === 'none' ? 'block' : 'none';
});

document.getElementById('editProfileForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const id = document.getElementById('p-set-mine').dataset.id;
  const resultEl = document.getElementById('editProfileResult');
  const btn = e.target.querySelector('button');
  if(!id){ toast('Спочатку відкрийте профіль', 'err'); return; }
  const payload = {};
  const uname = document.getElementById('edit-username').value.trim();
  const email = document.getElementById('edit-email').value.trim();
  const pass = document.getElementById('edit-password').value;
  if(uname) payload.username = uname;
  if(email) payload.email = email;
  if(pass) payload.password = pass;
  if(!Object.keys(payload).length){ toast('Заповніть хоча б одне поле', 'err'); return; }

  btn.disabled = true;
  try{
    const user = await api('/users/' + encodeURIComponent(id), {method:'PATCH', body: payload});
    showResult(resultEl, `<div class="ok-msg">Профіль оновлено: «${esc(user.username)}» / ${esc(user.email)}</div>`);
    document.getElementById('p-username').textContent = user.username;
    document.getElementById('p-email').textContent = user.email;
    document.getElementById('p-set-mine').dataset.id = user.id;
    if(getMyId() === user.id) setMyName(user.username);
    e.target.reset();
    toast('Профіль оновлено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('p-deactivate-btn').addEventListener('click', async ()=>{
  const id = document.getElementById('p-set-mine').dataset.id;
  const resultEl = document.getElementById('editProfileResult');
  if(!id){ toast('Спочатку відкрийте профіль', 'err'); return; }
  if(!confirm('Деактивувати цей акаунт? Це м\'яке видалення (is_active=false) — вхід стане неможливим, історія матчів збережеться.')) return;
  try{
    const user = await api('/users/' + encodeURIComponent(id) + '?requester_id=' + encodeURIComponent(id), {method:'DELETE'});
    showResult(resultEl, `<div class="ok-msg">Акаунт «${esc(user.username)}» деактивовано (is_active=false).</div>`);
    document.getElementById('p-active').textContent = 'деактивовано';
    document.getElementById('p-active').style.color = 'var(--red)';
    toast('Акаунт деактивовано', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

/* ================= PLAYERS: admin actions (reactivate / promote) ================= */
document.getElementById('p-reactivate-btn').addEventListener('click', async ()=>{
  const id = document.getElementById('p-set-mine').dataset.id;
  const admin = getMyId();
  const resultEl = document.getElementById('editProfileResult');
  if(!id || !admin){ toast('Потрібен профіль і адмін-акаунт у «Мій ID»', 'err'); return; }
  try{
    const user = await api(`/users/${encodeURIComponent(id)}/reactivate?requester_id=${encodeURIComponent(admin)}`, {method:'POST'});
    showResult(resultEl, `<div class="ok-msg">Акаунт «${esc(user.username)}» реактивовано.</div>`);
    document.getElementById('p-active').textContent = 'активний';
    document.getElementById('p-active').style.color = '';
    document.getElementById('p-reactivate-btn').style.display = 'none';
    toast('Акаунт реактивовано', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

document.getElementById('p-promote-btn').addEventListener('click', async ()=>{
  const id = document.getElementById('p-set-mine').dataset.id;
  const admin = getMyId();
  const resultEl = document.getElementById('editProfileResult');
  if(!id || !admin){ toast('Потрібен профіль і адмін-акаунт у «Мій ID»', 'err'); return; }
  try{
    const user = await api(`/users/${encodeURIComponent(id)}/promote?requester_id=${encodeURIComponent(admin)}`, {method:'POST'});
    showResult(resultEl, `<div class="ok-msg">«${esc(user.username)}» тепер admin.</div>`);
    document.getElementById('p-role').textContent = user.role;
    document.getElementById('p-promote-btn').style.display = 'none';
    toast('Роль оновлено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

function fillRatingBox(mode, rating){
  const mmrEl = document.getElementById(`p-${mode}-mmr`);
  const rankEl = document.getElementById(`p-${mode}-rank`);
  const wEl = document.getElementById(`p-${mode}-w`);
  const lEl = document.getElementById(`p-${mode}-l`);
  const mpEl = document.getElementById(`p-${mode}-mp`);
  const worldEl = document.getElementById(`p-${mode}-world`);
  if(!rating){
    mmrEl.textContent = '—';
    rankEl.className = 'pill rank-unranked';
    rankEl.textContent = 'немає даних';
    wEl.textContent = lEl.textContent = mpEl.textContent = '0';
    worldEl.textContent = '';
    return;
  }
  mmrEl.textContent = rating.mmr;
  if(rating.rank){
    rankEl.className = 'pill ' + rankNameToClass(rating.rank.name);
    rankEl.textContent = rating.rank.tier ? `${rating.rank.name} ${rating.rank.tier}` : rating.rank.name;
  } else {
    rankEl.className = 'pill rank-unranked';
    rankEl.textContent = 'Unranked';
  }
  wEl.textContent = rating.wins;
  lEl.textContent = rating.losses;
  mpEl.textContent = rating.matches_played;
  worldEl.textContent = rating.world_rank ? `♦ Світова позиція: #${rating.world_rank}` : '';
}

/* ================= TEAMS ================= */
document.getElementById('teamForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('teamResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      name: document.getElementById('team-name').value.trim() || null,
      member_user_ids: [
        document.getElementById('team-u1').value.trim(),
        document.getElementById('team-u2').value.trim(),
        document.getElementById('team-u3').value.trim(),
      ],
      is_permanent: document.getElementById('team-permanent').checked,
    };
    const team = await api('/teams/', {method:'POST', body: payload});
    showResult(resultEl, `
      <div class="ok-msg" style="margin-bottom:10px;">Команду ${team.name ? '«'+esc(team.name)+'» ' : ''}створено (${team.is_permanent?'постійна':'одноразова'}).</div>
      ${idBoxHtml('ID команди', team.id)}
      <div class="field"><label>Учасники</label>
        ${team.member_user_ids.map(uid=>`<div class="idbox" style="margin-bottom:6px;"><code>${esc(uid)}</code></div>`).join('')}
      </div>
    `);
    if(!document.getElementById('party-find-id').value){
      document.getElementById('party-find-id').value = team.id;
    }
    e.target.reset();
    autofillMyId();
    toast('Команду створено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

/* ================= TEAMS: lookup / edit / delete ================= */
let currentTeamId = null;

document.getElementById('teamLookupForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const id = document.getElementById('team-lookup-id').value.trim();
  const resultEl = document.getElementById('teamLookupResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const team = await api('/teams/' + encodeURIComponent(id));
    currentTeamId = team.id;
    document.getElementById('te-id').textContent = team.id;
    document.getElementById('te-members').textContent = team.member_user_ids.join(', ');
    document.getElementById('te-name').value = team.name || '';
    document.getElementById('te-permanent').checked = !!team.is_permanent;
    document.getElementById('teamEditCard').style.display = 'block';
    showResult(resultEl, `<div class="ok-msg">Команду знайдено нижче ↓</div>`);
  }catch(err){
    document.getElementById('teamEditCard').style.display = 'none';
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('teamEditForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  if(!currentTeamId){ toast('Спочатку знайдіть команду', 'err'); return; }
  const resultEl = document.getElementById('teamEditResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      name: document.getElementById('te-name').value.trim() || null,
      is_permanent: document.getElementById('te-permanent').checked,
    };
    const team = await api('/teams/' + encodeURIComponent(currentTeamId), {method:'PATCH', body: payload});
    showResult(resultEl, `<div class="ok-msg">Команду оновлено: «${esc(team.name || '(без назви)')}»</div>`);
    toast('Команду оновлено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('teamDeleteBtn').addEventListener('click', async ()=>{
  if(!currentTeamId){ toast('Спочатку знайдіть команду', 'err'); return; }
  const resultEl = document.getElementById('teamEditResult');
  if(!confirm('Видалити цю команду? Можливо лише якщо вона ще не брала участі в матчах.')) return;
  try{
    await api('/teams/' + encodeURIComponent(currentTeamId), {method:'DELETE'});
    showResult(resultEl, `<div class="ok-msg">Команду видалено.</div>`);
    document.getElementById('teamEditCard').style.display = 'none';
    toast('Команду видалено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

/* ================= MATCHES: mode + pairing toggle ================= */
let matchMode = 'solo';   // 'solo' | 'party'
let matchPair = 'auto';   // 'auto' | 'manual'

function refreshMatchForms(){
  document.getElementById('soloFindForm').style.display   = (matchMode==='solo'  && matchPair==='auto')   ? 'block' : 'none';
  document.getElementById('soloMatchForm').style.display  = (matchMode==='solo'  && matchPair==='manual') ? 'block' : 'none';
  document.getElementById('partyFindForm').style.display  = (matchMode==='party' && matchPair==='auto')   ? 'block' : 'none';
  document.getElementById('partyMatchForm').style.display = (matchMode==='party' && matchPair==='manual') ? 'block' : 'none';
  autofillMyId();
}

document.getElementById('matchModeSeg').addEventListener('click', (e)=>{
  const btn = e.target.closest('button');
  if(!btn) return;
  document.querySelectorAll('#matchModeSeg button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  matchMode = btn.dataset.mode;
  refreshMatchForms();
});

document.getElementById('matchPairSeg').addEventListener('click', (e)=>{
  const btn = e.target.closest('button');
  if(!btn) return;
  document.querySelectorAll('#matchPairSeg button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  matchPair = btn.dataset.pair;
  refreshMatchForms();
});

document.getElementById('soloFindForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('startMatchResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  showResult(resultEl, `<div class="ok-msg">Шукаємо вільного суперника з найближчим MMR…</div>`);
  try{
    const payload = { player_id: document.getElementById('solo-find-id').value.trim() };
    const match = await api('/matches/solo/find', {method:'POST', body: payload});
    afterMatchCreated(match, resultEl);
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('partyFindForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('startMatchResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  showResult(resultEl, `<div class="ok-msg">Шукаємо вільну команду з найближчим сумарним MMR…</div>`);
  try{
    const payload = { team_id: document.getElementById('party-find-id').value.trim() };
    const match = await api('/matches/party/find', {method:'POST', body: payload});
    afterMatchCreated(match, resultEl);
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('soloMatchForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('startMatchResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      player1_id: document.getElementById('solo-p1').value.trim(),
      player2_id: document.getElementById('solo-p2').value.trim(),
    };
    const match = await api('/matches/solo', {method:'POST', body: payload});
    afterMatchCreated(match, resultEl);
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

document.getElementById('partyMatchForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const resultEl = document.getElementById('startMatchResult');
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try{
    const payload = {
      team1_id: document.getElementById('party-t1').value.trim(),
      team2_id: document.getElementById('party-t2').value.trim(),
    };
    const match = await api('/matches/party', {method:'POST', body: payload});
    afterMatchCreated(match, resultEl);
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

function afterMatchCreated(match, resultEl){
  showResult(resultEl, `
    <div class="ok-msg" style="margin-bottom:10px;">Матч створено (${esc(match.status)}). Право обирати сторону монети — у гравця з нижчим MMR.</div>
    ${idBoxHtml('ID матчу', match.id)}
  `);
  document.getElementById('open-match-id').value = match.id;
  toast('Матч створено', 'ok');
  loadMatch(match.id);
}

/* ================= MATCHES: open / render ================= */
document.getElementById('openMatchForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const id = document.getElementById('open-match-id').value.trim();
  await loadMatch(id, document.getElementById('openMatchResult'));
});

let currentMatchId = null;

async function loadMatch(id, resultEl){
  try{
    const match = await api('/matches/' + encodeURIComponent(id));
    const rounds = await api('/matches/' + encodeURIComponent(id) + '/rounds');
    currentMatchId = match.id;
    renderMatch(match, rounds);
    if(resultEl) showResult(resultEl, `<div class="ok-msg">Матч завантажено нижче ↓</div>`);
    document.getElementById('matchCard').scrollIntoView({behavior:'smooth', block:'nearest'});
  }catch(err){
    if(resultEl) showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
}

function renderMatch(match, rounds){
  document.getElementById('matchCard').style.display = 'block';
  document.getElementById('m-mode').textContent = match.mode.toUpperCase();
  const statusPill = document.getElementById('m-status');
  statusPill.className = 'pill status-' + match.status;
  statusPill.textContent = statusLabel(match.status);
  document.getElementById('m-id').textContent = match.id;
  document.getElementById('m-side1-mmr').textContent = match.side1_mmr_snapshot ?? '—';
  document.getElementById('m-side2-mmr').textContent = match.side2_mmr_snapshot ?? '—';
  document.getElementById('m-bestof').textContent = `до ${Math.floor(match.best_of/2)+1} перемог (Bo${match.best_of})`;
  document.getElementById('m-chooser').textContent = match.coin_chooser_user_id || '—';
  document.getElementById('m-created').textContent = fmtDate(match.created_at);

  const side1Box = document.getElementById('side1-box');
  const side2Box = document.getElementById('side2-box');
  side1Box.classList.toggle('winner', match.winner_side === 1);
  side2Box.classList.toggle('winner', match.winner_side === 2);

  const finRow = document.getElementById('m-finished-row');
  if(match.finished_at){
    finRow.style.display = 'flex';
    document.getElementById('m-finished').textContent = fmtDate(match.finished_at);
  } else {
    finRow.style.display = 'none';
  }

  const finished = match.status === 'finished' || match.status === 'cancelled';
  document.getElementById('roundFormWrap').style.display = finished ? 'none' : 'block';
  const note = document.getElementById('matchFinishedNote');
  if(match.status === 'finished'){
    note.style.display = 'block';
    document.getElementById('matchFinishedText').textContent = `Перемогла сторона ${match.winner_side}. MMR обох сторін перераховано.`;
  } else {
    note.style.display = 'none';
  }

  renderRounds(rounds);
}

function renderRounds(rounds){
  const body = document.getElementById('roundsBody');
  const empty = document.getElementById('roundsEmpty');
  document.getElementById('roundsCountChip').textContent = rounds.length;
  if(!rounds.length){
    body.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  body.innerHTML = rounds.map(r => `
    <tr>
      <td class="num">${r.round_number}</td>
      <td>${r.coin_choice === 'heads' ? 'Орел' : 'Решка'}</td>
      <td>${r.coin_result === 'heads' ? 'Орел' : 'Решка'}</td>
      <td class="num">Сторона ${r.winner_side}</td>
      <td>${fmtDate(r.created_at)}</td>
    </tr>
  `).join('');
}

/* ================= MATCHES: cancel / delete ================= */
document.getElementById('matchCancelBtn').addEventListener('click', async ()=>{
  if(!currentMatchId){ toast('Спочатку відкрийте матч', 'err'); return; }
  const resultEl = document.getElementById('matchActionResult');
  if(!confirm('Скасувати цей матч? Можливо лише поки не зіграно жодного раунду.')) return;
  try{
    const match = await api(`/matches/${currentMatchId}/cancel`, {method:'POST'});
    showResult(resultEl, `<div class="ok-msg">Матч скасовано.</div>`);
    const rounds = await api('/matches/' + currentMatchId + '/rounds');
    renderMatch(match, rounds);
    toast('Матч скасовано', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

document.getElementById('matchDeleteBtn').addEventListener('click', async ()=>{
  if(!currentMatchId){ toast('Спочатку відкрийте матч', 'err'); return; }
  const resultEl = document.getElementById('matchActionResult');
  if(!confirm('Видалити цей матч назавжди? Можливо лише для скасованого матчу або матчу без зіграних раундів.')) return;
  try{
    await api('/matches/' + currentMatchId, {method:'DELETE'});
    showResult(resultEl, `<div class="ok-msg">Матч видалено.</div>`);
    document.getElementById('matchCard').style.display = 'none';
    currentMatchId = null;
    toast('Матч видалено', 'ok');
  }catch(err){
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }
});

/* ================= MATCHES: play round + coin flip animation ================= */
document.getElementById('roundForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  if(!currentMatchId){ toast('Спочатку відкрийте матч', 'err'); return; }
  const choice = document.getElementById('round-choice').value;
  const resultEl = document.getElementById('roundResult');
  const btn = document.getElementById('roundSubmitBtn');
  btn.disabled = true;

  const coin = document.getElementById('coinflip');
  const coinResultLabel = document.getElementById('coinflipResult');
  coin.classList.remove('spin','tails');
  void coin.offsetWidth; /* restart CSS animation */
  coinResultLabel.innerHTML = 'Підкидаємо монету…';

  try{
    const round = await api(`/matches/${currentMatchId}/rounds`, {
      method:'POST',
      body:{ coin_choice: choice },
    });

    coin.classList.add('spin');
    if(round.coin_result === 'tails') coin.classList.add('tails');

    setTimeout(()=>{
      coinResultLabel.innerHTML = `Випало: <b>${round.coin_result==='heads'?'Орел':'Решка'}</b> — перемогла сторона ${round.winner_side}`;
    }, 1350);

    showResult(resultEl, `
      <div class="kv"><span class="k">Раунд</span><span class="v">#${round.round_number}</span></div>
      <div class="kv"><span class="k">Вибір</span><span class="v">${round.coin_choice==='heads'?'Орел':'Решка'}</span></div>
      <div class="kv"><span class="k">Результат</span><span class="v">${round.coin_result==='heads'?'Орел':'Решка'}</span></div>
      <div class="kv"><span class="k">Перемогла сторона</span><span class="v">${round.winner_side}</span></div>
    `);

    const match = await api('/matches/' + currentMatchId);
    const rounds = await api('/matches/' + currentMatchId + '/rounds');
    setTimeout(()=> renderMatch(match, rounds), 400);

    if(match.status === 'finished'){
      toast('Матч завершено! MMR перераховано.', 'ok');
    }
  }catch(err){
    coinResultLabel.textContent = 'Оберіть сторону та підкиньте монету';
    showResult(resultEl, `<div class="error-msg">${esc(err.message)}</div>`, true);
    toast(err.message, 'err');
  }finally{
    btn.disabled = false;
  }
});

/* ================= LEADERBOARD ================= */
let lbMode = 'solo';
let lbPage = 1;
document.getElementById('lbModeSeg').addEventListener('click', (e)=>{
  const btn = e.target.closest('button');
  if(!btn) return;
  document.querySelectorAll('#lbModeSeg button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  lbMode = btn.dataset.mode;
  lbPage = 1;
  document.getElementById('lb-page').value = 1;
  loadLeaderboard();
});
document.getElementById('lbLoadBtn').addEventListener('click', ()=>{
  lbPage = Math.max(1, parseInt(document.getElementById('lb-page').value, 10) || 1);
  loadLeaderboard();
});
document.getElementById('lbPrevBtn').addEventListener('click', ()=>{
  lbPage = Math.max(1, lbPage - 1);
  document.getElementById('lb-page').value = lbPage;
  loadLeaderboard();
});
document.getElementById('lbNextBtn').addEventListener('click', ()=>{
  lbPage += 1;
  document.getElementById('lb-page').value = lbPage;
  loadLeaderboard();
});

async function loadLeaderboard(){
  const list = document.getElementById('lbList');
  const empty = document.getElementById('lbEmpty');
  const limit = parseInt(document.getElementById('lb-limit').value, 10) || 20;
  const sortDir = document.getElementById('lb-sort').value;
  const offset = (lbPage - 1) * limit;
  list.innerHTML = '<div class="empty">Завантаження…</div>';
  empty.style.display = 'none';
  try{
    const rows = await api(`/leaderboard/${lbMode}?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}&sort_dir=${encodeURIComponent(sortDir)}`);
    document.getElementById('lbPrevBtn').disabled = lbPage <= 1;
    document.getElementById('lbNextBtn').disabled = rows.length < limit;
    if(!rows.length){
      list.innerHTML = '';
      empty.style.display = 'block';
      empty.textContent = lbPage > 1 ? 'На цій сторінці нікого немає — спробуйте попередню.' : 'Даних для показу немає';
      return;
    }
    list.innerHTML = rows.map(r => {
      const topClass = r.rank_position===1?'top1':r.rank_position===2?'top2':r.rank_position===3?'top3':'';
      return `<div class="lb-row ${topClass}">
        <div class="rk">#${r.rank_position}</div>
        <div class="uname">${esc(r.username)}</div>
        <span class="pill ${rankNameToClass(r.rank_name)}">${esc(r.rank_name)}</span>
        <div class="mmrval">${r.mmr}</div>
      </div>`;
    }).join('');
  }catch(err){
    list.innerHTML = '';
    empty.style.display = 'block';
    empty.textContent = err.message;
    toast(err.message, 'err');
  }
}

/* ================= init ================= */
autofillMyId();
loadLeaderboard();