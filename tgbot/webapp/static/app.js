const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
tg?.setHeaderColor?.('#05060a');
tg?.setBackgroundColor?.('#05060a');
window.MiniIcons.hydrate();
const icon = (name) => window.MiniIcons.render(name);

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const user = tg?.initDataUnsafe?.user;
const CURRENCY_SIGNS = { RUB: '₽', USD: '$', EUR: '€', AMD: '֏' };
const LANGS = { ru: 'Հայերեն', en: 'English', ua: 'Ուկրաիներեն', hy: 'Հայերեն' };

let token = null;
let products = [];
let profile = null;
let ordersLoaded = false;
let sheetAction = null;
let toastTimer = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}

function haptic(type = 'light') { tg?.HapticFeedback?.impactOccurred?.(type); }

function notify(message, success = false) {
  const toast = $('#toast');
  $('#toast-text').textContent = message;
  toast.classList.toggle('success', success);
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 2800);
}

function formatMoney(value, sign = '₽') {
  return `${Number(value || 0).toLocaleString('hy-AM', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).replace(/\u00a0/g, ' ')} ${sign}`;
}

function formatDate(unix) {
  if (!unix) return '—';
  return new Date(unix * 1000).toLocaleDateString('hy-AM', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function formatDateTime(unix) {
  if (!unix) return '—';
  return new Date(unix * 1000).toLocaleString('hy-AM', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function setAvatar(node, fallback, photoUrl) {
  node.textContent = (fallback || 'A')[0].toUpperCase();
  if (photoUrl) {
    node.style.backgroundImage = `url("${String(photoUrl).replace(/["\\]/g, '')}")`;
    node.classList.add('has-photo');
  }
}

async function api(path, options = {}) {
  const headers = {...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {...options, headers});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' && /[\u0531-\u0587]/.test(body.detail) ? body.detail : 'Չհաջողվեց կատարել գործողությունը։ Ստուգեք տվյալներն ու մնացորդը և փորձեք կրկին։');
  }
  return response.json();
}

async function authorize() {
  if (!tg?.initData || !user) return false;
  try {
    const data = await api('/api/auth/telegram', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData}),
    });
    token = data.access_token;
    return true;
  } catch (error) {
    console.error('Mini App auth failed', error);
    return false;
  }
}

function animateBalance(target, sign) {
  const node = $('#balance');
  const start = performance.now();
  const duration = 650;
  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 4);
    node.textContent = formatMoney(target * eased, sign);
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function renderProfile(data) {
  profile = data;
  const name = data.full_name || user?.first_name || 'Telegram օգտատեր';
  const username = data.user_name ? `@${data.user_name}` : 'Username-ը նշված չէ';
  setAvatar($('#profile-avatar'), name, user?.photo_url);
  $('#profile-name').textContent = name;
  $('#profile-username').textContent = username;
  $('#profile-role').textContent = data.is_admin ? 'Ադմինիստրատոր' : 'Հաճախորդ';
  $('#profile-role').classList.toggle('admin', data.is_admin);
  $('#profile-language').textContent = 'Հայերեն';
  $('#profile-id').textContent = data.user_id;
  $('#profile-user-detail').textContent = username;
  $('#stat-reg-date').textContent = data.reg_date || '—';
  $('#profile-referrer').textContent = data.ref_id ? `ID ${data.ref_id}` : 'Նշված չէ';
  $('#stat-total-refill').textContent = formatMoney(data.total_refill, '₽');
  $('#stat-ref-count').textContent = data.ref_count;
  $('#stat-refills').textContent = data.count_refills;
  $('#wallet-currency').textContent = `Հիմնական հաշիվ · ${data.currency}`;
  const balanceCurrency = String(data.currency || 'RUB').toLowerCase();
  animateBalance(Number(data.balance[balanceCurrency] || 0), data.currency_sign || '₽');

  const balances = [
    ['RUB', data.balance.rub, '₽'], ['USD', data.balance.usd, '$'],
    ['EUR', data.balance.eur, '€'], ['AMD', data.balance.amd, '֏'],
  ];
  $('#profile-balances').innerHTML = balances.map(([code, value, sign], index) => `
    <div class="balance-row" style="--i:${index}">
      <span class="currency-icon">${sign}</span><span><small>${code}</small><b>${formatMoney(value, sign)}</b></span>
    </div>`).join('');
}

