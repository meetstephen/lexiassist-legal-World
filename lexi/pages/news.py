"""LexiAssist legal-news / practice-update generator."""
from __future__ import annotations

# Barrel import: mirrors the global namespace of the original single-file
# app.py exactly. The original code below is unchanged.
from ..runtime import *      # noqa: F401, F403
from ..crypto import *       # noqa: F401, F403
from ..constants import *    # noqa: F401, F403
from ..prompts import *      # noqa: F401, F403
from ..legal_data import *   # noqa: F401, F403
from ..citations import *    # noqa: F401, F403
from ..themes import *       # noqa: F401, F403
from ..rag import *          # noqa: F401, F403
from ..fuzzy import *        # noqa: F401, F403
from ..exports import *      # noqa: F401, F403
from ..database import *     # noqa: F401, F403
from ..auth import *         # noqa: F401, F403
from ..helpers import *      # noqa: F401, F403

# ═══════════════════════════════════════════════════════
# PAGE: LEGAL NEWS FEED
# ═══════════════════════════════════════════════════════
def render_legal_news():
    st.markdown("""<div class="page-header">
    <h2>📰 Practice Update Generator</h2>
    <p>AI-assisted Nigerian legal practice updates · Reading list · Case relevance scan · Deep-dive analysis</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
    '<div style="background:var(--la-bg2);border:1px solid #f59e0b;'
    'border-left:4px solid #f59e0b;border-radius:8px;'
    'padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.85rem;">'
    '<strong>⚠️ Private Beta Warning:</strong> This is an AI-assisted practice update generator, '
    'not a live verified legal news service. Verify every development against primary sources, '
    'law reports, regulator publications, or official court releases before relying on it.'
    '</div>',
    unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    # Ensure bookmarks list exists in session
    if "nf_bookmarks" not in st.session_state:
        st.session_state["nf_bookmarks"] = []

    bookmarks = st.session_state["nf_bookmarks"]

    # ── Top-level tabs ──
    tab_feed, tab_bookmarks, tab_scan = st.tabs([
        "📰 Live Feed",
        f"📌 Reading List ({len(bookmarks)})",
        "🎯 Case Relevance Scan",
    ])

    # ═══════════════════════════════════════════════════
    # TAB 1 — LIVE FEED
    # ═══════════════════════════════════════════════════
    with tab_feed:
        # ── Controls ──
        nf1, nf2, nf3 = st.columns([2, 2, 1])
        with nf1:
            nf_subject = st.selectbox(
                "Subject Area",
                NEWS_FEED_SUBJECTS,
                key="nf_subject_sel",
            )
        with nf2:
            nf_search = st.text_input(
                "🔍 Search within feed",
                key="nf_search_inp",
                placeholder="e.g. land registration, employment, tax",
            )
        with nf3:
            st.markdown("<br>", unsafe_allow_html=True)
            nf_generate_btn = st.button(
                "🔄 Generate Updates",
                type="primary", use_container_width=True,
                key="nf_generate_btn",
            )

        if nf_generate_btn:
            subject_val = nf_subject if nf_subject != "All Areas" else "all major practice areas of Nigerian law"
            prompt = NEWS_FEED_PROMPT.format(
                subject_area=subject_val,
                today=date.today().strftime("%d %B %Y"),
            )
            with st.spinner(f"📰 Fetching legal developments — {nf_subject}…"):
                raw = generate(prompt, NEWS_FEED_SYSTEM, "brief", "research")
            try:
                clean = raw.strip().replace("```json", "").replace("```", "").strip()
                feed_data = json.loads(clean)
                st.session_state["nf_feed_data"] = feed_data
                st.session_state["nf_subject_loaded"] = nf_subject
                # Clear any stale deep-dive results
                st.session_state["nf_deepdive"] = {}
            except Exception:
                st.session_state["nf_feed_data"] = {"_raw": raw, "items": []}
                st.session_state["nf_subject_loaded"] = nf_subject

        feed_data = st.session_state.get("nf_feed_data", None)
        subject_loaded = st.session_state.get("nf_subject_loaded", "")
        if "nf_deepdive" not in st.session_state:
            st.session_state["nf_deepdive"] = {}

        if feed_data is None:
            st.markdown("""
<div style="background:var(--la-bg2);border:1.5px dashed var(--la-border);border-radius:0.85rem;
padding:2.5rem;text-align:center;color:var(--la-text2);">
  <h3 style="margin:0 0 0.5rem 0;color:var(--la-text);">📰 No Practice Updates Generated Yet</h3>
  <p style="margin:0;">Select a subject area and click <strong>Fetch Latest</strong>
  to load Nigerian legal developments.</p>
</div>""", unsafe_allow_html=True)

        elif "_raw" in feed_data:
            raw_text = feed_data.get("_raw", "")
            if raw_text and raw_text.strip():
                st.warning("⚠️ Could not parse as structured data. Showing raw output:")
                st.markdown(f'<div class="response-box">{esc(raw_text)}</div>',
                            unsafe_allow_html=True)
            else:
                st.error(
                    "⚠️ The AI response came back empty. Please try again."
                )

        else:
            items = feed_data.get("items", [])
            gen_date = feed_data.get("generated_date", date.today().strftime("%d %B %Y"))

            # ── Header ──
            hd1, hd2 = st.columns([3, 1])
            with hd1:
                st.markdown(f"""
<div style="padding:0.6rem 1rem;background:var(--la-bg2);border:1px solid var(--la-border);border-radius:0.5rem;
display:inline-block;font-size:0.9rem;color:var(--la-text);">
  📅 <strong>Ref date:</strong> {esc(gen_date)} &nbsp;|&nbsp;
  📂 <strong>Subject:</strong> {esc(subject_loaded)} &nbsp;|&nbsp;
  📰 <strong>{len(items)} items</strong> &nbsp;|&nbsp;
  📌 <strong>{len(bookmarks)} bookmarked</strong>
</div>""", unsafe_allow_html=True)
            with hd2:
                if st.button("🗑️ Clear Feed", key="nf_clear_btn", use_container_width=True):
                    st.session_state["nf_feed_data"] = None
                    st.session_state["nf_subject_loaded"] = ""
                    st.session_state["nf_deepdive"] = {}
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Filter by search ──
            search_val = nf_search.strip().lower()
            display_items = items
            if search_val:
                display_items = [
                    item for item in items
                    if search_val in item.get("title", "").lower()
                    or search_val in item.get("summary", "").lower()
                    or search_val in item.get("key_takeaway", "").lower()
                    or search_val in item.get("practice_impact", "").lower()
                ]

            if not display_items:
                st.info(f"No items match '{nf_search}'. Try a different term or clear the filter.")
            else:
                for item in display_items:
                    item_id = str(item.get("id", 0))
                    title = item.get("title", "Untitled Development")
                    summary = item.get("summary", "")
                    takeaway = item.get("key_takeaway", "")
                    impact = item.get("practice_impact", "")

                    # Check if bookmarked
                    is_bookmarked = any(b.get("id") == item_id for b in bookmarks)
                    bm_icon = "📌" if is_bookmarked else "🔖"

                    with st.expander(f"{'📌' if is_bookmarked else '📰'} {esc(title)}", expanded=False):
                        st.markdown(f"""
<div style="background:var(--la-card);border:1px solid var(--la-border);border-radius:0.75rem;padding:1.2rem;">
  <p style="margin:0 0 0.9rem 0;font-size:0.95rem;line-height:1.7;color:var(--la-text);">{esc(summary)}</p>
  <div style="background:var(--la-bg2);border-left:3px solid var(--la-pos);padding:0.7rem 1rem;
  border-radius:0.4rem;margin-bottom:0.7rem;">
    <strong style="color:var(--la-pos);">🔑 Key Takeaway:</strong>
    <span style="font-size:0.93rem;color:var(--la-text);"> {esc(takeaway)}</span>
  </div>
  <div style="background:var(--la-bg2);border-left:3px solid var(--la-acc);padding:0.7rem 1rem;
  border-radius:0.4rem;">
    <strong style="color:var(--la-acc);">⚖️ Practice Impact:</strong>
    <span style="font-size:0.93rem;color:var(--la-text);"> {esc(impact)}</span>
  </div>
</div>""", unsafe_allow_html=True)

                        # ── Action buttons ──
                        act1, act2, act3 = st.columns(3)

                        with act1:
                            bm_label = "📌 Bookmarked" if is_bookmarked else "🔖 Bookmark"
                            if st.button(bm_label, key=f"nf_bm_{item_id}", use_container_width=True):
                                if is_bookmarked:
                                    st.session_state["nf_bookmarks"] = [
                                        b for b in bookmarks if b.get("id") != item_id
                                    ]
                                    st.success("Removed from Reading List.")
                                else:
                                    st.session_state["nf_bookmarks"].append({
                                        "id": item_id,
                                        "title": title,
                                        "summary": summary,
                                        "key_takeaway": takeaway,
                                        "practice_impact": impact,
                                        "subject": subject_loaded,
                                        "saved_at": datetime.now().strftime("%d %b %Y %H:%M"),
                                    })
                                    st.success("✅ Added to Reading List.")
                                st.rerun()

                        with act2:
                            dd_key = f"nf_dd_{item_id}"
                            dd_result = st.session_state["nf_deepdive"].get(item_id, "")
                            if not dd_result:
                                if st.button("🔬 Deep Dive Analysis", key=dd_key, use_container_width=True):
                                    dd_prompt = NEWS_DEEPDIVE_PROMPT.format(
                                        title=title, summary=summary,
                                        takeaway=takeaway, impact=impact,
                                    )
                                    with st.spinner(f"🔬 Analysing: {title[:50]}…"):
                                        dd_result = generate(dd_prompt, NEWS_DEEPDIVE_SYSTEM, "standard", "analysis")
                                    st.session_state["nf_deepdive"][item_id] = dd_result
                                    st.rerun()
                            else:
                                if st.button("🔬 Hide Deep Dive", key=dd_key, use_container_width=True):
                                    st.session_state["nf_deepdive"].pop(item_id, None)
                                    st.rerun()

                        with act3:
                            st.download_button(
                                "📥 Export Item",
                                export_txt(
                                    f"TITLE: {title}\n\nSUMMARY:\n{summary}\n\n"
                                    f"KEY TAKEAWAY:\n{takeaway}\n\nPRACTICE IMPACT:\n{impact}",
                                    title,
                                ),
                                f"LegalNews_{item_id}_{datetime.now():%Y%m%d}.txt",
                                "text/plain",
                                key=f"nf_dl_{item_id}", use_container_width=True,
                            )

                        # ── Deep Dive result ──
                        if dd_result:
                            st.markdown(f"""
<div style="margin-top:1rem;background:var(--la-card);border:1px solid var(--la-border);
border-radius:0.75rem;padding:1.4rem;">
  <h5 style="margin:0 0 0.8rem 0;color:var(--la-text);">🔬 Full Legal Analysis</h5>
  <div style="white-space:pre-wrap;font-size:0.92rem;line-height:1.75;">{esc(dd_result)}</div>
</div>""", unsafe_allow_html=True)
                            safe_pdf_download(
                                dd_result, f"Deep Dive — {title}",
                                f"DeepDive_{item_id}_{datetime.now():%Y%m%d}",
                                f"nf_dd_pdf_{item_id}",
                            )

            # ── Export full feed ──
            st.markdown("---")
            if items:
                feed_text = f"NIGERIAN LEGAL NEWS FEED\nSubject: {subject_loaded}\nDate: {gen_date}\n\n"
                for item in items:
                    feed_text += f"{'='*60}\n{item.get('title','')}\n\n"
                    feed_text += f"SUMMARY:\n{item.get('summary','')}\n\n"
                    feed_text += f"KEY TAKEAWAY:\n{item.get('key_takeaway','')}\n\n"
                    feed_text += f"PRACTICE IMPACT:\n{item.get('practice_impact','')}\n\n"

                ef1, ef2 = st.columns(2)
                fname = f"LegalNewsFeed_{subject_loaded.replace(' ','_').replace('/','_')}_{datetime.now():%Y%m%d_%H%M}"
                with ef1:
                    st.download_button(
                        "📥 Export Full Feed (TXT)",
                        export_txt(feed_text, f"Nigerian Legal News Feed — {subject_loaded}"),
                        f"{fname}.txt", "text/plain",
                        key="nf_dl_txt", use_container_width=True,
                    )
                with ef2:
                    st.download_button(
                        "📥 Export Full Feed (HTML)",
                        export_html(feed_text, f"Nigerian Legal News Feed — {subject_loaded}"),
                        f"{fname}.html", "text/html",
                        key="nf_dl_html", use_container_width=True,
                    )

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> This feed is AI-generated. All case citations are
            [CITATION TO BE VERIFIED]. Verify all developments against official law reports
            and primary sources before relying on them in practice.
        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # TAB 2 — READING LIST / BOOKMARKS
    # ═══════════════════════════════════════════════════
    with tab_bookmarks:
        bookmarks = st.session_state["nf_bookmarks"]
        if not bookmarks:
            st.info("📌 No items bookmarked yet. Open any feed item and click 🔖 Bookmark to save it here.")
        else:
            st.markdown(f"##### 📌 {len(bookmarks)} Saved Item(s)")

            bm_search = st.text_input("🔍 Search reading list", key="bm_search_inp",
                                       placeholder="Search your bookmarks...")
            bm_search_val = bm_search.strip().lower()
            display_bm = bookmarks
            if bm_search_val:
                display_bm = [b for b in bookmarks
                               if bm_search_val in b.get("title", "").lower()
                               or bm_search_val in b.get("summary", "").lower()]

            for i, bm in enumerate(display_bm):
                with st.expander(f"📌 {esc(bm.get('title',''))}"
                                 f" · {esc(bm.get('subject',''))} · {esc(bm.get('saved_at',''))}",
                                 expanded=False):
                    st.markdown(f"""
<div style="background:var(--la-card);border:1px solid var(--la-border);border-radius:0.75rem;padding:1.1rem;">
  <p style="margin:0 0 0.8rem 0;font-size:0.93rem;line-height:1.7;color:var(--la-text);">{esc(bm.get('summary',''))}</p>
  <div style="background:var(--la-bg2);border-left:3px solid var(--la-pos);padding:0.6rem 0.9rem;
  border-radius:0.4rem;margin-bottom:0.6rem;">
    <strong style="color:var(--la-pos);">🔑</strong>
    <span style="color:var(--la-text);"> {esc(bm.get('key_takeaway',''))}</span>
  </div>
  <div style="background:var(--la-bg2);border-left:3px solid var(--la-acc);padding:0.6rem 0.9rem;
  border-radius:0.4rem;">
    <strong style="color:var(--la-acc);">⚖️</strong>
    <span style="color:var(--la-text);"> {esc(bm.get('practice_impact',''))}</span>
  </div>
</div>""", unsafe_allow_html=True)

                    bm_act1, bm_act2 = st.columns(2)
                    with bm_act1:
                        st.download_button(
                            "📥 Export (TXT)",
                            export_txt(
                                f"TITLE: {bm.get('title','')}\n\n"
                                f"SUMMARY:\n{bm.get('summary','')}\n\n"
                                f"KEY TAKEAWAY:\n{bm.get('key_takeaway','')}\n\n"
                                f"PRACTICE IMPACT:\n{bm.get('practice_impact','')}",
                                bm.get("title", ""),
                            ),
                            f"Bookmark_{bm.get('id','x')}_{datetime.now():%Y%m%d}.txt",
                            "text/plain",
                            key=f"bm_dl_{i}", use_container_width=True,
                        )
                    with bm_act2:
                        if st.button("🗑️ Remove", key=f"bm_del_{i}", use_container_width=True):
                            bm_id = bm.get("id")
                            st.session_state["nf_bookmarks"] = [
                                b for b in st.session_state["nf_bookmarks"] if b.get("id") != bm_id
                            ]
                            st.rerun()

            st.markdown("---")
            if st.button("🗑️ Clear All Bookmarks", key="bm_clear_all", use_container_width=True):
                st.session_state["nf_bookmarks"] = []
                st.rerun()

    # ═══════════════════════════════════════════════════
    # TAB 3 — CASE RELEVANCE SCAN
    # ═══════════════════════════════════════════════════
    with tab_scan:
        st.markdown("#### 🎯 Case Relevance Scan")
        st.caption(
            "Paste your case facts below. The AI will scan every item in your current feed "
            "and rank them by relevance to your matter — identifying which developments help, "
            "which hurt, and which raise procedural flags."
        )

        feed_data = st.session_state.get("nf_feed_data", None)
        feed_items = feed_data.get("items", []) if (feed_data and "_raw" not in feed_data) else []

        if not feed_items:
            st.warning("⚠️ Load a news feed first (use the 'Live Feed' tab → Fetch Latest). "
                       "The scanner needs items to check against.")
        else:
            st.info(f"📰 {len(feed_items)} item(s) loaded from feed: **{st.session_state.get('nf_subject_loaded', '')}**")

            scan_facts = st.text_area(
                "Your Case Facts *",
                height=200,
                key="nf_scan_facts_ta",
                placeholder="""Describe your current matter. Example:

Client is a tenant in Lagos who was issued a Notice to Quit in January 2024.
The tenancy is a yearly tenancy at ₦800,000 per annum. Landlord claims breach of
tenancy covenants (subletting). Client denies subletting and has receipts of all rent
paid. Matter is before the Lagos State Rent Tribunal.""",
            )

            scan_btn = st.button(
                "🎯 Scan Feed for Relevance",
                type="primary", use_container_width=True,
                key="nf_scan_btn",
                disabled=not scan_facts.strip(),
            )

            if scan_btn and scan_facts.strip():
                news_text = ""
                for item in feed_items:
                    news_text += (
                        f"\n[Item {item.get('id',0)}] TITLE: {item.get('title','')}\n"
                        f"SUMMARY: {item.get('summary','')}\n"
                        f"TAKEAWAY: {item.get('key_takeaway','')}\n"
                        f"PRACTICE IMPACT: {item.get('practice_impact','')}\n"
                    )

                scan_prompt = NEWS_RELEVANCE_PROMPT.format(
                    case_facts=scan_facts.strip(),
                    news_items=news_text,
                )
                with st.spinner(f"🎯 Scanning {len(feed_items)} items against your case facts…"):
                    raw_scan = generate(scan_prompt, NEWS_RELEVANCE_SYSTEM, "brief", "analysis")

                try:
                    clean_scan = raw_scan.strip().replace("```json", "").replace("```", "").strip()
                    scan_data = json.loads(clean_scan)
                    st.session_state["nf_scan_result"] = scan_data
                except Exception:
                    st.session_state["nf_scan_result"] = {"_raw": raw_scan}
                st.rerun()

            scan_result = st.session_state.get("nf_scan_result", None)

            if scan_result:
                st.markdown("---")

                if "_raw" in scan_result:
                    raw_text = scan_result.get("_raw", "")
                    if raw_text and raw_text.strip():
                        st.warning(
                            "⚠️ Could not parse the scan response as "
                            "structured data. Showing raw AI output below:"
                        )
                        st.markdown(
                            f'<div class="response-box">{esc(raw_text)}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(
                            "⚠️ The AI response came back empty. Please try "
                            "again."
                        )
                else:
                    # Summary banner
                    summary_text = scan_result.get("scan_summary", "")
                    if summary_text:
                        st.markdown(f"""
<div style="background:#f0fdf4;border:2px solid #059669;border-radius:0.75rem;
padding:1rem 1.4rem;margin-bottom:1.2rem;">
  <strong style="color:#059669;">🎯 Scan Summary:</strong>
  <span style="font-size:0.95rem;"> {esc(summary_text)}</span>
</div>""", unsafe_allow_html=True)

                    scan_items = scan_result.get("items", [])
                    # Sort by score descending
                    scan_items = sorted(scan_items, key=lambda x: x.get("relevance_score", 0), reverse=True)

                    for si in scan_items:
                        score = si.get("relevance_score", 0)
                        label = si.get("relevance_label", "")
                        fav = si.get("favourable_or_unfavourable", "NEUTRAL")
                        how = si.get("how_it_affects_case", "")
                        si_title = si.get("title", "")

                        if score >= 7:
                            score_color = "#059669"; bg = "#f0fdf4"; border = "#059669"
                        elif score >= 5:
                            score_color = "#d97706"; bg = "#fffbeb"; border = "#f59e0b"
                        elif score >= 1:
                            score_color = "#64748b"; bg = "#f8fafc"; border = "#cbd5e1"
                        else:
                            score_color = "#94a3b8"; bg = "#f8fafc"; border = "#e2e8f0"

                        fav_icons = {
                            "FAVOURABLE": "🟢 Favourable",
                            "UNFAVOURABLE": "🔴 Unfavourable",
                            "NEUTRAL": "⚪ Neutral",
                            "PROCEDURAL": "🔵 Procedural",
                        }
                        fav_label = fav_icons.get(fav, fav)

                        st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:0.75rem;
padding:1rem 1.2rem;margin-bottom:0.7rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
    <strong style="font-size:0.95rem;">{esc(si_title)}</strong>
    <div style="display:flex;gap:0.5rem;align-items:center;">
      <span style="background:{score_color};color:white;font-weight:700;font-size:0.8rem;
      padding:0.2rem 0.6rem;border-radius:1rem;">{score}/10</span>
      <span style="font-size:0.8rem;color:{score_color};font-weight:600;">{esc(label)}</span>
      <span style="font-size:0.8rem;">{esc(fav_label)}</span>
    </div>
  </div>
  {f'<p style="margin:0;font-size:0.9rem;color:var(--la-text);line-height:1.6;">{esc(how)}</p>' if how else ''}
</div>""", unsafe_allow_html=True)

                    # Export scan report
                    scan_report = f"CASE RELEVANCE SCAN REPORT\nDate: {datetime.now():%d %B %Y at %H:%M}\n\n"
                    scan_report += f"CASE FACTS:\n{st.session_state.get('nf_scan_facts_ta','')}\n\n"
                    scan_report += f"SCAN SUMMARY:\n{summary_text}\n\n"
                    scan_report += "RANKED ITEMS:\n"
                    for si in scan_items:
                        scan_report += (
                            f"\n[Score {si.get('relevance_score',0)}/10 | "
                            f"{si.get('relevance_label','')} | "
                            f"{si.get('favourable_or_unfavourable','')}]\n"
                            f"{si.get('title','')}\n"
                            f"{si.get('how_it_affects_case','')}\n"
                        )

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        st.download_button(
                            "📥 Export Scan Report (TXT)",
                            export_txt(scan_report, "Case Relevance Scan Report"),
                            f"RelevanceScan_{datetime.now():%Y%m%d_%H%M}.txt",
                            "text/plain", key="nf_scan_dl_txt", use_container_width=True,
                        )
                    with sc2:
                        if st.button("🗑️ Clear Scan", key="nf_scan_clear", use_container_width=True):
                            st.session_state["nf_scan_result"] = None
                            st.rerun()

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> Relevance scores are AI-generated assessments.
            Independent legal judgment is required before relying on any matched development.
            Verify all citations against primary sources.
        </div>""", unsafe_allow_html=True)

