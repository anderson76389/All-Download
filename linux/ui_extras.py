"""Linux-only settings controls injected into the unchanged Windows HTML."""
from __future__ import annotations

LINUX_SETTINGS_SCRIPT = r"""
<script>
(function () {
  function addLinuxSettings() {
    const parent = document.getElementById('setSectionAppli');
    if (!parent || document.getElementById('linuxExtraSettings')) return;
    const section = document.createElement('div');
    section.id = 'linuxExtraSettings';
    section.className = 'setting-section';
    section.innerHTML = [
      '<div class="setting-sec-title">Linux</div>',
      '<div class="setting-sec-desc">Version portable : contrôle manuel des mises à jour et raccourci facultatif, sans installation système.</div>',
      '<div class="setting-field" style="display:flex;gap:9px;flex-wrap:wrap;align-items:center;">',
      '<button type="button" class="btn-logs-card" id="linuxCheckUpdates">Vérifier les mises à jour Linux</button>',
      '<button type="button" class="btn-logs-card" id="linuxOpenUpdate" hidden>Voir la nouvelle version</button>',
      '</div>',
      '<div class="setting-subtext" id="linuxUpdateStatus" role="status" aria-live="polite">Aucune connexion automatique au démarrage.</div>',
      '<div class="setting-field" style="display:flex;gap:9px;flex-wrap:wrap;align-items:center;">',
      '<button type="button" class="btn-logs-card" id="linuxInstallShortcut">Ajouter au menu des applications</button>',
      '<button type="button" class="btn-logs-card" id="linuxRemoveShortcut">Retirer le raccourci</button>',
      '</div>',
      '<div class="setting-subtext" id="linuxShortcutStatus" role="status" aria-live="polite">Les médias, réglages et outils restent dans le dossier All-Download. Le raccourci est facultatif.</div>'
    ].join('');
    parent.appendChild(section);
    const bridge = () => window.pywebview && window.pywebview.api;
    const button = document.getElementById('linuxCheckUpdates');
    const open = document.getElementById('linuxOpenUpdate');
    const status = document.getElementById('linuxUpdateStatus');
    button.addEventListener('click', async () => {
      button.disabled = true;
      open.hidden = true;
      status.textContent = 'Vérification de la Release Linux…';
      try {
        if (!bridge() || !bridge().check_linux_updates) throw Error('Moteur Linux indisponible.');
        const result = await bridge().check_linux_updates();
        if (!result || !result.success) {
          status.textContent = (result && result.error) || 'Vérification impossible.';
        } else if (result.available) {
          status.textContent = 'Version ' + result.latest + ' disponible (installable manuellement).';
          open.hidden = false;
          open.onclick = () => bridge().open_external(result.url);
        } else {
          status.textContent = 'Version ' + result.current + ' à jour.';
        }
      } catch (error) {
        status.textContent = 'Connexion ou vérification Linux indisponible.';
      } finally {
        button.disabled = false;
      }
    });
    const shortcutStatus = document.getElementById('linuxShortcutStatus');
    for (const [id, method] of [
      ['linuxInstallShortcut', 'install_linux_launcher'],
      ['linuxRemoveShortcut', 'remove_linux_launcher']
    ]) {
      document.getElementById(id).addEventListener('click', async () => {
        try {
          if (!bridge() || !bridge()[method]) throw Error('Moteur Linux indisponible.');
          const result = await bridge()[method]();
          shortcutStatus.textContent = result && result.success
            ? (method === 'install_linux_launcher'
                ? 'Raccourci ajouté au menu des applications.'
                : 'Raccourci retiré.')
            : ((result && result.error) || 'Opération impossible.');
        } catch (error) {
          shortcutStatus.textContent = 'Impossible de modifier le raccourci Linux.';
        }
      });
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addLinuxSettings);
  } else {
    addLinuxSettings();
  }
})();
</script>
"""


def inject_linux_controls(html: str) -> str:
    if not isinstance(html, str) or "</body>" not in html:
        raise ValueError("Interface Windows HTML invalide.")
    if 'id="linuxExtraSettings"' in html:
        return html
    return html.replace("</body>", LINUX_SETTINGS_SCRIPT + "\n</body>", 1)