async function loadProfile() {
  try { renderProfile(await api('/api/me')); }
  catch (error) { console.error(error); notify('Չհաջողվեց բեռնել հաշվի տվյալները։'); }
}

function orderStatus(order) {
  const labels = {completed:'Կատարված է', paid:'Վճարված է', created:'Ստեղծված է', awaiting_payment:'Սպասում է վճարմանը', processing:'Մշակվում է', cancelled:'Չեղարկված է', fulfillment_failed:'Առաքման սխալ', refund_pending:'Սպասում է վերադարձին', refunded:'Վերադարձված է'};
  return labels[order.status] || (order.kind === 'shop' ? 'Կատարված է' : 'Ստուգվում է');
}

function productTheme(id) {
  if (String(id).startsWith('shop:')) return 'goods';
  return id === 'premium' ? 'premium' : id === 'gift' ? 'gift' : 'stars';
}

let selectedCategory = 'all';
let selectedSubcategory = 'all';

function bindProductCards(container) {
  $$('[data-product]', container).forEach((button) => button.addEventListener('click', () => openProduct(button.dataset.product)));
  $$('img', container).forEach((img) => img.addEventListener('error', () => { img.hidden = true; img.parentElement.classList.add('image-failed'); }));
}

function productCards(items) {
  return items.map((item, index) => `
    <article class="product ${productTheme(item.id)} ${item.image && item.category === 'goods' ? 'with-cover' : ''}" style="--i:${Math.min(index, 8)}">
      ${item.image ? `<div class="catalog-cover"><img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}" loading="lazy" referrerpolicy="no-referrer"></div>` : `<div class="catalog-placeholder">${icon('package')}</div>`}
      <div class="product-copy"><small class="product-category">${escapeHtml(item.category_name || 'Telegram')}</small>
      <h3>${escapeHtml(item.title)}</h3><p class="product-summary">${escapeHtml(item.subtitle)}</p>
      ${item.price != null ? `<strong class="product-price">${formatMoney(item.price, item.currency_sign)}</strong>` : ''}
      <button type="button" data-product="${escapeHtml(item.id)}"><span>Մանրամասն</span><b>${icon('arrow-right')}</b></button></div>
    </article>`).join('') || `<div class="empty-state"><span>${icon('package')}</span><b>Այստեղ դեռ դատարկ է</b><p>Ընտրեք այլ բաժին։</p></div>`;
}

function renderProducts() {
  const goods = products.filter((item) => item.category === 'goods');
  const categories = [...new Map(goods.map((item) => [item.category_id || 'uncategorized', item.category_name || 'Այլ ապրանքներ'])).entries()];
  if (selectedCategory !== 'all' && !categories.some(([id]) => id === selectedCategory)) selectedCategory = 'all';
  const atRoot = selectedCategory === 'all';
  $('#catalog-title').textContent = atRoot ? 'Կատալոգ' : categories.find(([id]) => id === selectedCategory)?.[1] || 'Ապրանքներ';
  $('#categories').hidden = !atRoot;
  $('#categories-back').hidden = atRoot;
  $('#products').hidden = atRoot;
  $('#categories').innerHTML = categories.map(([id, name], index) => {
    const members = goods.filter((item) => (item.category_id || 'uncategorized') === id);
    const cover = members.find((item) => item.image)?.image;
    return `<button type="button" class="category-tile" data-category="${escapeHtml(id)}" style="--i:${Math.min(index, 8)}">
      <span class="category-art">${cover ? `<img src="${escapeHtml(cover)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : icon('package')}</span>
      <strong>${escapeHtml(name)}</strong></button>`;
  }).join('') || '<div class="empty-state"><b>Կատալոգը դեռ դատարկ է</b><p>Ապրանքները շուտով կհայտնվեն։</p></div>';
  $$('[data-category]', $('#categories')).forEach((button) => button.addEventListener('click', () => {
    selectedCategory = button.dataset.category; selectedSubcategory = 'all'; renderProducts(); haptic();
  }));
  $$('img', $('#categories')).forEach((img) => img.addEventListener('error', () => {
    img.parentElement.innerHTML = icon('package');
  }));
  $('#categories-back').onclick = () => { selectedCategory = 'all'; selectedSubcategory = 'all'; renderProducts(); haptic(); };
  const categoryGoods = goods.filter((item) => selectedCategory === 'all' || item.category_id === selectedCategory);
  const subcategories = [...new Map(categoryGoods.filter((item) => item.subcategory_id).map((item) => [item.subcategory_id, item.subcategory_name])).entries()];
  if (!subcategories.some(([id]) => id === selectedSubcategory)) selectedSubcategory = 'all';
  $('#subcategories').hidden = selectedCategory === 'all' || !subcategories.length;
  $('#subcategories').innerHTML = [['all', 'Ամբողջ բաժինը'], ...subcategories].map(([id, name]) => `<button type="button" data-subcategory="${escapeHtml(id)}" class="${selectedSubcategory === id ? 'active' : ''}">${escapeHtml(name)}</button>`).join('');
  $$('[data-subcategory]').forEach((button) => button.addEventListener('click', () => { selectedSubcategory = button.dataset.subcategory; renderProducts(); }));
  const visible = categoryGoods.filter((item) => selectedSubcategory === 'all' || item.subcategory_id === selectedSubcategory);
  $('#product-count').hidden = atRoot;
  $('#product-count').textContent = `Ապրանքներ՝ ${visible.length}`;
  $('#products').innerHTML = atRoot ? '' : productCards(visible);
  $('#digital-products').innerHTML = productCards(products.filter((item) => ['stars', 'premium'].includes(item.id)));
  bindProductCards($('#products')); bindProductCards($('#digital-products'));
}

