/* ════════════════════════════════════════
   STATE
════════════════════════════════════════ */
let currentUser = null;
let analysisHistory = [];

/* ════════════════════════════════════════
   AUTH
════════════════════════════════════════ */
function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t, i) => {
    t.classList.toggle('active', (tab === 'login' && i === 0) || (tab === 'register' && i === 1));
  });
  document.getElementById('login-form').style.display    = tab === 'login'    ? 'block' : 'none';
  document.getElementById('register-form').style.display = tab === 'register' ? 'block' : 'none';
}

function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const pass  = document.getElementById('login-pass').value;
  if (!email || !pass) { alert('Preencha e-mail e senha.'); return; }

  const users = JSON.parse(localStorage.getItem('curriculo_users') || '[]');
  const user  = users.find(u => u.email === email && u.pass === pass);
  if (!user) { alert('E-mail ou senha incorretos.'); return; }
  loginUser(user);
}

function doRegister() {
  const name  = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const pass  = document.getElementById('reg-pass').value;
  if (!name || !email || !pass)  { alert('Preencha todos os campos.'); return; }
  if (pass.length < 6)           { alert('Senha deve ter ao menos 6 caracteres.'); return; }

  const users = JSON.parse(localStorage.getItem('curriculo_users') || '[]');
  if (users.find(u => u.email === email)) { alert('E-mail já cadastrado.'); return; }

  const user = { name, email, pass };
  users.push(user);
  localStorage.setItem('curriculo_users', JSON.stringify(users));
  loginUser(user);
}

function loginUser(user) {
  currentUser = user;
  localStorage.setItem('curriculo_session', JSON.stringify(user));

  document.getElementById('user-display-name').textContent  = user.name;
  document.getElementById('user-display-email').textContent = user.email;
  document.getElementById('user-initials').textContent =
    user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  analysisHistory = JSON.parse(localStorage.getItem('curriculo_history_' + user.email) || '[]');
  showScreen('screen-dashboard');
}

function doLogout() {
  currentUser = null;
  localStorage.removeItem('curriculo_session');
  showScreen('screen-auth');
}

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

/* ════════════════════════════════════════
   NAVIGATION
════════════════════════════════════════ */
function switchNav(page) {
  document.querySelectorAll('.nav-item[id^="nav-"]').forEach(n => n.classList.remove('active'));
  document.getElementById('nav-' + page).classList.add('active');
  document.getElementById('page-analyze').style.display = page === 'analyze' ? 'block' : 'none';
  document.getElementById('page-history').style.display = page === 'history' ? 'block' : 'none';
  if (page === 'history') renderHistory();
}

/* ════════════════════════════════════════
   TABS (resultado)
════════════════════════════════════════ */
function switchTab(btn, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

/* ════════════════════════════════════════
   ANÁLISE COM IA
════════════════════════════════════════ */
async function startAnalysis() {
  const jobTitle   = document.getElementById('job-title').value.trim();
  const jobDesc    = document.getElementById('job-desc').value.trim();
  const resumeText = document.getElementById('resume-text').value.trim();

  if (!jobTitle)   { alert('Informe o título da vaga.'); return; }
  if (!jobDesc)    { alert('Cole a descrição da vaga.'); return; }
  if (!resumeText) { alert('Cole o texto do seu currículo.'); return; }

  // mostrar loading
  document.getElementById('analyze-form-view').style.display    = 'none';
  document.getElementById('analyze-loading-view').style.display = 'block';

  // animar etapas
  const stepsEl = ['step1','step2','step3','step4'];
  let si = 0;
  const stepTimer = setInterval(() => {
    if (si < stepsEl.length) {
      const el = document.getElementById(stepsEl[si]);
      el.classList.add('done');
      el.querySelector('i').className = 'ti ti-check';
      si++;
    }
  }, 1400);

  const prompt = `Você é um especialista sênior em recrutamento e análise de currículos. Analise o currículo abaixo considerando a vaga indicada.

Responda APENAS com um objeto JSON válido (sem markdown, sem backticks, sem texto fora do JSON) com as seguintes chaves:

{
  "compatibility_score": número inteiro de 0 a 100,
  "compatibility_label": texto curto como "Alta compatibilidade", "Compatibilidade média" ou "Baixa compatibilidade",
  "strengths_count": número de pontos fortes identificados,
  "analysis": "Avaliação geral em 3 a 5 parágrafos: perfil do candidato, o que o destaca para a vaga, riscos ou lacunas, e uma conclusão sobre as chances.",
  "improvements": "Lista numerada de 4 a 6 pontos específicos e práticos: habilidades que faltam e como desenvolvê-las, palavras-chave da vaga que deveriam aparecer no currículo, experiências que poderiam ser descritas com mais clareza, etc.",
  "rewrite": "Currículo COMPLETO reestruturado. Use SOMENTE as informações do currículo original — nunca invente dados. Reorganize a ordem das seções para priorizar o que é mais relevante para ESTA vaga. Use linguagem mais clara, objetiva e com impacto. Inclua naturalmente palavras-chave da vaga onde fizerem sentido real. Formate com cabeçalhos em MAIÚSCULAS e bullets onde apropriado."
}

=== VAGA ===
Título: ${jobTitle}

${jobDesc}

=== CURRÍCULO ===
${resumeText}`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }]
      })
    });

    clearInterval(stepTimer);
    stepsEl.forEach(s => {
      const el = document.getElementById(s);
      el.classList.add('done');
      el.querySelector('i').className = 'ti ti-check';
    });

    const data = await response.json();
    let text = (data.content || []).map(b => b.text || '').join('').trim();
    text = text.replace(/^```json\s*/,'').replace(/```\s*$/,'').trim();

    const result = JSON.parse(text);
    const entry  = { ...result, jobTitle, timestamp: new Date().toLocaleString('pt-BR') };

    saveToHistory(entry);
    renderResults(entry);

    setTimeout(() => {
      document.getElementById('analyze-loading-view').style.display = 'none';
      document.getElementById('analyze-results-view').style.display = 'block';
    }, 500);

  } catch (err) {
    clearInterval(stepTimer);
    document.getElementById('analyze-loading-view').style.display = 'none';
    document.getElementById('analyze-form-view').style.display    = 'block';
    alert('Erro ao processar a análise. Verifique os campos e tente novamente.\n\nDetalhe: ' + err.message);
    console.error(err);
  }
}

