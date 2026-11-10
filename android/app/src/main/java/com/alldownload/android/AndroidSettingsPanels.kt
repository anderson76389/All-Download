package com.alldownload.android

import android.app.Activity
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.LayerDrawable
import android.view.Gravity
import android.widget.Switch
import android.net.Uri
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

/**
 * Functional counterparts of the Windows Téléchargement / Application / Réseau
 * settings, adapted to touch navigation and Android's storage/security rules.
 *
 * No inert toggles: only yt-dlp flags actually applied by DownloadOptions
 * and native app preferences are presented as editable controls.
 */
internal object AndroidSettingsPanels {
    private val purple = Color.rgb(124, 58, 237)

    fun populate(activity: Activity, settingsPage: LinearLayout,
                 updateMessage: (String) -> Unit) {
        val prefs = DownloadOptions.get(activity)
        val light = prefs.getInt("theme", 0) == 1
        val oled = prefs.getInt("theme", 0) == 2
        val panelColor = if (light) Color.WHITE else if (oled) Color.rgb(14, 14, 14)
                         else Color.rgb(27, 28, 36)
        val borderColor = if (light) Color.rgb(226, 232, 240) else Color.rgb(51, 53, 66)
        val color = if (light) Color.rgb(15, 23, 42) else Color.rgb(243, 244, 246)
        val muted = if (light) Color.rgb(100, 116, 139) else Color.rgb(161, 161, 170)
        val fieldColor = if (light) Color.rgb(246, 247, 251)
                         else if (oled) Color.rgb(22, 22, 24) else Color.rgb(35, 36, 46)
        val tileColor = if (light) Color.rgb(245, 239, 255)
                        else if (oled) Color.rgb(38, 27, 49) else Color.rgb(49, 37, 70)
        val dp = activity.resources.displayMetrics.density
        fun px(value: Int) = (value * dp + .5f).toInt()

        fun label(value: String, size: Float = 14f, bold: Boolean = false,
                  tint: Int = color): TextView = TextView(activity).apply {
            text = value
            textSize = size
            setTextColor(tint)
            if (tint == muted) tag = "muted"
            if (bold) setTypeface(typeface, Typeface.BOLD)
        }

        // Same three settings sections as Windows, but touch-optimized on Android.
        val downloadPanel = LinearLayout(activity).apply {
            id = R.id.settingsDownloadPanel
            orientation = LinearLayout.VERTICAL
        }
        val applicationPanel = LinearLayout(activity).apply {
            id = R.id.settingsApplicationPanel
            orientation = LinearLayout.VERTICAL
        }
        val networkPanel = LinearLayout(activity).apply {
            id = R.id.settingsNetworkPanel
            orientation = LinearLayout.VERTICAL
        }
        // Apply one consistent vector tile, type scale and card spacing to
        // the XML settings as well as the newer Kotlin controls.
        fun surface(fill: Int, radius: Int = 15): GradientDrawable =
            GradientDrawable().apply {
                setColor(fill)
                cornerRadius = px(radius).toFloat()
                setStroke(px(1), borderColor)
            }

        fun sectionGlyph(iconId: Int): LayerDrawable? {
            val icon = activity.getDrawable(iconId)?.mutate() ?: return null
            icon.setTint(purple)
            val backdrop = GradientDrawable().apply {
                setColor(tileColor)
                cornerRadius = px(11).toFloat()
            }
            return LayerDrawable(arrayOf(backdrop, icon)).apply {
                setLayerInset(1, px(9), px(9), px(9), px(9))
                setBounds(0, 0, px(38), px(38))
            }
        }

        fun decorateHeading(title: TextView, iconId: Int) {
            title.textSize = 16f
            title.setTextColor(color)
            title.setTypeface(title.typeface, Typeface.BOLD)
            title.gravity = Gravity.CENTER_VERTICAL
            title.minHeight = px(40)
            title.includeFontPadding = false
            title.maxLines = 2
            title.ellipsize = android.text.TextUtils.TruncateAt.END
            title.setCompoundDrawablesRelative(sectionGlyph(iconId), null, null, null)
            title.compoundDrawablePadding = px(11)
        }

        fun decorateLegacyCard(id: Int, iconId: Int): LinearLayout {
            val panel = activity.findViewById<LinearLayout>(id)
            (panel.parent as? ViewGroup)?.removeView(panel)
            panel.setPadding(px(15), px(13), px(15), px(16))
            panel.background = surface(panelColor, 17)
            panel.elevation = 0f
            panel.layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = px(10) }
            decorateHeading(panel.getChildAt(0) as TextView, iconId)
            (panel.getChildAt(1) as? TextView)?.apply {
                textSize = 12f
                setTextColor(muted)
                setPadding(0, px(6), 0, px(10))
                maxLines = 4
            }
            return panel
        }