function openDigitalWizard(product) {
  let step = 1, mode = 'self', username = '', quantity = product.id === 'stars' ? 50 : 3, busy = false;
  let quote = null;
  function draw() {
    const heading = ['Ստացող', product.id === 'stars' ? 'Աստղերի քանակը' : 'Բաժանորդագրության ժամկետը', 'Հաստատում'][step - 1];
    let content = `<div class="wizard-steps">${['Ո՞ւմ', 'Քանակ', 'Վճարում'].map((label, i) => `<span class="${i + 1 <= step ? 'done' : ''}">${i + 1}<small>${label}</small></span>`).join('')}</div><div class="wizard-stage">`;
    if (step === 1) content += `<div class="option-grid recipient-options"><button type="button" data-recipient="self" class="${mode === 'self' ? 'selected' : ''}">${icon('user-round')}<small>Ինձ համար</small></button><button type="button" data-recipient="other" class="${mode === 'other' ? 'selected' : ''}">${icon('gift')}<small>Ուրիշին</small></button></div><label class="amount-field" id="recipient-field" ${mode === 'self' ? 'hidden' : ''}><span>Ստացողի Telegram username</span><div><input id="digital-username" type="text" maxlength="33" autocomplete="off" placeholder="@username" value="${escapeHtml(username)}"></div></label><p class="delivery-warning" id="self-username">${mode === 'self' ? (profile?.user_name ? `Ստացող: @${escapeHtml(profile.user_name)}` : 'Ձեզ համար գնելու համար սահմանեք Telegram username։') : 'Մուտքագրեք username-ը, ոչ թե հեռախոսահամարը։'}</p>`;
    if (step === 2) {
      const options = product.id === 'stars' ? [50, 100, 500] : [3, 6, 12];
      content += `<div class="option-grid">${options.map((value) => `<button type="button" data-quantity="${value}" class="${quantity === value ? 'selected' : ''}">${value}<small>${product.id === 'stars' ? 'Stars' : 'ամիս'}</small></button>`).join('')}</div>`;
      if (product.id === 'stars') content += `<label class="amount-field shop-quantity"><span>Իմ քանակը · 50-ից 4999</span><div><input id="stars-quantity" type="number" min="50" max="4999" step="1" inputmode="numeric" value="${quantity}"><b>Stars</b></div></label>`;
    }
    if (step === 3) content += `<div class="order-detail"><div><span>Ապրանք</span><b>${escapeHtml(product.title)}</b></div><div><span>Ստացող</span><b>@${escapeHtml(quote.recipient)}</b></div><div><span>Քանակ</span><b>${quantity}${product.id === 'premium' ? ' ամիս' : ' Stars'}</b></div><div><span>Վճարման ենթակա</span><b>${formatMoney(quote.total)}</b></div></div><p class="delivery-warning">${escapeHtml(quote.payment_message || 'Վճարումը կշարունակվի բոտի զրույցում։')}</p>`;
    content += `${step > 1 ? '<button type="button" class="redeliver-action" id="wizard-back">Հետ</button>' : ''}</div>`;
    openSheet({icon: product.id === 'stars' ? 'star' : 'crown', title: product.title, subtitle: heading, content,
      button: step === 3 ? 'Շարունակել բոտում' : step === 2 ? 'Ստուգել և շարունակել' : 'Հաջորդը',
      note: 'Ձևակերպումը՝ Mini App-ում։ Հաշվարկի ընթացքում գումար չի գանձվում։',
      onContinue: async () => {
        if (busy) return;
        if (step === 1) { step = 2; draw(); return; }
        if (step === 3) return sendToBot({action:'digital_select', product:product.id, quantity, recipient_mode:mode, username:quote?.recipient || username});
        if (step !== 2) return;
        busy = true; $('#sheet-continue').disabled = true;
        const action = sheetAction;
        try {
          quote = await api('/api/digital/quote', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({product:product.id, quantity, recipient_mode:mode, username})});
          if (sheetAction === action && !$('#sheet-backdrop').hidden) { step = 3; draw(); }
        } catch (error) { notify(error.message || 'Հաշվարկը ժամանակավորապես հասանելի չէ։'); }
        finally { busy = false; if (sheetAction === action && step === 2) validate(); }
      }});
    $$('[data-recipient]').forEach((button) => button.addEventListener('click', () => { mode = button.dataset.recipient; draw(); }));
    $('#digital-username')?.addEventListener('input', (event) => { username = event.target.value; validate(); });
    $$('[data-quantity]').forEach((button) => button.addEventListener('click', () => { quantity = Number(button.dataset.quantity); draw(); }));
    $('#stars-quantity')?.addEventListener('input', (event) => {
      quantity = Number(event.target.value);
      $$('[data-quantity]').forEach((button) => button.classList.toggle('selected', Number(button.dataset.quantity) === quantity));
      validate();
    });
    $('#wizard-back')?.addEventListener('click', () => { if (!busy) { step--; draw(); } });
    validate();
  }
  function validate() {
    const name = (mode === 'self' ? profile?.user_name || '' : username).replace(/^@/, '').trim();
    const validQuantity = product.id === 'stars' ? Number.isInteger(quantity) && quantity >= 50 && quantity <= 4999 : [3, 6, 12].includes(quantity);
    $('#sheet-continue').disabled = !token || busy || (step === 1 ? !/^[A-Za-z][A-Za-z0-9_]{2,31}$/.test(name) : !validQuantity);
    $('#stars-quantity')?.classList.toggle('invalid', !validQuantity);
  }
  draw();
}

