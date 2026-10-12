// Verification de l'interface reelle (HTML/JS embarques dans yt_app.py).
// Les API Python sont simulees : aucun appel Internet ni media telecharge.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');

const html = fs.readFileSync('tests/ui-test.html', 'utf8');
const defaults = {
  sortie_type: 'video', video_format: 'MKV', post_process_video: 'Aucun',
  video_origin_stream: false, video_embed_thumb: true, video_write_thumb: true,
  video_add_metadata: true, audio_format: 'M4A', post_process_audio: 'Aucun',
  audio_embed_thumb: true, audio_write_thumb: true, audio_add_metadata: true,
  sponsor_enable: false, sponsor_remove: 'sponsor', sponsor_mark: 'none',
  sponsor_api: 'https://sponsor.ajay.app', exact_cut: false, theme: 'dark',
  extra_selector: 'none', notify: 'never', proxy_toggle: false, proxy_url: '',
  impersonation: 'none', extractor_args: '',
};

const events = [];
const jsErrors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => jsErrors.push(e.message));
const media = {
  title: 'Vidéo exemple', duration: '03:01', thumbnail: '',
  url: 'https://www.youtube.com/watch?v=test42', mode: 'Vidéo',
  formats: ['Meilleure qualité (Auto)', '1080p', '720p'],
  selectedQuality: 'Meilleure qualité (Auto)', isError: false,
  is_playlist: false, is_channel: false
};
const playlist = {
  ...media, title: 'Ma playlist', url: 'https://www.youtube.com/playlist?list=123',
  is_playlist: true, playlist_title: 'Ma playlist', item_count: 12,
  start_idx: 1, end_idx: 12
};
const backend = {
  get_app_settings: () => ({ ...defaults }),
  save_app_settings: settings => { events.push(['save_app_settings', settings]); return true; },
  get_auth_config: () => ({cookie_file:'',cookie_browser:'none'}),
  save_auth_config: (file, browser) => { events.push(['save_auth_config', file, browser]); return true; },
  select_cookie_file: () => 'C:\\test\\cookies.txt',
  get_clipboard_text: () => 'https://example.com/copied',
  open_folder: () => {events.push(['open_folder']);return true;},
  open_external: url => {events.push(['open_external',url]);return true;},
  cancel_downloads: () => {events.push(['cancel_downloads']);return true;},
  pause_downloads: () => {events.push(['pause_downloads']);return true;},
  resume_downloads: () => {events.push(['resume_downloads']);return true;},
  start_downloads: items => {events.push(['start_downloads',JSON.parse(JSON.stringify(items))]);return true;},
  extract_info: url => {
    events.push(['extract_info',url]);
    if(url.includes('denied')) return {success:false,error:'Accès refusé'};
    if(url.includes('/playlist?')) return {success:true,data:{...playlist,url}};
    return {success:true,data:{...media,url}};
  }
};