        val appearanceCard = decorateLegacyCard(R.id.settingsAppearanceCard,
            R.drawable.ic_sliders).also(applicationPanel::addView)
        val engineCard = decorateLegacyCard(R.id.settingsEngineCard,
            R.drawable.ic_download).also(applicationPanel::addView)
        val cookiesCard = decorateLegacyCard(R.id.settingsCookiesCard,
            R.drawable.ic_security).also(networkPanel::addView)
        appearanceCard.findViewById<Spinner>(R.id.themeSpinner).apply {
            minimumHeight = px(50)
            background = surface(fieldColor, 12)
        }
        engineCard.findViewById<Switch>(R.id.autoUpdateCheck).apply {
            textSize = 13f
            setTextColor(color)
            minimumHeight = px(54)
            gravity = Gravity.CENTER_VERTICAL
            showText = false
            thumbTintList = ColorStateList(arrayOf(
                intArrayOf(android.R.attr.state_checked), intArrayOf()),
                intArrayOf(Color.WHITE, if (light) Color.rgb(220, 223, 231) else Color.rgb(190, 190, 198)))
            trackTintList = ColorStateList(arrayOf(
                intArrayOf(android.R.attr.state_checked), intArrayOf()),
                intArrayOf(purple, borderColor))
        }
        listOf(R.id.importCookiesButton, R.id.removeCookiesButton).forEachIndexed {
                index, buttonId ->
            cookiesCard.findViewById<Button>(buttonId).apply {
                textSize = 13f
                gravity = Gravity.CENTER_VERTICAL or Gravity.START
                setPadding(px(13), 0, px(12), 0)
                compoundDrawablePadding = px(9)
                setTextColor(color)
                isAllCaps = false
                background = surface(fieldColor, 12)
                minimumHeight = px(52)
                layoutParams = (layoutParams as LinearLayout.LayoutParams).apply {
                    height = px(52)
                    topMargin = px(if (index == 0) 10 else 8)
                }
            }
        }
        val tabs = LinearLayout(activity).apply {
            id = R.id.settingsTabs
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, px(8), 0, px(4))
        }
        val sections = listOf(downloadPanel, applicationPanel, networkPanel)
        val labels = listOf("Médias", "Appli", "Réseau")
        val stackedTabs = activity.resources.configuration.screenWidthDp < 390 ||
            activity.resources.configuration.fontScale > 1.2f
        val tabIcons = listOf(R.drawable.ic_video, R.drawable.nav_settings,
            R.drawable.ic_network)
        val buttonIds = listOf(R.id.settingsTabDownload,
            R.id.settingsTabApplication, R.id.settingsTabNetwork)
        val buttons = labels.mapIndexed { index, caption ->
            Button(activity).apply {
                id = buttonIds[index]
                text = caption
                textSize = if (stackedTabs) 11.5f else 12f
                val image = activity.getDrawable(tabIcons[index])?.mutate()?.apply {
                    setTint(color)
                    setBounds(0, 0, px(17), px(17))
                }
                setCompoundDrawablesRelative(
                    if (stackedTabs) null else image,
                    if (stackedTabs) image else null, null, null)
                compoundDrawablePadding = px(if (stackedTabs) 2 else 5)
                gravity = android.view.Gravity.CENTER
                setSingleLine(true)
                ellipsize = android.text.TextUtils.TruncateAt.END
                includeFontPadding = false
                setPadding(px(4), 0, px(4), 0)
                isAllCaps = false
                minHeight = px(if (stackedTabs) 60 else 48)
                tabs.addView(this, LinearLayout.LayoutParams(
                    0, px(if (stackedTabs) 62 else 49), 1f).apply {
                    marginStart = if (index == 0) 0 else px(3)
                    marginEnd = if (index == 2) 0 else px(3)
                })
            }
        }
        val host = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            addView(downloadPanel)
            addView(applicationPanel)
            addView(networkPanel)
        }
        // Title and subtitle precede the categories on both phone and tablet.
        settingsPage.addView(tabs, 2)
        settingsPage.addView(host, 3)
        fun selectTab(index: Int) {
            for (section in sections.indices) {
                sections[section].visibility = if (index == section)
                    View.VISIBLE else View.GONE
                val active = section == index
                buttons[section].background = GradientDrawable().apply {
                    setColor(if (active) purple else panelColor)
                    cornerRadius = px(16).toFloat()
                    setStroke(px(1), if (active) purple else borderColor)
                }
                buttons[section].tag = if (active) "primary" else "settings-tab"
                buttons[section].setTextColor(if (active) Color.WHITE else color)
                buttons[section].compoundDrawablesRelative.filterNotNull()
                    .forEach { it.setTint(if (active) Color.WHITE else color) }
            }
            prefs.edit().putInt("settings_tab", index).apply()
        }
        buttons.forEachIndexed { index, button ->
            button.setOnClickListener { selectTab(index) }
        }
        selectTab(prefs.getInt("settings_tab", 0).coerceIn(0, 2))

        fun card(title: String, subtitle: String,
                 group: LinearLayout = downloadPanel): LinearLayout {
            val panel = LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(px(15), px(13), px(15), px(16))
                background = surface(panelColor, 17)
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = px(10) }
            }
            val sectionIcon = when (title) {
                "Téléchargements" -> R.drawable.ic_download
                "Audio" -> R.drawable.ic_audio
                "Métadonnées et miniatures" -> R.drawable.ic_metadata
                "SponsorBlock" -> R.drawable.ic_security
                "Réseau et connexions" -> R.drawable.ic_network
                "Application et notifications" -> R.drawable.ic_notifications
                "Mises à jour Android" -> R.drawable.ic_update
                else -> R.drawable.ic_sliders
            }
            panel.addView(label(title, 16f, true).apply {
                decorateHeading(this, sectionIcon)
            }, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(40)))
            panel.addView(label(subtitle, 12f, tint = muted).apply {
                maxLines = 4
                setPadding(0, px(6), 0, px(10))
            })
            group.addView(panel)
            return panel
        }

        fun spinner(panel: LinearLayout, title: String, keys: List<String>,
                    descriptions: List<String>, preference: String, initial: String) {
            panel.addView(label(title, 13.5f, true).apply {
                setPadding(0, px(14), 0, px(7))
            })
            val view = Spinner(activity).apply {
                minimumHeight = px(50)
                contentDescription = title
                background = surface(fieldColor, 12)
            }
            val adapter = object : ArrayAdapter<String>(
                activity, android.R.layout.simple_spinner_dropdown_item, descriptions) {
                override fun getView(position: Int, convertView: android.view.View?,
                                     parent: ViewGroup): android.view.View {
                    val textView = super.getView(position, convertView, parent)
                    if (textView is TextView) {
                        textView.setTextColor(color)
                        textView.textSize = 14f
                        textView.gravity = android.view.Gravity.CENTER_VERTICAL
                        textView.setSingleLine(true)
                        textView.ellipsize = android.text.TextUtils.TruncateAt.END
                        val arrow = activity.getDrawable(R.drawable.ic_chevron)?.mutate()?.apply {
                            setTint(muted)
                            setBounds(0, 0, px(18), px(18))
                        }
                        textView.setCompoundDrawablesRelative(null, null, arrow, null)
                        textView.compoundDrawablePadding = px(7)
                        textView.setPadding(px(13), 0, px(12), 0)
                    }
                    return textView
                }
                override fun getDropDownView(position: Int, convertView: android.view.View?,
                                             parent: ViewGroup): android.view.View {
                    val item = super.getDropDownView(position, convertView, parent)
                    if (item is TextView) {
                        item.setTextColor(color)
                        item.textSize = 14f
                        item.setPadding(px(14), px(13), px(14), px(13))
                        item.minHeight = px(48)
                    }
                    return item
                }
            }
            view.adapter = adapter
            view.setSelection(keys.indexOf(prefs.getString(preference, initial))
                .coerceAtLeast(0))
            view.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?, selected: android.view.View?,
                                            position: Int, id: Long) {
                    prefs.edit().putString(preference, keys[position]).apply()
                }
            }
            panel.addView(view, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(50)))
        }

        fun number(panel: LinearLayout, title: String, values: List<Int>,
                   preference: String, initial: Int) {
            spinner(panel, title, values.map { it.toString() },
                values.map { it.toString() }, preference + "_display",
                prefs.getString(preference + "_display", initial.toString()).orEmpty())
            // Persist integer value as well (actual yt-dlp reads this).
            val view = panel.getChildAt(panel.childCount - 1) as Spinner
            view.setSelection(values.indexOf(prefs.getInt(preference, initial)).coerceAtLeast(0))
            view.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?, selected: android.view.View?,
                                            position: Int, id: Long) {
                    prefs.edit().putInt(preference, values[position]).apply()
                }
            }
        }

        fun toggle(panel: LinearLayout, text: String, detail: String,
                   key: String, default: Boolean = false): Switch {
            val row = LinearLayout(activity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                minimumHeight = px(64)
                setPadding(0, px(9), 0, px(8))
            }
            val captions = LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL
                addView(label(text, 14f, true).apply {
                    maxLines = 2
                    ellipsize = android.text.TextUtils.TruncateAt.END
                })
                addView(label(detail, 12f, tint = muted).apply {
                    maxLines = 4
                    setPadding(0, px(3), 0, 0)
                })
            }
            row.addView(captions, LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = px(12) })
            val control = Switch(activity).apply {
                contentDescription = text
                showText = false
                isChecked = prefs.getBoolean(key, default)
                minimumWidth = px(52)
                minimumHeight = px(48)
                thumbTintList = ColorStateList(arrayOf(
                    intArrayOf(android.R.attr.state_checked), intArrayOf()),
                    intArrayOf(Color.WHITE, if (light) Color.rgb(221, 224, 232)
                        else Color.rgb(190, 190, 198)))
                trackTintList = ColorStateList(arrayOf(
                    intArrayOf(android.R.attr.state_checked), intArrayOf()),
                    intArrayOf(purple, borderColor))
                setOnCheckedChangeListener { _, checked ->
                    prefs.edit().putBoolean(key, checked).apply()
                }
            }
            row.addView(control, LinearLayout.LayoutParams(px(56), px(48)))
            row.setOnClickListener { control.isChecked = !control.isChecked }
            panel.addView(row, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            return control
        }

        fun entry(panel: LinearLayout, title: String, key: String,
                  hint: String, private: Boolean = false) {
            panel.addView(label(title, 13.5f, true).apply {
                setPadding(0, px(14), 0, px(7))
            })
            val input = EditText(activity).apply {
                setSingleLine(true)
                textSize = 14f
                setTextColor(color)
                setHintTextColor(muted)
                this.hint = hint
                setText(prefs.getString(key, "").orEmpty())
                setPadding(px(12), 0, px(12), 0)
                background = surface(fieldColor, 12)
                addTextChangedListener(object : TextWatcher {
                    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                        if ((s?.length ?: 0) <= 500) prefs.edit().putString(key, s.toString()).apply()
                    }
                    override fun afterTextChanged(s: Editable?) {}
                })
            }
            panel.addView(input, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(50)))
            if (private) panel.addView(label(
                "Stocké uniquement dans les préférences privées Android. Ne partagez pas de mots de passe.",
                11f, tint = muted))
        }

        fun button(panel: LinearLayout, title: String, onClick: () -> Unit) {
            val primary = title.startsWith("Rechercher")
            val iconRes = if (primary) R.drawable.ic_update else R.drawable.ic_network
            val textColor = if (primary) Color.WHITE else color
            val b = Button(activity).apply {
                text = title
                textSize = 13.5f
                setSingleLine(true)
                ellipsize = android.text.TextUtils.TruncateAt.END
                contentDescription = title
                isAllCaps = false
                setTextColor(textColor)
                val image = activity.getDrawable(iconRes)?.mutate()?.apply {
                    setTint(textColor)
                    setBounds(0, 0, px(19), px(19))
                }
                setCompoundDrawablesRelative(image, null, null, null)
                compoundDrawablePadding = px(10)
                gravity = Gravity.CENTER_VERTICAL or Gravity.START
                setPadding(px(15), 0, px(12), 0)
                background = if (primary)
                    GradientDrawable().apply {
                        setColor(purple)
                        cornerRadius = px(12).toFloat()
                    } else surface(fieldColor, 12)
                minHeight = px(52)
                stateListAnimator = null
                setOnClickListener { onClick() }
            }
            panel.addView(b, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(52)).apply { topMargin = px(9) })
        }

        val files = card("Téléchargements", "Formats vidéo et organisation des fichiers.")
        files.addView(label("Téléchargements/All-Download/",
            12f, tint = muted))
        files.addView(label("Dossier public géré par Android.",
            11f, tint = muted).apply { setPadding(0, px(10), 0, 0) })
        spinner(files, "Format vidéo", listOf("MP4", "MKV"),
            listOf("MP4 (compatibilité)", "MKV (conteneur natif)"),
            "video_format", "MP4")

        toggle(files, "Remuxer dans le conteneur choisi",
            "Sans réencodage. Certaines sources ne peuvent pas être remuxées en MP4.",
            "remux_video")

        val audio = card("Audio", "Qualité et conversion des fichiers audio.")
        spinner(audio, "Qualité MP3",
            listOf("0", "128K", "192K", "256K", "320K"),
            listOf("Meilleure qualité disponible", "128 kb/s", "192 kb/s", "256 kb/s", "320 kb/s"),
            "audio_quality", "0")
        audio.addView(label("La qualité dépend de la source.",
            11f, tint = muted))

        val media = card("Métadonnées et miniatures",
            "Informations et sous-titres des prochains fichiers.")
        toggle(media, "Ajouter titre et artiste", "Métadonnées intégrées si disponibles.",
            "embed_metadata")
        toggle(media, "Enregistrer la miniature", "Image de couverture séparée du média.",
            "write_thumbnail")
        toggle(media, "Intégrer la couverture", "Peut nécessiter un post-traitement FFmpeg.",
            "embed_thumbnail")
        toggle(media, "Enregistrer les sous-titres", "FR/EN si les sous-titres sont proposés.",
            "write_subtitles")
        toggle(media, "Sous-titres automatiques", "Uniquement si l’option précédente est active et la plateforme le permet.",
            "auto_subtitles")

        val sponsor = card("SponsorBlock",
            "Utilisé uniquement pour YouTube lorsque le site rend ces données accessibles.")
        toggle(sponsor, "Activer SponsorBlock",
            "Désactivé par défaut pour éviter les échecs sur les plateformes non compatibles.",
            "sponsor_enable")
        spinner(sponsor, "Segments à supprimer",
            listOf("sponsor", "all", "none"),
            listOf("Segments sponsorisés", "Tous les segments détectés", "Ne rien supprimer"),
            "sponsor_remove", "sponsor")
        toggle(sponsor, "Marquer les sections en chapitres",
            "Insérer des chapitres quand la source le permet.", "sponsor_mark")
        toggle(sponsor, "Découpe précise", "Traitement FFmpeg supplémentaire.",
            "sponsor_exact")

        val network = card("Réseau et connexions",
            "Options de connexion et paramètres avancés.",
            networkPanel)
        toggle(network, "Utiliser un proxy",
            "HTTP, HTTPS ou SOCKS. Vérifiez sa disponibilité avant un téléchargement.",
            "proxy_enabled")
        entry(network, "Adresse du proxy", "proxy_url",
            "socks5://127.0.0.1:1080", true)
        spinner(network, "Navigateur annoncé (User-Agent)",
            listOf("auto", "android_chrome", "android_firefox"),
            listOf("Automatique", "Chrome Android", "Firefox Android"),
            "user_agent", "auto")
        network.addView(label("Le User-Agent modifie l'en-tête HTTP, pas l'empreinte TLS du navigateur.",
            11f, tint = muted))
        number(network, "Tentatives en cas d’erreur", listOf(1, 3, 5, 10, 15),
            "network_retries", 10)
        number(network, "Téléchargements de fragments simultanés", listOf(1, 2, 4, 8),
            "fragments", 1)
        number(network, "Délai réseau (secondes)", listOf(10, 20, 30, 45, 60),
            "network_timeout", 20)
        entry(network, "Arguments d'extracteur avancés", "extractor_args",
            "youtube:player_client=android")
        network.addView(label("Avancé : un argument incompatible peut empêcher un téléchargement. Laissez vide si inutile.",
            11f, tint = muted))

        val app = card("Application et notifications",
            "Comportement et confort d’utilisation.",
            applicationPanel)
        toggle(app, "Notification de fin de téléchargement",
            "En cours : notification Android toujours affichée.",
            "notify_finished", true)
        toggle(app, "Réduire les animations",
            "Désactive les transitions et animations.",
            "reduce_motion")

        val updates = card("Mises à jour Android",
            "APK Android officiels depuis GitHub.",
            applicationPanel)
        val updateToggle = toggle(updates, "Me prévenir des nouvelles versions",
            "Une vérification discrète à l’ouverture, au plus toutes les 30 minutes.",
            "update_alerts", true)
        updateToggle.apply {
            isChecked = AndroidUpdates.enabled(activity)
            setOnCheckedChangeListener { _, checked ->
                prefs.edit().putBoolean("update_alerts", checked).apply()
                AndroidUpdates.setEnabled(activity, checked)
            }
        }
        button(updates, "Rechercher une mise à jour") {
            updateMessage("Recherche sur les Releases GitHub…")
            AndroidUpdates.check(activity, true, updateMessage)
        }
        updates.addView(label("All-Download Android " + BuildConfig.VERSION_NAME +
            " · les prochaines Releases nécessitent la signature permanente. Une ancienne bêta debug peut demander une dernière réinstallation.",
            11f, tint = muted))
        button(updates, "Voir les Releases GitHub") {
            activity.startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("https://github.com/anderson76389/All-Download/releases")))
        }

        // Logical order: network settings then private cookies; appearance,
        // app, releases, then technical engine settings. Controls are reparented,
        // not recreated, so previously attached listeners remain active.
        networkPanel.removeView(cookiesCard)
        networkPanel.addView(cookiesCard)
        applicationPanel.removeView(engineCard)
        applicationPanel.addView(engineCard)
    }
}