async function loadProducts() {
  try {
    const data = await api('/api/digital/products');
    products = (data.products || []).map((item) => item.id === 'stars' ? {...item, subtitle:'Սկսած 50 աստղից'} : item.id === 'premium' ? {...item, subtitle:'3, 6 կամ 12 ամիս'} : item);
    renderProducts();
  } catch (error) {
    console.error(error);
    $('#categories').hidden = true; $('#products').hidden = false;
    $('#products').innerHTML = `<div class="empty-state"><span>${icon('triangle-alert')}</span><b>Կատալոգը հասանելի չէ</b><p>Ստուգեք կապը և փորձեք կրկին։</p></div>`;
  }
}

function openSheet({icon: iconName = 'sparkles', title, subtitle, content = '', button = 'Շարունակել', note = '', onContinue}) {
  $('#sheet-icon').innerHTML = icon(iconName);
  $('#sheet-title').textContent = title;
  $('#sheet-subtitle').textContent = subtitle;
  $('#sheet-content').innerHTML = content;
  $('#sheet-continue').textContent = button;
  $('#sheet-continue').disabled = true;
  $('#sheet-note').textContent = note || 'Ստուգեք տվյալները հաստատելուց առաջ';
  $$('img', $('#sheet-content')).forEach((img) => img.addEventListener('error', () => { img.hidden = true; }));
  sheetAction = onContinue;
  $('#sheet-backdrop').hidden = false;
  tg?.BackButton?.show?.();
  haptic();
}