const dom = new JSDOM(html, {
  url:'https://all-download.local/',
  runScripts:'dangerously', pretendToBeVisual:true, virtualConsole:vc,
  beforeParse(win) {
    win.pywebview = {api: Object.fromEntries(
      Object.entries(backend).map(([k,v]) => [k, (...args) => Promise.resolve(v(...args))])
    )};
    Object.defineProperty(win.navigator,'clipboard',{
      configurable:true,
      value:{
        readText:() => Promise.resolve('https://example.com/copied'),
        writeText:txt => {events.push(['copy',txt]);return Promise.resolve();}
      }
    });
  }
});
const win=dom.window, doc=win.document;
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const action=selector=>{
  const el=doc.querySelector(selector);
  assert.ok(el, 'Element absent: '+selector);
  el.click();
  return el;
};
function verifyInlineHandlers() {
  let count=0;
  for (const el of doc.querySelectorAll('[onclick],[onmousedown],[onchange],[onkeydown]')) {
    for(const attr of ['onclick','onmousedown','onchange','onkeydown']) {
      if(el.hasAttribute(attr)) {
        // Compile réellement la syntaxe de chaque gestionnaire de bouton.
        new win.Function('event',el.getAttribute(attr));
        count++;
      }
    }
  }
  return count;
}
function validate() {
  assert.equal(jsErrors.length,0,'Erreur JavaScript : '+jsErrors.join('; '));
  assert.ok(doc.getElementById('appBody'),'Application absente');
  assert.ok(verifyInlineHandlers()>25,'Boutons introuvables');
}
async function run() {
  validate();

  // Paramètres : le bouton doit charger les valeurs enregistrées.
  action('.btn-settings');
  await flush();
  assert.equal(doc.getElementById('viewSettings').style.display,'flex');
  assert.equal(doc.getElementById('setVideoFormat').value,'MKV');
  assert.equal(doc.getElementById('setAudioFormat').value,'M4A');
  action('#tabBtnAppli');
  assert.equal(doc.getElementById('setSectionAppli').style.display,'flex');
  action('#tabBtnReseau');
  assert.equal(doc.getElementById('setSectionReseau').style.display,'flex');
  action('#tabBtnTelech');
  action('#btnSortieAudio');
  assert.equal(doc.getElementById('sortieAudioFields').style.display,'block');
  doc.getElementById('setTheme').value='dark_pure';
  action('[onclick="saveSettings()"]');
  await flush();
  const saved=events.findLast(x=>x[0]==='save_app_settings');
  assert.equal(saved[1].sortie_type,'audio');
  assert.equal(saved[1].theme,'dark_pure');
  assert.equal(doc.getElementById('viewMain').style.display,'flex');

  // Menus auth et cookies, sélection d'un navigateur, sauvegarde.
  action('[title="Authentification / Cookies"]');
  await flush();
  action('[onclick="chooseCookieFile()"]');
  await flush();
  assert.equal(doc.getElementById('cookieFile').value,'C:\\test\\cookies.txt');
  action('[onclick="clearCookieFile()"]');
  assert.equal(doc.getElementById('cookieFile').value,'');
  const firefox = [...doc.querySelectorAll('[onclick]')].find(
    e => e.getAttribute('onclick').includes("selectBrowser('firefox'")
  );
  assert.ok(firefox, 'Option Firefox du menu Cookies introuvable');
  firefox.click();
  action('[onclick="saveAuth()"]');
  await flush();
  assert.deepEqual(events.findLast(x=>x[0]==='save_auth_config'),['save_auth_config','','firefox']);

  // Outils d'URL : presse-papiers, effacer.
  const input=doc.getElementById('urlInput');
  doc.querySelector('[onmousedown="pasteFromClipboard(event)"]')
    .dispatchEvent(new win.MouseEvent('mousedown',{bubbles:true}));
  await flush();
  assert.equal(input.value,'https://example.com/copied');
  doc.querySelector('[onmousedown="copyUrlText(event)"]')
    .dispatchEvent(new win.MouseEvent('mousedown',{bubbles:true}));
  await flush();
  assert.ok(events.some(x=>x[0]==='copy'&&x[1]===input.value));
  doc.querySelector('[onmousedown="clearUrlInput(event)"]')
    .dispatchEvent(new win.MouseEvent('mousedown',{bubbles:true}));
  assert.equal(input.value,'');

  // Ajouter une vidéo, choisir Audio/GIF, utiliser les boutons par carte.
  input.value='https://www.youtube.com/watch?v=test42';
  action('.btn-add[onclick="addVideo()"]');
  await flush();
  assert.equal(win.eval('queue.length'),1);
  assert.equal(doc.querySelectorAll('.media-card').length,1);
  win.setCardMode(0,'Audio');
  assert.equal(win.eval('queue[0].selectedQuality'),'FLAC');
  assert.match(doc.querySelector('.media-card').textContent,/AUDIOS/);
  win.setCardQuality(0,'M4A','M4A (Format natif)');
  assert.equal(win.eval('queue[0].selectedQuality'),'M4A');
  win.setCardMode(0,'GIF');
  assert.match(doc.querySelector('.media-card').textContent,/GIFS/);
  action('.media-card [title="Télécharger"]');
  await flush();
  assert.equal(events.findLast(x=>x[0]==='start_downloads')[1][0].mode,'GIF');
  action('.media-card [title="Ouvrir dans le navigateur"]');
  assert.equal(events.findLast(x=>x[0]==='open_external')[1],media.url);
  action('.media-card [title="Informations"]');
  assert.equal(doc.getElementById('viewLogs').style.display,'flex');
  action('[title="Ouvrir le dossier"]');

  // Erreur d'extraction : boutons Cookies, Logs et Réessayer.
  win.clearQueue();
  input.value='https://example.com/denied';
  win.addVideo();
  await flush();
  assert.match(doc.getElementById('statusBar').innerText,/1 élément/);
  assert.ok(doc.getElementById('errHeader'), 'En-tête des erreurs manquant');
  action('.media-card [onclick="showLogsView()"]');
  assert.match(doc.getElementById('errHeader').innerText,/1/);
  assert.match(doc.getElementById('errList').textContent,/Accès refusé/);

  // Playlist précédée d'une erreur : vérifier les vrais index du DOM.
  input.value=playlist.url;
  win.addVideo();
  await flush();
  assert.equal(win.eval('queue.length'),2);
  const first=doc.getElementById('p_start_1'),last=doc.getElementById('p_end_1');
  assert.ok(first&&last,'Plage de playlist introuvable');
  first.value='3'; last.value='7';
  action('[onclick="startDownloads()"]');
  await flush();
  const selected=events.findLast(x=>x[0]==='start_downloads')[1];
  assert.equal(selected.length,1,'Une entrée en erreur ne doit pas être téléchargée');
  assert.equal(selected[0].start_idx,3);
  assert.equal(selected[0].end_idx,7);

  // Queue, erreurs, mode global, pause/reprise/annulation.
  win.cancelDownloadsSafe();
  win.pauseDownloadsSafe();
  win.resumeDownloadsSafe();
  assert.ok(events.some(x=>x[0]==='cancel_downloads'));
  assert.ok(events.some(x=>x[0]==='pause_downloads'));
  assert.ok(events.some(x=>x[0]==='resume_downloads'));
  win.selectGlobalMode('Audio');
  assert.equal(win.eval('queue[1].mode'),'Audio');
  win.clearFailed();
  assert.equal(win.eval('queue.length'),1);
  win.clearQueue();
  assert.equal(win.eval('queue.length'),0);
  assert.equal(doc.getElementById('emptyView').style.display,'flex');
  validate();
  console.log('OK : boutons, formulaires, thèmes, cookies, file d’attente, qualité, playlist, navigation, API Python simulée');
  console.log('Gestionnaires HTML vérifiés : '+verifyInlineHandlers());
}
run().then(()=>{dom.window.close()}).catch(e=>{console.error(e.stack||e);dom.window.close();process.exitCode=1;});
