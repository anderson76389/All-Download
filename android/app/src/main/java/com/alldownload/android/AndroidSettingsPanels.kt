package com.alldownload.android

import android.app.Activity
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.text.Editable
import android.text.TextWatcher
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
                         else Color.rgb(33, 33, 33)
        val borderColor = if (light) Color.rgb(226, 232, 240) else Color.rgb(55, 55, 55)
        val color = if (light) Color.rgb(15, 23, 42) else Color.rgb(243, 244, 246)
        val muted = if (light) Color.rgb(100, 116, 139) else Color.rgb(161, 161, 170)
        val dp = activity.resources.displayMetrics.density
        fun px(value: Int) = (value * dp + .5f).toInt()

        fun label(value: String, size: Float = 14f, bold: Boolean = false,
                  tint: Int = color): TextView = TextView(activity).apply {
            text = value
            textSize = size
            setTextColor(tint)
            if (bold) setTypeface(typeface, Typeface.BOLD)
        }

        fun card(title: String, subtitle: String): LinearLayout {
            val panel = LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(px(19), px(18), px(19), px(19))
                background = GradientDrawable().apply {
                    setColor(panelColor)
                    cornerRadius = px(18).toFloat()
                    setStroke(px(1), borderColor)
                }
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                    topMargin = px(14)
                }
            }
            panel.addView(label(title, 18f, true))
            panel.addView(label(subtitle, 12f, tint = muted).apply {
                setPadding(0, px(7), 0, px(13))
            })
            // Insert before the footer text explaining the beta version.
            settingsPage.addView(panel, settingsPage.childCount - 1)
            return panel
        }

        fun spinner(panel: LinearLayout, title: String, keys: List<String>,
                    descriptions: List<String>, preference: String, initial: String) {
            panel.addView(label(title, 13f, true).apply {
                setPadding(0, px(12), 0, px(5))
            })
            val view = Spinner(activity).apply {
                minimumHeight = px(54)
                contentDescription = title
                background = GradientDrawable().apply {
                    setColor(if (light) Color.rgb(241, 245, 249) else Color.rgb(29, 29, 29))
                    cornerRadius = px(10).toFloat()
                    setStroke(px(1), borderColor)
                }
            }
            val adapter = object : ArrayAdapter<String>(
                activity, android.R.layout.simple_spinner_dropdown_item, descriptions) {
                override fun getView(position: Int, convertView: android.view.View?,
                                     parent: ViewGroup): android.view.View {
                    val textView = super.getView(position, convertView, parent)
                    if (textView is TextView) {
                        textView.setTextColor(color)
                        textView.setPadding(px(13), px(12), px(8), px(12))
                    }
                    return textView
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
                ViewGroup.LayoutParams.MATCH_PARENT, px(54)))
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
                   key: String, default: Boolean = false) {
            val check = CheckBox(activity).apply {
                this.text = text
                textSize = 14f
                setTextColor(color)
                buttonTintList = ColorStateList.valueOf(purple)
                isChecked = prefs.getBoolean(key, default)
                minHeight = px(48)
                setOnCheckedChangeListener { _, checked ->
                    prefs.edit().putBoolean(key, checked).apply()
                }
            }
            panel.addView(check, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            panel.addView(label(detail, 11f, tint = muted).apply {
                setPadding(px(8), 0, px(8), px(8))
            })
        }

        fun entry(panel: LinearLayout, title: String, key: String,
                  hint: String, private: Boolean = false) {
            panel.addView(label(title, 13f, true).apply {
                setPadding(0, px(12), 0, px(5))
            })
            val input = EditText(activity).apply {
                setSingleLine(true)
                textSize = 13f
                setTextColor(color)
                setHintTextColor(muted)
                this.hint = hint
                setText(prefs.getString(key, "").orEmpty())
                setPadding(px(12), 0, px(12), 0)
                background = GradientDrawable().apply {
                    setColor(if (light) Color.rgb(241, 245, 249) else Color.rgb(29, 29, 29))
                    cornerRadius = px(10).toFloat()
                    setStroke(px(1), borderColor)
                }
                addTextChangedListener(object : TextWatcher {
                    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                        if ((s?.length ?: 0) <= 500) prefs.edit().putString(key, s.toString()).apply()
                    }
                    override fun afterTextChanged(s: Editable?) {}
                })
            }
            panel.addView(input, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(52)))
            if (private) panel.addView(label(
                "Stocké uniquement dans les préférences privées Android. Ne partagez pas de mots de passe.",
                11f, tint = muted))
        }

        fun button(panel: LinearLayout, title: String, onClick: () -> Unit) {
            val b = Button(activity).apply {
                text = title
                isAllCaps = false
                setTextColor(Color.WHITE)
                background = GradientDrawable().apply {
                    setColor(purple)
                    cornerRadius = px(12).toFloat()
                }
                setOnClickListener { onClick() }
            }
            panel.addView(b, LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, px(51)).apply { topMargin = px(9) })
        }

        val files = card("Téléchargements", "Comme sous Windows, les fichiers sont rangés automatiquement dans les sept catégories All-Download.")
        files.addView(label("Téléchargements / All-Download / VIDÉOS, AUDIOS, TWITCH, GIFS, CHAÎNES, PLAYLIST, AUTRES",
            12f, tint = muted))
        files.addView(label("Android protège ce dossier : impossible de choisir un chemin extérieur à All-Download.",
            11f, tint = muted).apply { setPadding(0, px(10), 0, 0) })
        spinner(files, "Format vidéo", listOf("MP4", "MKV"),
            listOf("MP4 (compatibilité)", "MKV (conteneur natif)"),
            "video_format", "MP4")

        val media = card("Métadonnées et miniatures",
            "Options appliquées au moteur yt-dlp pour les téléchargements suivants.")
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
            "Options équivalentes à Windows et utilisables avec yt-dlp sur Android.")
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
        number(network, "Tentatives en cas d’erreur", listOf(1, 3, 5, 8, 12),
            "network_retries", 5)
        number(network, "Téléchargements de fragments simultanés", listOf(1, 2, 4, 8),
            "fragments", 2)
        number(network, "Délai réseau (secondes)", listOf(10, 20, 30, 45, 60),
            "network_timeout", 20)
        entry(network, "Arguments d'extracteur avancés", "extractor_args",
            "youtube:player_client=android")
        network.addView(label("Avancé : un argument incompatible peut empêcher un téléchargement. Laissez vide si inutile.",
            11f, tint = muted))

        val app = card("Application et notifications",
            "Même esprit que Windows, avec les obligations système Android.")
        toggle(app, "Notification de fin de téléchargement",
            "La notification en cours de téléchargement reste obligatoire pour le service Android.",
            "notify_finished", true)
        toggle(app, "Réduire les animations",
            "Désactive l'entrée animée du popup de mise à jour et les transitions de pages.",
            "reduce_motion")
        toggle(app, "Actualiser yt-dlp automatiquement",
            "Tentative hebdomadaire pour les réseaux sociaux ; repli sur la version intégrée.",
            "auto_update", true)

        val updates = card("Mises à jour Android",
            "Mises à jour détectées depuis les Releases Android de GitHub, sans toucher à Windows.")
        toggle(updates, "Me prévenir des nouvelles versions",
            "Vérification à l'ouverture au plus une fois toutes les 12 h.",
            "update_alerts", true)
        val updateToggle = updates.getChildAt(updates.childCount - 2) as? CheckBox
        updateToggle?.apply {
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
            " · les APK bêta actuels ont une signature de test. Une désinstallation peut être nécessaire pour les mises à jour.",
            11f, tint = muted))
        button(updates, "Voir toutes les Releases Android") {
            activity.startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("https://github.com/anderson76389/All-Download/releases")))
        }
    }
}