function closeSheet() {
  $('#sheet-backdrop').hidden = true;
  sheetAction = null;
  tg?.BackButton?.hide?.();
}

function sendToBot(payload) {
  if (!tg?.sendData) {
    notify('Բացեք Mini App-ը Telegram-ի կոճակով։');
    return false;
  }
  haptic('medium');
  tg.sendData(JSON.stringify(payload));
  notify('Պատրաստ է։ Շարունակեք բոտի հետ զրույցում։', true);
  setTimeout(() => tg.close(), 650);
  return true;
}

function newPurchaseKey() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function openProduct(productId) {
  const product = products.find((item) => item.id === productId);
  if (!product) return notify('Ապրանքը ժամանակավորապես հասանելի չէ։');
  if (productId.startsWith('shop:')) {
    let pending = false;
    const purchaseKey = newPurchaseKey();
    const positionId = Number(productId.split(':')[1]);
    openSheet({
      icon: 'package', title: product.title,
      subtitle: `${formatMoney(product.price, product.currency_sign)} մեկ հատի համար · ${product.category_name || 'Ապրանքներ'}`,
      content: `${product.image ? `<img class="detail-cover" src="${escapeHtml(product.image)}" alt="${escapeHtml(product.title)}" referrerpolicy="no-referrer">` : ''}<p class="sheet-description product-description">${escapeHtml(product.description || product.subtitle)}</p>
        <label class="amount-field shop-quantity"><span>Քանակ · 1-ից 10</span><div><input id="purchase-quantity" type="number" inputmode="numeric" min="1" max="10" step="1" value="1"><b>հատ</b></div></label>
        <div class="checkout-total"><span>Հաշվեկշռից վճարման ենթակա</span><strong id="purchase-total">${formatMoney(product.price, product.currency_sign)}</strong></div>`,
      button: 'Գնել',
      note: token ? 'Գինը, առկա քանակը և մնացորդը ստուգվում են վճարումից առաջ' : 'Գնելու համար բացեք Mini App-ը Telegram-ից',
      onContinue: async () => {
        if (pending || !token) return;
        const quantity = Number($('#purchase-quantity').value);
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10) return;
        pending = true;
        $('#sheet-continue').disabled = true;
        try {
          const result = await api('/api/shop/purchase', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({position_id: positionId, quantity, idempotency_key: purchaseKey,
              expected_unit_price: product.price, expected_currency: product.currency}),
          });
          ordersLoaded = false;
          await Promise.all([loadProfile(), loadProducts()]);
          notify('Գնումը ձևակերպված է', true);
          await showOrder('shop', result.receipt, result.delivery_status);
        } catch (error) {
          console.error(error);
          notify(error.message || 'Չհաջողվեց ձևակերպել գնումը։');
        } finally {
          pending = false;
          if (!$('#sheet-backdrop').hidden && $('#purchase-quantity')) update();
        }
      },
    });
    const qty = $('#purchase-quantity');
    const update = () => {
      const quantity = Number(qty.value);
      const validQuantity = Number.isInteger(quantity) && quantity >= 1 && quantity <= 10;
      qty.classList.toggle('invalid', Boolean(qty.value) && !validQuantity);
      $('#purchase-total').textContent = validQuantity ? formatMoney(product.price * quantity, product.currency_sign) : '—';
      $('#sheet-continue').disabled = pending || !token || !validQuantity;
    };
    qty.addEventListener('input', update);
    update();
    return;
  }
  if (['stars', 'premium'].includes(productId)) return openDigitalWizard(product);
  notify('Այս բաժինը դեռ հասանելի չէ։');
}

