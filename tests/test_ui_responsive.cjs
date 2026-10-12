// Verifie les vraies dimensions de l'interface avec Microsoft Edge en mode headless.
// Ne lance aucun téléchargement réseau, n'affecte aucun fichier utilisateur.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

const edgeCandidates = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft/Edge/Application/msedge.exe'),
  process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Microsoft/Edge/Application/msedge.exe')
].filter(Boolean);
const executablePath = edgeCandidates.find(p => fs.existsSync(p));
assert.ok(executablePath, 'Microsoft Edge x64 introuvable sur le runner Windows');

(async () => {
  const browser = await chromium.launch({ executablePath, headless: true,
    args: ['--no-sandbox', '--disable-gpu'] });
  try {
    const page = await browser.newPage({viewport:{width:1050,height:800}});
    await page.goto('file:///' + path.resolve('tests/ui-test.html').replaceAll('\\','/'));
    await page.evaluate(() => {
      const data = {title:'Vidéo de démonstration',duration:'03:20',thumbnail:'',url:'https://example.com/video',
        mode:'Vidéo', formats:['Meilleure qualité (Auto)','1080p'], selectedQuality:'1080p',
        selectedQualityLabel:'1080p', isError:false, is_playlist:false, is_channel:false};
      queue = [ {...data}, {...data,title:'Un deuxième média'} ];
      renderCards(); updateView();
    });

    await page.setViewportSize({width:1920,height:1080});
    const large = await page.evaluate(() => {
      const app=document.querySelector('.app-container');
      const list=document.getElementById('cardList');
      const cards=[...document.querySelectorAll('.media-card')].map(el=>el.getBoundingClientRect());
      return {width:app.getBoundingClientRect().width,
        display:getComputedStyle(list).display,
        firstX:cards[0].x,secondX:cards[1].x,
        hasHorizontalOverflow:document.documentElement.scrollWidth>innerWidth};
    });
    assert.ok(large.width>=1500, "La page ne s'étend pas en plein écran : " + large.width);
    assert.equal(large.display,'grid','Les cartes ne passent pas en grille en plein écran');
    assert.ok(large.secondX>large.firstX+200,'Les cartes ne sont pas disposées côte à côte');
    assert.equal(large.hasHorizontalOverflow,false,'Débordement horizontal en plein écran');

    await page.evaluate(() => showSettingsView());
    const settings = await page.evaluate(() => ({
      width:document.getElementById('setSectionTelech').getBoundingClientRect().width,
      display:getComputedStyle(document.getElementById('setSectionTelech')).display
    }));
    assert.ok(settings.width>1050,'Les paramètres restent trop étroits en plein écran');
    assert.equal(settings.display,'grid','Les paramètres ne passent pas en deux colonnes');

    await page.evaluate(() => openView('viewMain'));
    await page.setViewportSize({width:1050,height:800});
    const normal = await page.evaluate(() => ({
      list:getComputedStyle(document.getElementById('cardList')).display,
      mainWidth:document.querySelector('.app-container').getBoundingClientRect().width,
      overflow:document.documentElement.scrollWidth>innerWidth,
      footer:getComputedStyle(document.querySelector('.actions-bar')).flexWrap
    }));
    assert.equal(normal.list,'flex');
    assert.ok(normal.mainWidth>950, 'La fenêtre normale reste inutilement étroite');
    assert.equal(normal.footer,'wrap','Le pied de page ne se réorganise pas');
    assert.equal(normal.overflow,false,'Débordement horizontal en fenêtre normale');

    // Finitions : centrage et bordures reels, verifies dans Edge a 1334 px.
    await page.setViewportSize({width:1334,height:950});
    const balance = await page.evaluate(() => {
      queue = [];
      updateView();
      const mid = node => {
        const box = node.getBoundingClientRect();
        return box.x + box.width / 2;
      };
      return {
        main: mid(document.querySelector('.empty-title')),
        controls: mid(document.querySelector('.actions-center')),
        viewport: innerWidth / 2,
        headerLine: getComputedStyle(document.querySelector('.header')).borderBottomColor,
        footerLine: getComputedStyle(document.querySelector('.footer')).borderTopColor,
        statusLine: getComputedStyle(document.querySelector('.status-bar')).borderBottomColor,
        verticalDivider: getComputedStyle(document.querySelector('.bottom-v-separator')).backgroundColor,
        overflow: document.documentElement.scrollWidth > innerWidth
      };
    });
    assert.ok(Math.abs(balance.main-balance.viewport)<2, 'L etat vide n est pas centre');
    assert.ok(Math.abs(balance.controls-balance.viewport)<2, 'La barre de formats n est pas centree');
    assert.equal(balance.headerLine,'rgb(203, 213, 225)','Separateur haut light pas assez visible');
    assert.equal(balance.footerLine,'rgb(203, 213, 225)','Separateur bas light incorrect');
    assert.equal(balance.statusLine,'rgb(203, 213, 225)','Separateur de statut manquant');
    assert.equal(balance.verticalDivider,'rgb(203, 213, 225)','Trait entre formats incorrect');
    assert.equal(balance.overflow,false,'Debordement horizontal dans l interface normale');
    for (const [theme,color] of [['theme-dark','rgb(59, 59, 59)'],['theme-dark_pure','rgb(45, 45, 45)']]) {
      await page.evaluate(t => { document.body.className = t; }, theme);
      const themeLines = await page.evaluate(() => ({
        head:getComputedStyle(document.querySelector('.header')).borderBottomColor,
        footer:getComputedStyle(document.querySelector('.footer')).borderTopColor,
        divider:getComputedStyle(document.querySelector('.bottom-v-separator')).backgroundColor
      }));
      assert.equal(themeLines.head,color,'Trait de separation haut incorrect : '+theme);
      assert.equal(themeLines.footer,color,'Trait de separation bas incorrect : '+theme);
      assert.equal(themeLines.divider,color,'Trait de separation des boutons incorrect : '+theme);
    }
    console.log('OK centrage et traits de separation verifies dans Edge (1334 px, 3 themes)');

    console.log('OK interface responsive Edge : plein écran 1920, fenêtre 1050, 2 colonnes de cartes et paramètres');
    await page.close();
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err.stack||err); process.exitCode=1; });