function renderResults(r) {
  document.getElementById('result-job-title-display').textContent = 'Vaga: ' + r.jobTitle + ' · ' + r.timestamp;

  // score de compatibilidade
  const score = parseInt(r.compatibility_score) || 0;
  const c1    = document.getElementById('score-circle-1');
  c1.textContent = score + '%';
  c1.className   = 'score-circle ' + (score >= 70 ? 'good' : score >= 40 ? 'medium' : 'low');
  document.getElementById('score-label-1').textContent = r.compatibility_label || '—';

  // pontos fortes
  const c2 = document.getElementById('score-circle-2');
  c2.textContent = r.strengths_count || '—';
  c2.className   = 'score-circle good';
  document.getElementById('score-label-2').textContent = 'pontos identificados';

  // textos
  document.getElementById('result-analysis').textContent    = r.analysis    || '—';
  document.getElementById('result-improvements').textContent = r.improvements || '—';
  document.getElementById('result-rewrite').textContent      = r.rewrite     || '—';

  // resetar para a primeira aba
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('active', i === 0));
  document.querySelectorAll('.tab-content').forEach((c,i) => c.classList.toggle('active', i === 0));
}

function resetAnalysis() {
  document.getElementById('analyze-results-view').style.display = 'none';
  document.getElementById('analyze-form-view').style.display    = 'block';
  ['step1','step2','step3','step4'].forEach(s => {
    const el = document.getElementById(s);
    el.classList.remove('done');
    el.querySelector('i').className = 'ti ti-clock';
  });
}

function copyRewrite() {
  const text = document.getElementById('result-rewrite').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('#tab-rewrite .copy-btn');
    btn.innerHTML = '<i class="ti ti-check"></i> Copiado!';
    setTimeout(() => { btn.innerHTML = '<i class="ti ti-copy"></i> Copiar texto'; }, 2500);
  }).catch(() => alert('Não foi possível copiar. Selecione e copie manualmente.'));
}

/* ════════════════════════════════════════
   HISTÓRICO
════════════════════════════════════════ */
function saveToHistory(entry) {
  if (!currentUser) return;
  analysisHistory.unshift(entry);
  if (analysisHistory.length > 30) analysisHistory = analysisHistory.slice(0, 30);
  localStorage.setItem('curriculo_history_' + currentUser.email, JSON.stringify(analysisHistory));
}

function renderHistory() {
  const list = document.getElementById('history-list');
  if (!analysisHistory.length) {
    list.innerHTML = `
      <div class="empty-state">
        <i class="ti ti-file-off"></i>
        <p>Nenhuma análise ainda.<br>Faça sua primeira análise!</p>
      </div>`;
    return;
  }
  list.innerHTML = analysisHistory.map((item, i) => {
    const score = parseInt(item.compatibility_score) || 0;
    const cls   = score >= 70 ? 'good' : score >= 40 ? 'medium' : 'low';
    const colors = {
      good:   { bg: '#E1F5EE', color: '#085041' },
      medium: { bg: '#FAEEDA', color: '#633806' },
      low:    { bg: '#FCEBEB', color: '#501313' }
    };
    const c = colors[cls];
    return `
      <div class="history-card" onclick="loadHistoryItem(${i})">
        <div>
          <h4>${item.jobTitle}</h4>
          <p>${item.timestamp}</p>
        </div>
        <div class="history-badge" style="background:${c.bg}; color:${c.color};">${score}% compat.</div>
      </div>`;
  }).join('');
}

function loadHistoryItem(i) {
  const entry = analysisHistory[i];
  switchNav('analyze');
  document.getElementById('analyze-form-view').style.display    = 'none';
  document.getElementById('analyze-loading-view').style.display = 'none';
  renderResults(entry);
  document.getElementById('analyze-results-view').style.display = 'block';
}

/* ════════════════════════════════════════
   INICIALIZAÇÃO — restaurar sessão
════════════════════════════════════════ */
(function init() {
  const session = localStorage.getItem('curriculo_session');
  if (session) {
    try { loginUser(JSON.parse(session)); } catch(e) { localStorage.removeItem('curriculo_session'); }
  }
})();