async function openTopup() {
  if (!token) return notify('Լիցքավորելու համար բացեք Mini App-ը Telegram-ում։');
  let config;
  try { config = await api('/api/payment-methods'); }
  catch (error) { console.error(error); return notify('Չհաջողվեց բեռնել վճարման եղանակները։'); }
  if (!config.enabled || !config.methods.length) return notify('Լիցքավորումն անջատված է ադմինիստրատորի կողմից։');

  let method = null;
  let amount = 0;
  const methodIcons = {cryptoBot: 'wallet', stars: 'star', custom_pay_method: 'credit-card'};
  openSheet({
    icon: 'plus', title: 'Հաշվեկշռի լիցքավորում',
    subtitle: `Մուտքագրեք գումարը՝ ${config.min_amount}-ից մինչև ${config.max_amount.toLocaleString('hy-AM')} ${config.currency_sign}`,
    content: `
      <label class="amount-field"><span>Գումար</span><div><input id="topup-amount" type="number" inputmode="decimal" min="${config.min_amount}" max="${config.max_amount}" placeholder="0"><b>${escapeHtml(config.currency_sign)}</b></div></label>
      <p class="choice-label">Վճարման եղանակ</p>
      <div class="payment-grid">${config.methods.map((item) => `<button type="button" data-method="${escapeHtml(item.id)}"><span>${icon(methodIcons[item.id] || 'credit-card')}</span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.subtitle || (item.id === 'stars' ? 'Վճարում Telegram Stars-ով' : 'Վճարում կրիպտոարժույթով'))}</small></button>`).join('')}</div>`,
    button: 'Ստեղծել հաշիվ', note: 'Հաշիվը կստեղծվի ադմինիստրատորի միացրած եղանակով',
    onContinue: async () => {
      if (!method || !amount) return;
      $('#sheet-continue').disabled = true;
      $('#sheet-continue').textContent = 'Ստեղծվում է...';
      try {
        const invoice = await api('/api/refill', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({method, amount}),
        });
        renderTopupInvoice(invoice);
      } catch (error) {
        console.error(error);
        notify(error.message || 'Չհաջողվեց ստեղծել վճարման հաշիվ։');
        $('#sheet-continue').textContent = 'Ստեղծել հաշիվ';
        validate();
      }
    },
  });
  const amountInput = $('#topup-amount');
  const validate = () => {
    amount = Number(amountInput.value || 0);
    const valid = amount >= config.min_amount && amount <= config.max_amount && method;
    $('#sheet-continue').disabled = !valid;
    amountInput.classList.toggle('invalid', Boolean(amountInput.value) && (amount < config.min_amount || amount > config.max_amount));
  };
  amountInput.addEventListener('input', validate);
  $$('#sheet-content [data-method]').forEach((button) => button.addEventListener('click', () => {
    $$('#sheet-content [data-method]').forEach((item) => item.classList.remove('selected'));
    button.classList.add('selected');
    method = button.dataset.method;
    validate(); haptic();
  }));
  setTimeout(() => amountInput.focus(), 250);
}

