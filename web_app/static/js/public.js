(function () {
  const header = document.getElementById('siteHeader');
  const onScroll = () => {
    if (!header) return;
    header.classList.toggle('scrolled', window.scrollY > 8);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  const toggle = document.getElementById('navToggle');
  const nav = document.getElementById('siteNav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => nav.classList.toggle('open'));
    nav.querySelectorAll('a').forEach((link) =>
      link.addEventListener('click', () => nav.classList.remove('open'))
    );
  }

  const launcher = document.getElementById('chatLauncher');
  const panel = document.getElementById('chatPanel');
  const closeBtn = document.getElementById('chatClose');
  const body = document.getElementById('chatBody');
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatText');
  if (!launcher || !panel || !form) return;

  const history = [];
  let greeted = false;
  let busy = false;

  const scrollDown = () => { body.scrollTop = body.scrollHeight; };

  const addMessage = (role, text) => {
    const el = document.createElement('div');
    el.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-bot');
    el.textContent = text;
    body.appendChild(el);
    scrollDown();
    return el;
  };

  const openPanel = () => {
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    launcher.classList.add('hidden');
    if (!greeted) {
      addMessage('bot', 'Hi, I am the AlertEye assistant. Ask me about features, setup, pricing or anything else.');
      greeted = true;
    }
    input.focus();
  };

  const closePanel = () => {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    launcher.classList.remove('hidden');
  };

  launcher.addEventListener('click', openPanel);
  closeBtn.addEventListener('click', closePanel);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;

    busy = true;
    input.value = '';
    addMessage('user', text);
    history.push({ role: 'user', content: text });

    const typing = document.createElement('div');
    typing.className = 'msg-typing';
    typing.textContent = 'Assistant is typing...';
    body.appendChild(typing);
    scrollDown();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history })
      });
      const data = await res.json();
      const reply = data.reply || 'Sorry, I could not answer that. Please try the contact page.';
      typing.remove();
      addMessage('bot', reply);
      history.push({ role: 'assistant', content: reply });
    } catch (err) {
      typing.remove();
      addMessage('bot', 'Connection problem. Please try again in a moment.');
    } finally {
      busy = false;
      input.focus();
    }
  });
})();
