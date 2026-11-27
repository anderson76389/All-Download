// Verifie les vraies dimensions de l'interface avec Microsoft Edge en mode headless.
// Ne lance aucun téléchargement réseau, n'affecte aucun fichier utilisateur.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright-core');

const edgeCandidates = [
  process.env.ALL_DOWNLOAD_TEST_BROWSER,
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft/Edge/Application/msedge.exe'),
  process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Microsoft/Edge/Application/msedge.exe')
].filter(Boolean);
const executablePath = edgeCandidates.find(p => fs.existsSync(p));
assert.ok(executablePath, 'Navigateur Chromium introuvable pour le test de rendu');

(async () => {
  const browser = await chromium.launch({ executablePath, headless: true,
    args: ['--no-sandbox', '--disable-gpu'] });
  try {
    const page = await browser.newPage({viewport:{width:1050,height:800}});
    await page.goto(pathToFileURL(path.resolve('tests/ui-test.html')).href);
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

    // Le trait sous l'URL doit rejoindre les deux bords, sans élargir
    // le champ ni déborder horizontalement, y compris après 1800px.
    for (const width of [1050, 1652, 1920]) {
      await page.setViewportSize({width,height:900});
      const line = await page.evaluate(() => {
        const header = document.querySelector('#viewMain .header');
        const rect = header.getBoundingClientRect();
        const pseudo = getComputedStyle(header, '::after');
        const pseudoWidth = parseFloat(pseudo.width);
        return {
          left: rect.left + rect.width / 2 - pseudoWidth / 2,
          right: rect.left + rect.width / 2 + pseudoWidth / 2,
          color: pseudo.backgroundColor,
          lineWidth: pseudoWidth,
          viewport: innerWidth,
          overflow: document.documentElement.scrollWidth > innerWidth
        };
      });
      assert.ok(Math.abs(line.left) < 2 && Math.abs(line.right-width) < 2,
        'Trait sous URL non étendu bord à bord à '+width+': '+JSON.stringify(line));
      assert.equal(line.overflow,false,'Trait URL crée un débordement horizontal');
    }
    await page.setViewportSize({width:1920,height:1080});
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
      footer:getComputedStyle(document.querySelector('.actions-bar')).display
    }));
    assert.equal(normal.list,'flex');
    assert.ok(normal.mainWidth>950, 'La fenêtre normale reste inutilement étroite');
    assert.equal(normal.footer,'grid','Les trois groupes doivent rester alignés, sans retour à la ligne');
    assert.equal(normal.overflow,false,'Débordement horizontal en fenêtre normale');

    // Les trois zones du pied doivent être sur la même ligne en fenêtre
    // normale et grande : l'ancien flex-wrap en décalait le groupe central.
    for (const width of [920, 1050, 1334, 1652, 1920]) {
      await page.setViewportSize({width,height:900});
      const geometry = await page.evaluate(() => {
        const rect = selector => {
          const {left,right,top,bottom,width,height} = document.querySelector(selector).getBoundingClientRect();
          return {left,right,top,bottom,width,height,midX:(left+right)/2,midY:(top+bottom)/2};
        };
        return {left:rect('.actions-left'),center:rect('.center-cluster'),
          right:rect('.actions-right'),footer:rect('.actions-bar'),viewport:innerWidth,
          overflow:document.documentElement.scrollWidth>innerWidth};
      });
      assert.equal(geometry.overflow,false,'Débordement horizontal du pied à '+width);
      assert.ok(Math.abs(geometry.center.midX - width/2) < 3,
        'Format/qualité non centrés à '+width+': '+geometry.center.midX);
      assert.ok(Math.abs(geometry.left.midY-geometry.center.midY) < 3 &&
        Math.abs(geometry.center.midY-geometry.right.midY) < 3,
        'Icônes et Télécharger non alignés verticalement à '+width);
      assert.ok(geometry.left.right < geometry.center.left &&
        geometry.center.right < geometry.right.left,
        'Chevauchement des groupes du pied à '+width);
    }

    await page.setViewportSize({width:1652,height:900});
    // WebView2/Edge peut terminer l'ancienne frame après setViewportSize.
    // Attendre le style du VRAI plein écran avant de mesurer les dimensions.
    await page.waitForFunction(() => {
      const download = document.querySelector('#viewMain .actions-right .btn-download-all');
      const tool = document.querySelector('#viewMain .tool-cluster-btn');
      return window.matchMedia('(min-width:1500px) and (min-height:760px)').matches &&
        download && tool && download.getBoundingClientRect().height >= 52 &&
        tool.getBoundingClientRect().height >= 46;
    }, null, {timeout:10000});
    await page.evaluate(() => new Promise(resolve =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const largeMain = await page.evaluate(() => ({
      addHeight:document.querySelector('#viewMain .btn-add').getBoundingClientRect().height,
      urlHeight:document.querySelector('#viewMain .input-wrapper').getBoundingClientRect().height,
      downloadHeight:document.querySelector('#viewMain .actions-right .btn-download-all').getBoundingClientRect().height,
      toolsHeight:document.querySelector('#viewMain .tool-cluster-btn').getBoundingClientRect().height
    }));
    assert.ok(largeMain.addHeight>=54,'Bouton Ajouter trop petit en plein écran');
    assert.ok(largeMain.urlHeight>=54,'Champ URL trop petit en plein écran');
    console.log('DIAGNOSTIC dimensions commandes 1652×900:', JSON.stringify(largeMain));
    assert.ok(largeMain.downloadHeight>=52 && largeMain.toolsHeight>=46,
      'Commandes du bas trop petites en plein écran: '+JSON.stringify(largeMain));
    await page.evaluate(() => showSettingsView());
    const centeredSettings = await page.evaluate(() => {
      const box = el => {const {left,right,top,bottom,height}=el.getBoundingClientRect();
        return {left,right,top,bottom,height,midX:(left+right)/2};};
      const section=document.getElementById('setSectionTelech');
      return {folder:box(section.children[0]),sortie:box(section.children[1]),
        sponsor:box(section.children[3]),section:box(section),
        grid:getComputedStyle(section).display,
        headerNav:box(document.querySelector('.settings-nav')),
        themeButton:box(document.querySelector('.settings-header .btn-download-all')),
        settingInput:box(document.getElementById('setDownloadFolder')),
        labelSize:parseFloat(getComputedStyle(document.querySelector('.setting-label')).fontSize),
        tabSize:parseFloat(getComputedStyle(document.querySelector('.tab-btn')).fontSize),
        bodyWidth:innerWidth,
        overflow:document.documentElement.scrollWidth>innerWidth};
    });
    assert.equal(centeredSettings.grid,'grid','Les paramètres ne sont pas sur deux colonnes');
    assert.ok(Math.abs(centeredSettings.headerNav.midX - 826)<3,'Onglets des paramètres décentrés');
    assert.ok(Math.abs(centeredSettings.section.midX - 826)<3,'Grille des paramètres décentrée');
    assert.ok(Math.abs(centeredSettings.folder.top-centeredSettings.sortie.top)<3,
      'Dossier et sortie ne démarrent pas au même niveau');
    assert.ok(centeredSettings.sponsor.top >= centeredSettings.folder.bottom &&
      centeredSettings.sponsor.top < centeredSettings.sortie.bottom,
      'SponsorBlock doit suivre le dossier sans grand vide à gauche');
    assert.ok(centeredSettings.settingInput.height>=48,'Champ des paramètres trop petit');
    assert.ok(centeredSettings.labelSize>=16 && centeredSettings.tabSize>=16,
      'Textes et onglets des paramètres trop petits en plein écran');
    assert.ok(centeredSettings.themeButton.height>=48,'Bouton Enregistrer trop petit');
    assert.equal(centeredSettings.overflow,false,'Débordement horizontal dans les paramètres');
    await page.evaluate(() => openView('viewMain'));
    console.log('OK tailles et alignements à 920, 1050, 1334, 1652 et 1920 pixels');

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
        overflow: document.documentElement.scrollWidth > innerWidth
      };
    });
    assert.ok(Math.abs(balance.main-balance.viewport)<2, 'L etat vide n est pas centre');
    assert.ok(Math.abs(balance.controls-balance.viewport)<2, 'La barre de formats n est pas centree');
    assert.equal(balance.headerLine,'rgb(203, 213, 225)','Separateur haut light pas assez visible');
    assert.equal(balance.overflow,false,'Debordement horizontal dans l interface normale');

    // Audit des 3 themes en situation reelle, y compris toutes les lignes fines.
    // Les elements restent dans le DOM quel que soit l'ecran affiché.
    const themes = [
      {id:'light',name:'theme-light',body:'rgb(248, 250, 252)',glass:'#ffffffd9',
       divider:'rgb(203, 213, 225)',accent:'rgb(124, 58, 237)',card:'rgb(255, 255, 255)'},
      {id:'dark',name:'theme-dark',body:'rgb(20, 20, 20)',glass:'#343434d6',
       divider:'rgb(59, 59, 59)',accent:'rgb(124, 58, 237)',card:'rgb(33, 33, 33)'},
      {id:'dark_pure',name:'theme-dark_pure',body:'rgb(0, 0, 0)',glass:'#252525d6',
       divider:'rgb(45, 45, 45)',accent:'rgb(124, 58, 237)',card:'rgb(0, 0, 0)'}
    ];
    // La carte de configuration avancee est creee dynamiquement ;
    // le controle visuel garde un echantillon neutre dans le DOM.
    await page.evaluate(() => {
      if (!document.querySelector('.secret-box')) {
        const probe = document.createElement('div');
        probe.className = 'secret-box';
        probe.style.display = 'none';
        document.body.appendChild(probe);
      }
    });
    for (const theme of themes) {
      await page.evaluate(id => applyTheme(id), theme.id);
      const colors = await page.evaluate(() => {
        const rule = (selector,property) => getComputedStyle(document.querySelector(selector)).getPropertyValue(property).trim();
        return {
          theme:document.body.className,
          body:rule('body','background-color'),
          glassColor:rule('body','--glass-top-alpha'),
          blur:getComputedStyle(document.querySelector('.footer')).backdropFilter,
          status:rule('.status-bar','background-color'),
          card:rule('.media-card','background-color'),
          form:rule('.setting-input','background-color'),
          controls:rule('.center-cluster','background-color'),
          tools:rule('.tools-cluster','background-color'),
          popup:rule('.popover-menu','background-color'),
          contextMenu:rule('.context-menu','background-color'),
          log:rule('.terminal-box','background-color'),
          secret:rule('.secret-box','background-color'),
          headLine:rule('.header','border-bottom-color'),
          cardDivider:rule('.v-separator','background-color'),
          settingsLine:rule('.settings-header','border-bottom-color'),
          authLine:rule('.auth-header','border-bottom-color'),
          trashLine:rule('.trash-arrow','border-left-color'),
          headerWidth:rule('.header','border-bottom-width'),
          footerWidth:rule('.footer','border-top-width'),
          statusWidth:rule('.status-bar','border-bottom-width'),
          mainButton:rule('.btn-add','background-color'),
          secondaryButton:rule('.btn-logs-card','background-color'),
          secondaryColor:rule('.btn-logs-card','color')
        };
      });
      assert.equal(colors.theme,theme.name,'Classe theme non synchronisee');
      assert.equal(colors.body,theme.body,'Fond de la fenetre incorrect : '+theme.id);
      assert.equal(colors.glassColor,theme.glass,'Teinte du verre : '+theme.id);
      assert.match(colors.blur, /blur\(28px\)/);
      for (const k of ['status','controls','tools'])
        assert.equal(colors[k],'rgba(0, 0, 0, 0)','Surface imbriquée opaque : '+k);
      assert.equal(colors.card,theme.card,'Cartes de medias non harmonisees : '+theme.id);
      for (const k of ['headLine','cardDivider','settingsLine','authLine','trashLine'])
        assert.equal(colors[k],theme.divider,'Trait gris incoherent ('+k+') : '+theme.id);
      assert.equal(colors.headerWidth,'1px');
      assert.equal(colors.footerWidth,'0px');
      assert.equal(colors.statusWidth,'0px');
      assert.equal(colors.mainButton,theme.accent,'Accent du bouton Ajouter incorrect : '+theme.id);
      // Même violet dans les trois thèmes, mais fond sombre/OLED inchangé.
      const accents = await page.evaluate(() => {
        const bg = sel => getComputedStyle(document.querySelector(sel)).backgroundColor;
        const color = sel => getComputedStyle(document.querySelector(sel)).color;
        const border = sel => getComputedStyle(document.querySelector(sel)).borderColor;
        const selected = document.querySelector('.mode-pill-btn.active');
        const switchInput = document.getElementById('setSponsorEnable');
        const slider = switchInput.nextElementSibling;
        return {
          add:bg('.btn-add'), download:bg('.btn-download-all'),
          progress:bg('.progress-fill'), switch:bg('.switch input:checked + .slider'),
          center:border('.center-cluster'), activeText:color('.tab-btn.active'),
          statusText:color('.status-bar'), slider:bg('.slider'),
          statusBg:bg('.status-bar')
        };
      });
      assert.equal(accents.add,'rgb(124, 58, 237)','Ajouter doit être violet : '+theme.id);
      assert.equal(accents.download,'rgb(124, 58, 237)','Télécharger doit être violet : '+theme.id);
      assert.equal(accents.progress,'rgb(124, 58, 237)','Barre de progression non violette : '+theme.id);
      assert.equal(accents.center,'rgba(0, 0, 0, 0)','Contour superposé : '+theme.id);
      if(theme.id !== 'light') {
        assert.equal(accents.activeText,'rgb(196, 181, 253)','Onglet actif non lisible : '+theme.id);
        assert.notEqual(accents.statusBg,'rgb(0, 230, 118)','Fond vert interdit : '+theme.id);
      }

      assert.notEqual(colors.secondaryButton,'rgb(56, 49, 51)',
        'Bouton secondaire conserve un fond gris-rose hors theme : '+theme.id);
      if (theme.id==='dark_pure') {
        for (const k of ['form','popup','contextMenu','log','secret'])
          assert.equal(colors[k],'rgb(0, 0, 0)','OLED pas completement noir ('+k+')');
        assert.equal(colors.secondaryButton,'rgb(0, 0, 0)','Bouton secondaire non OLED');
      }
      // Le theme doit rester stable dans les paramètres et apres annulation.
      await page.evaluate(() => {
        openView('viewSettings');
        switchSettingsTab('appli');
        previewTheme('light');
        cancelSettings();
      });
      const afterCancel = await page.evaluate(() => document.body.className);
      assert.equal(afterCancel,theme.name,'Annuler les paramètres ne restaure pas le thème : '+theme.id);
    }
    // Alternances répétées : aucun style du theme precedent ne doit subsister.
    for (const id of ['dark_pure','light','dark','dark_pure','light','dark_pure']) {
      await page.evaluate(value => applyTheme(value),id);
      const actual = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      assert.equal(actual,themes.find(x=>x.id===id).body,'Changement de thème glitché : '+id);
    }
    console.log('OK audit des 3 thèmes : OLED #000, palettes du verre, menus, boutons et transitions');

    await page.evaluate(() => {
      queue = Array.from({length: 16}, (_, i) => ({
        title:'Média ' + i, duration:'03:20', thumbnail:'', url:'https://example.com/video/' + i,
        mode:'Vidéo', formats:['1080p'], selectedQuality:'1080p', selectedQualityLabel:'1080p'
      }));
      renderCards();
      updateView();
    });

    for (const width of [320, 375, 680, 920, 1050, 1920]) {
      await page.setViewportSize({width, height:620});
      await page.waitForFunction(() => {
        const dock = document.querySelector('.footer');
        return parseFloat(getComputedStyle(dock).getPropertyValue('--dock-space')) === dock.offsetHeight + 8;
      });
      const layout = await page.evaluate(() => {
        const dock = document.querySelector('.footer').getBoundingClientRect();
        const scroll = document.querySelector('.main-content');
        scroll.scrollTop = scroll.scrollHeight;
        return {
          dockTop:dock.top, viewportBottom:scroll.getBoundingClientRect().bottom,
          lastCardBottom:document.querySelector('.media-card:last-child').getBoundingClientRect().bottom,
          controlsFit:[...document.querySelectorAll('.footer .dock-trigger, .footer .tool-cluster-btn, .footer .btn-download-all')].every(button => {
            const rect = button.getBoundingClientRect();
            return rect.left >= dock.left && rect.right <= dock.right;
          })
        };
      });
      assert.ok(layout.dockTop < layout.viewportBottom, 'Le contenu doit passer derrière le verre');
      assert.ok(layout.lastCardBottom <= layout.dockTop, 'Dernier média masqué à '+width);
      assert.ok(layout.controlsFit, 'Commande hors de la barre à '+width);
    }

    await page.setViewportSize({width:375, height:640});
    const format = page.getByRole('button', {name:'Format', exact:true});
    await format.focus();
    await page.keyboard.press('Enter');
    assert.equal(await format.getAttribute('aria-expanded'), 'true');
    await page.keyboard.press('Tab');
    assert.match(await page.evaluate(() => document.activeElement.textContent), /Vidéo/);
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    assert.equal(await format.getAttribute('aria-expanded'), 'false');
    assert.equal(await page.evaluate(() => currentGlobalMode), 'Audio');
    const quality = page.getByRole('button', {name:'Qualité', exact:true});
    await quality.click();
    await page.locator('#globalQualPopover').getByRole('button', {name:'MP3 (320 kbps)'}).click();
    assert.equal(await page.evaluate(() => currentGlobalQuality), 'MP3_320');
    const trash = page.getByRole('button', {name:'Options de la file'});
    await trash.click();
    assert.equal(await trash.getAttribute('aria-expanded'), 'true');
    await page.keyboard.press('Escape');
    assert.equal(await trash.getAttribute('aria-expanded'), 'false');
    assert.ok(await trash.evaluate(button => document.activeElement === button));

    await page.setViewportSize({width:1050, height:620});
    await page.evaluate(() => {
      queue = [];
      updateView();
    });
    const sample = await page.locator('.footer').evaluate(dock => {
      const {x, y} = dock.getBoundingClientRect();
      return {x: Math.round(x + 25), y: Math.round(y + 12), width: 12, height: 12};
    });
    const paintBehindDock = color => page.locator('.main-content').evaluate((scroll, background) => {
      scroll.style.background = background;
    }, color);
    await paintBehindDock('#ff0000');
    const redBackdrop = await page.screenshot({clip:sample});
    await paintBehindDock('#0000ff');
    const blueBackdrop = await page.screenshot({clip:sample});
    assert.notDeepEqual(redBackdrop, blueBackdrop, 'Le contenu derrière le verre doit modifier son rendu');

    await page.emulateMedia({forcedColors:'active'});
    assert.equal(await page.locator('.footer').evaluate(dock => getComputedStyle(dock).backdropFilter), 'none');
    console.log('OK dock Liquid Glass : trois thèmes, 320 à 1920 px, file défilante, menus, clavier, rendu du fond et contraste forcé');
    await page.close();
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err.stack||err); process.exitCode=1; });