function renderTopupInvoice(invoice) {
  const hasPaymentLink = Boolean(invoice.pay_url);
  const checkPayload = JSON.stringify({
    method: invoice.method,
    receipt: invoice.receipt,
    amount: Number(invoice.amount || 0),
    second_amount: Number(invoice.second_amount || 0),
  });
  $('#sheet-title').textContent = invoice.status === 'existing' ? 'Ակտիվ հաշիվ' : 'Հաշիվը ստեղծված է';
  $('#sheet-subtitle').textContent = `${invoice.method_title || invoice.method} · ${invoice.second_amount}${invoice.currency_sign}`;
  $('#sheet-content').innerHTML = `
    <div class="order-detail">
      <div><span>Եղանակ</span><b>${escapeHtml(invoice.method_title || invoice.method)}</b></div>
      <div><span>Գումար</span><b>${escapeHtml(String(invoice.second_amount))}${escapeHtml(invoice.currency_sign)}</b></div>
      <div><span>ID</span><b>${escapeHtml(invoice.receipt)}</b></div>
      <div><span>Վերջնաժամկետ</span><b>${escapeHtml(invoice.under_date || '—')}</b></div>
    </div>
    ${invoice.instructions ? `<p class="delivery-warning">${invoice.instructions}</p>` : ''}
    <div class="invoice-actions">
      ${hasPaymentLink ? `<button type="button" class="primary-action" id="topup-pay">${icon('wallet')} Վճարել</button>` : ''}
      ${invoice.checkable ? `<button type="button" class="secondary-action" id="topup-check" data-check='${escapeHtml(checkPayload)}'>${icon('refresh')} Ստուգել վճարումը</button>` : ''}
    </div>
  `;
  $('#sheet-continue').textContent = 'Փակել';
  $('#sheet-continue').disabled = false;
  $('#sheet-continue').onclick = closeSheet;
  $('#topup-pay')?.addEventListener('click', () => {
    if (window.Telegram?.WebApp?.openLink) window.Telegram.WebApp.openLink(invoice.pay_url);
    else window.open(invoice.pay_url, '_blank', 'noopener');
  });
  $('#topup-check')?.addEventListener('click', async (buttonEvent) => {
    const button = buttonEvent.currentTarget;
    button.disabled = true;
    try {
      const result = await api('/api/refill/check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: button.dataset.check,
      });
      if (result.status === 'paid') {
        notify('Հաշվեկշիռը լիցքավորվել է։');
        await loadProfile();
        closeSheet();
      } else {
        notify('Վճարումը դեռ չի գտնվել։');
        button.disabled = false;
      }
    } catch (error) {
      console.error(error);
      notify(error.message || 'Չհաջողվեց ստուգել վճարումը։');
      button.disabled = false;
    }
  });
}

function statusClass(status) {
  if (['completed', 'paid'].includes(status)) return 'done';
  if (['cancelled', 'fulfillment_failed', 'refunded'].includes(status)) return 'bad';
  return 'pending';
}

async function loadOrders() {
  $('#orders').innerHTML = '<div class="loader"></div>';
  try {
    const data = await api('/api/orders');
    const orders = data.orders || [];
    $('#orders').innerHTML = orders.length ? orders.map((order, index) => `
      <button class="order" type="button" data-order-kind="${escapeHtml(order.kind)}" data-order-id="${escapeHtml(order.id)}" style="--i:${index}" aria-label="Պատվեր ${escapeHtml(order.title)}, ${escapeHtml(orderStatus(order))}">
        <div class="order-icon">${icon(order.kind === 'shop' ? 'package' : String(order.title).toLowerCase().includes('premium') ? 'crown' : 'star')}</div>
        <div class="order-body"><b>${escapeHtml(order.title)}</b><span>${escapeHtml(order.detail || '')}</span></div>
        <div class="order-right"><em class="chip ${statusClass(order.status)}">${escapeHtml(orderStatus(order))}</em><b>${formatMoney(order.amount, CURRENCY_SIGNS[order.currency] || order.currency)}</b><span>${formatDate(order.unix)}</span></div>
      </button>`).join('') : `<div class="empty-state"><span>${icon('clock-3')}</span><b>Պատվերներ դեռ չկան</b><p>Ձեր առաջին գնումը կհայտնվի այստեղ։</p></div>`;
    $$('[data-order-id]', $('#orders')).forEach((button) => button.addEventListener('click', () =>
      showOrder(button.dataset.orderKind, button.dataset.orderId)));
    ordersLoaded = true;
  } catch (error) {
    console.error(error);
    $('#orders').innerHTML = `<div class="empty-state"><span>${icon('triangle-alert')}</span><b>Պատմությունը հասանելի չէ</b><p>Բացեք Mini App-ը Telegram-ում։</p></div>`;
  }
}

async function showOrder(kind, orderId, deliveryStatus = null) {
  if (!token) return notify('Պատվերների պատմությունը հասանելի է Telegram-ում։');
  let order;
  try { order = await api(`/api/orders/${encodeURIComponent(kind)}/${encodeURIComponent(orderId)}`); }
  catch (error) { console.error(error); return notify('Չհաջողվեց բացել պատվերը։'); }
  const rows = [
    ['Պատվերի համարը', order.id],
    ['Ամսաթիվ և ժամ', formatDateTime(order.unix)],
    ['Կարգավիճակ', orderStatus(order)],
    ['Քանակ', String(order.quantity || '—')],
    ['Գումար', formatMoney(order.amount, CURRENCY_SIGNS[order.currency] || order.currency)],
  ];
  if (order.recipient) rows.push(['Ստացող', order.recipient]);
  if (order.completed_unix) rows.push(['Կատարված է', formatDateTime(order.completed_unix)]);
  const contents = (order.items || []).map((item, index) => item.kind === 'text'
    ? `<div class="delivery-item"><small>Ապրանք ${index + 1}</small><pre>${escapeHtml(item.text)}</pre></div>`
    : `<div class="delivery-item"><small>Ապրանք ${index + 1}</small><p>${escapeHtml(item.type)} ուղարկված է Telegram զրույցին${item.caption ? ` · ${escapeHtml(item.caption)}` : ''}</p></div>`).join('');
  openSheet({
    icon: kind === 'digital' ? 'star' : 'package',
    title: kind === 'digital' ? 'Պատվերի մանրամասներ' : 'AutoShop գնում', subtitle: order.title,
    content: `<div class="order-detail">${rows.map(([label, value]) =>
      `<div><span>${label}</span><b>${escapeHtml(value)}</b></div>`).join('')}</div>${contents}
      ${kind === 'shop' ? '<button class="redeliver-action" id="redeliver-order" type="button">Կրկին ուղարկել ապրանքը զրույցին</button>' : ''}
      ${deliveryStatus === 'not_sent' ? '<p class="delivery-warning">Ապրանքի հաղորդագրությունը չի առաքվել։ Տեքստը հասանելի է այս պատվերում։ Մեդիաֆայլի դեպքում դիմեք աջակցությանը՝ նշելով պատվերի համարը։</p>' : ''}`,
    button: 'Փակել', note: 'Պատվերը պահպանված է Mini App-ի պատմության մեջ', onContinue: closeSheet,
  });
  $('#sheet-continue').disabled = false;
  $('#redeliver-order')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await api(`/api/orders/shop/${encodeURIComponent(order.id)}/deliver`, {method: 'POST'});
      notify('Ապրանքը կրկին ուղարկվել է զրույցին', true);
    } catch (error) {
      console.error(error);
      notify(error.message || 'Չհաջողվեց ուղարկել ապրանքը։');
    } finally { button.disabled = false; }
  });
}

function switchTab(name) {
  $$('[data-tab]').forEach((button) => button.classList.toggle('active', button.dataset.tab === name));
  $$('.view').forEach((view) => { view.hidden = view.id !== `view-${name}`; });
  const view = $(`#view-${name}`);
  view.classList.remove('entering'); void view.offsetWidth; view.classList.add('entering');
  window.scrollTo({top: 0, behavior: 'smooth'});
  if (name === 'history' && !ordersLoaded) loadOrders();
  if (name === 'profile' && token && !profile) loadProfile();
  haptic();
}

$('#topup').addEventListener('click', openTopup);
$('#sheet-close').addEventListener('click', closeSheet);
$('#sheet-backdrop').addEventListener('click', (event) => { if (event.target === $('#sheet-backdrop')) closeSheet(); });
$('#sheet-continue').addEventListener('click', () => sheetAction?.());
tg?.BackButton?.onClick?.(closeSheet);

$$('[data-tab]').forEach((button) => button.addEventListener('click', () => switchTab(button.dataset.tab)));
$('#copy-id').addEventListener('click', async () => {
  if (!profile?.user_id) return;
  try { await navigator.clipboard.writeText(String(profile.user_id)); notify('Telegram ID-ն պատճենված է', true); }
  catch { notify(`Ձեր Telegram ID-ն՝ ${profile.user_id}`); }
  haptic();
});

(async function init() {
  if (user) {
    $('#greeting').textContent = `Բարև, ${user.first_name}`;
    setAvatar($('#profile-avatar'), user.first_name, user.photo_url);
  }
  await loadProducts();
  if (await authorize()) {
    $('#status').classList.add('ready');
    await loadProfile();
  } else {
    $('#status').classList.add('off');
    $('#status b').textContent = 'Հյուր';
    $('#balance').textContent = 'Բացեք Telegram-ում';
  }
})();
