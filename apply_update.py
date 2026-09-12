#!/usr/bin/env python3
"""
apply_update.py — Bubblegum Atelier bundle update.

Installs, in one pass:

  SPEED
    1. Swaps the 4 oversized graphics for optimized versions (4.41 MB -> 0.14 MB)
    2. Turns on lazy loading for product photos

  REAL DATA (owner dashboard)
    3. AI Insights are computed from your real event log (no more sample text)
    4. The 4 stat cards open a drill-down panel with the real numbers
       (visits detail, customer list, vision tags, concierge chats)

  FEATURE
    5. Lookbook looks get a like button (one per visitor, toggleable)

Run from the PROJECT ROOT (the folder containing app/ and public/):

    python apply_update.py --check     # dry run - report only
    python apply_update.py             # install (backs up every file it touches)

Backups are written as <name>.pre-update.bak next to each file.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "update_payload"
GRAPHICS = HERE / "graphics_optimized"
BACKUP = ".pre-update.bak"

BACKEND_FILES = [
    "app/main.py",
    "app/routers/insights.py",
    "app/routers/lookbook.py",
    "app/routers/chatbot.py",
    "app/routers/stylewall.py",
    "app/routers/events.py",
    "tests/test_endpoints.py",
]

DATA_FILES = [
    "data/chats.json",
    "data/lookbook_likes.json",
]

GRAPHIC_FILES = ["welcome-hero.jpg", "lookbook-banner.jpg", "empty-bag.jpg", "empty-wishlist.jpg"]

HTML_TARGETS = ["public/index.html", "frontend/index.html"]


# ═══════════════════════════════════════════════════════════════════ new frontend code

DRILLDOWN_JSX = r'''
/* =======================================================================
   OWNER: DRILL-DOWN PANEL — the real numbers behind each stat card
======================================================================= */
const DETAIL_META = {
  visits:    { icon: "bag",   title: "Visit activity",  subtitle: "What shoppers looked at, and when." },
  customers: { icon: "user",  title: "Customers",       subtitle: "Anonymous guest ids browsing your boutique." },
  tagged:    { icon: "photo", title: "Products tagged", subtitle: "Every photo the vision model has read." },
  chats:     { icon: "chat",  title: "Concierge chats", subtitle: "What shoppers asked your concierge." },
};

function MiniBar({ value, max, color = "var(--pink)" }) {
  const pct = max > 0 ? Math.max(3, Math.round((value / max) * 100)) : 3;
  return (
    <div style={{ height: 8, borderRadius: 999, background: "var(--pink-soft)", overflow: "hidden" }}>
      <div style={{ width: pct + "%", height: "100%", borderRadius: 999, background: color, transition: "width 0.4s ease" }} />
    </div>
  );
}

function Row({ left, right, sub }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ minWidth: 0 }}>
        <p style={{ fontSize: 13.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{left}</p>
        {sub && <p style={{ fontSize: 11.5, color: "var(--text-soft)" }}>{sub}</p>}
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, whiteSpace: "nowrap" }}>{right}</span>
    </div>
  );
}

function StatDetailBody({ kind, data }) {
  if (kind === "visits") {
    const maxDay = Math.max(1, ...data.days.map((d) => d.count));
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--pink-soft)", color: "var(--pink-dark)" }}>{data.total} product views</span>
          <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--mint)", color: "#22996F" }}>{data.last_24h} in the last 24h</span>
        </div>

        <div>
          <p style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 10, color: "var(--text-soft)" }}>LAST 7 DAYS</p>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 92 }}>
            {data.days.map((d) => (
              <div key={d.date} style={{ flex: 1, textAlign: "center" }}>
                <div style={{ height: Math.max(6, Math.round((d.count / maxDay) * 70)), background: "var(--pink)", borderRadius: 8, marginBottom: 6, transition: "height 0.4s ease" }} />
                <p style={{ fontSize: 10.5, color: "var(--text-soft)" }}>{d.label}</p>
                <p style={{ fontSize: 10, color: "var(--text-soft)" }}>{d.count}</p>
              </div>
            ))}
          </div>
        </div>

        {data.top_categories.length > 0 && (
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 10, color: "var(--text-soft)" }}>BROWSED BY CATEGORY</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
              {data.top_categories.map((c) => (
                <div key={c.category} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 96, fontSize: 12.5, textTransform: "capitalize" }}>{c.category}</span>
                  <div style={{ flex: 1 }}><MiniBar value={c.views} max={data.top_categories[0].views} /></div>
                  <span style={{ fontSize: 12, fontWeight: 700, width: 34, textAlign: "right" }}>{c.views}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.top_products.length > 0 && (
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 4, color: "var(--text-soft)" }}>MOST-VIEWED PIECES</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {data.top_products.map((p) => (
                <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <img src={API_CONFIG.baseUrl + p.image} alt={p.name} loading="lazy" decoding="async"
                       style={{ width: 42, height: 42, borderRadius: 10, objectFit: "cover", background: "var(--pink-soft)", flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</p>
                    <p style={{ fontSize: 11.5, color: "var(--text-soft)", textTransform: "capitalize" }}>{p.category} · ₹{p.price}</p>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700 }}>{p.views}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (kind === "customers") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--mint)", color: "#22996F" }}>{data.total} people</span>
          <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--lavender)", color: "#8B7CE8" }}>{data.returning} came back</span>
        </div>
        <div>
          {data.customers.map((c) => (
            <Row key={c.id} left={c.label}
                 sub={(c.last_seen ? "Last seen " + timeAgo(c.last_seen) : "No timestamp") + (c.returning ? " · returning" : "")}
                 right={c.events + " actions"} />
          ))}
        </div>
        <p style={{ fontSize: 11.5, color: "var(--text-soft)" }}>
          Guest ids are generated on the shopper's own device - no names, no personal data stored here.
        </p>
      </div>
    );
  }

  if (kind === "tagged") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--lavender)", color: "#8B7CE8", alignSelf: "flex-start" }}>
          {data.total} photos read by the vision model
        </span>

        {data.by_category.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
            {data.by_category.map((c) => (
              <div key={c.category} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 96, fontSize: 12.5, textTransform: "capitalize" }}>{c.category}</span>
                <div style={{ flex: 1 }}><MiniBar value={c.count} max={data.by_category[0].count} color="#8B7CE8" /></div>
                <span style={{ fontSize: 12, fontWeight: 700, width: 34, textAlign: "right" }}>{c.count}</span>
              </div>
            ))}
          </div>
        )}

        {data.recent.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-soft)" }}>
            Nothing tagged yet. Every photo shared on the Style Wall is read by the model - the first one will show up here.
          </p>
        )}

        {data.recent.length > 0 && (
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 6, color: "var(--text-soft)" }}>RECENT</p>
            {data.recent.map((t, i) => (
              <Row key={i}
                   left={(t.category || "unknown") + (t.source === "style_wall" ? " · from the Style Wall" : "")}
                   sub={t.ts ? timeAgo(t.ts) : ""}
                   right={t.confidence != null ? Math.round(t.confidence * 100) + "% sure" : "—"} />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (kind === "chats") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--cream)", color: "var(--text)", alignSelf: "flex-start" }}>
          {data.total} conversations with the concierge
        </span>
        {data.recent.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-soft)" }}>No chats yet - ask the concierge something and it will appear here.</p>
        )}
        {data.recent.map((c, i) => (
          <div key={i} style={{ padding: "12px 14px", background: "var(--cream)", borderRadius: 14 }}>
            <p style={{ fontSize: 13, fontWeight: 700 }}>{c.message}</p>
            <p style={{ fontSize: 12.5, color: "var(--text-soft)", marginTop: 4 }}>{c.reply}</p>
            <p style={{ fontSize: 10.5, color: "var(--text-soft)", marginTop: 6 }}>
              {c.intent ? c.intent + " · " : ""}{c.ts ? timeAgo(c.ts) : ""}
            </p>
          </div>
        ))}
      </div>
    );
  }

  return <p style={{ fontSize: 13, color: "var(--text-soft)" }}>Nothing to show yet.</p>;
}

function StatDetailModal({ kind, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!kind) return;
    setLoading(true); setError(null); setData(null);
    api.insightDetail(kind).then((res) => {
      setLoading(false);
      if (res.ok) setData(res.data);
      else setError(res.message || "Could not load that.");
    });
  }, [kind, nonce]);

  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!kind) return null;
  const meta = DETAIL_META[kind] || { icon: "sparkle", title: "Details", subtitle: "" };

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(47,42,53,0.34)", zIndex: 90, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div onClick={(e) => e.stopPropagation()} className="card fade-up" style={{ width: "min(620px, 100%)", maxHeight: "84vh", overflowY: "auto", padding: 26, background: "#fff" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 18 }}>
          <div style={{ width: 42, height: 42, borderRadius: "50%", background: "var(--pink-soft)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--pink-dark)", flexShrink: 0 }}>
            <Icon name={meta.icon} size={19} />
          </div>
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: 19 }}>{meta.title}</h3>
            <p style={{ fontSize: 12.5, color: "var(--text-soft)" }}>{meta.subtitle}</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close" style={{ padding: "8px 12px" }}>
            <Icon name="x" size={14} />
          </button>
        </div>

        {loading && <LoadingState label="Reading the real data..." />}
        {!loading && error && <ErrorState message={error} onRetry={() => setNonce((n) => n + 1)} />}
        {!loading && !error && data && <StatDetailBody kind={kind} data={data} />}
      </div>
    </div>
  );
}

'''

NEW_STATS_JSX = '''          <div className="grid-3 fade-up" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 22 }}>
            <StatCard icon="bag" label="Total Visits" value={totals.visits} bg="var(--pink-soft)" onClick={() => setDrill("visits")} />
            <StatCard icon="user" label="Unique Customers" value={totals.customers} bg="var(--mint)" onClick={() => setDrill("customers")} />
            <StatCard icon="photo" label="Products Tagged" value={totals.tagged} bg="var(--lavender)" onClick={() => setDrill("tagged")} note="all time" />
            <StatCard icon="chat" label="Concierge Chats" value={totals.chats} bg="var(--cream)" onClick={() => setDrill("chats")} note="all time" />
          </div>'''

NEW_INSIGHTS_JSX = '''              <p style={{ fontSize: 12, color: "var(--text-soft)", marginBottom: 14 }}>
                Computed from {insights ? insights.events_considered : 0} recorded actions in your boutique, refreshed every time this page loads.
              </p>
              {!insights && <p style={{ fontSize: 13, color: "var(--text-soft)" }}>Reading your data...</p>}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {insightCards.map((card, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "12px 14px", background: "var(--cream)", borderRadius: 14 }}>
                    <Icon name={card.icon || "star"} size={14} style={{ color: "var(--pink)", marginTop: 2, flexShrink: 0 }} />
                    <div>
                      <p style={{ fontSize: 13, fontWeight: 700, lineHeight: 1.45 }}>{card.title}</p>
                      <p style={{ fontSize: 12.5, color: "var(--text-soft)", lineHeight: 1.5 }}>{card.text}</p>
                    </div>
                  </div>
                ))}
              </div>'''


def patch_html(path: Path, dry: bool) -> list:
    report = []
    text = path.read_text(encoding="utf-8")
    original = text

    def note(status, what):
        report.append((status, path.name, what))

    def edit(old, new, label, required=True):
        nonlocal text
        if old not in text:
            if new.split("\n")[0].strip() and new.split("\n")[0].strip()[:40] in text:
                note("already", label)
                return
            note("FAILED" if required else "skipped", label)
            return
        text = text.replace(old, new, 1)
        note("added", label)

    # ── 1. graphics: point at the optimized files ───────────────────────────
    for name in ("welcome-hero", "lookbook-banner", "empty-bag", "empty-wishlist"):
        old, new = f'"/static/graphics/{name}.png"', f'"/static/graphics/{name}.jpg"'
        if new in text and old not in text:
            note("already", f"graphics/{name}.jpg")
        elif old in text:
            text = text.replace(old, new)
            note("added", f"graphics/{name}.jpg")

    # ── 2. lazy loading for product photos ──────────────────────────────────
    # (only the product grid images - the zoom-modal image must stay eager,
    #  and the Style Wall photos already carry the attribute)
    out, n, already = [], 0, 0
    for line in text.splitlines(True):
        if ("<img" in line and "src={API_CONFIG.baseUrl + p.image}" in line
                and "transform: zoom" not in line):
            if "loading=" in line:
                already += 1
            else:
                line = line.replace("<img ", '<img loading="lazy" decoding="async" ', 1)
                n += 1
        out.append(line)
    if n:
        text = "".join(out)
        note("added", f"lazy loading ({n} images)")
    else:
        note("already", f"lazy loading ({already} images)")

    # ── 3. new API helpers ──────────────────────────────────────────────────
    api_anchor = '  favRemove: (productId) => apiRequest("/favorites", { method: "DELETE", body: JSON.stringify({ customer: getCustomerId(), product_id: productId }) }),\n'
    api_new = api_anchor + (
        '  insights: () => apiRequest("/insights", { method: "GET" }),\n'
        '  insightDetail: (kind) => apiRequest(`/insights/${kind}`, { method: "GET" }),\n'
        '  lookbookLikes: (customer) => apiRequest(`/lookbook/likes?customer=${encodeURIComponent(customer)}`, { method: "GET" }),\n'
        '  lookbookLike: (lookId, customer) => apiRequest(`/lookbook/${lookId}/like`, { method: "POST", body: JSON.stringify({ customer }) }),\n'
    )
    edit(api_anchor, api_new, "insights + lookbook API calls")

    # ── 4. OverviewPage state ───────────────────────────────────────────────
    edit(
        "  const [reviewMood, setReviewMood] = useState(null);\n",
        "  const [reviewMood, setReviewMood] = useState(null);\n"
        "  const [insights, setInsights] = useState(null);\n"
        "  const [drill, setDrill] = useState(null);\n",
        "dashboard state",
    )

    # ── 5. fetch the insights ───────────────────────────────────────────────
    reviews_effect = """  useEffect(() => {
    api.getReviews().then((res) => {
      if (res.ok) {
        const counts = {};
        res.data.reviews.forEach((r) => { counts[r.sentiment] = (counts[r.sentiment] || 0) + 1; });
        if (Object.keys(counts).length) setReviewMood(counts);
      }
    });
  }, []);
"""
    edit(
        reviews_effect,
        reviews_effect + """  useEffect(() => {
    api.insights().then((res) => { if (res.ok) setInsights(res.data); });
  }, []);
""",
        "fetch real insights",
    )

    # ── 6. drop the sample insights, add real totals ────────────────────────
    sample = '''  const insightCards = [
    "Lipstick reviews are trending positive this week.",
    "Bags remain the most-photographed category in the studio.",
    "Guests recognized at the door tend to browse accessories first.",
    "Playful, story-driven captions get the warmest customer replies.",
  ];
'''
    edit(sample, '''  const totals = (insights && insights.totals) || {
    visits: state.data ? state.data.total_visits : 0,
    customers: state.data ? state.data.unique_customers : 0,
    tagged: session.classifyCount,
    chats: session.chatCount,
  };
  const insightCards = (insights && insights.insights) || [];
''', "real insight cards")

    # ── 7. the four stat cards become clickable ─────────────────────────────
    old_stats = '''            <StatCard icon="bag" label="Total Visits" value={state.data.total_visits || 0} bg="var(--pink-soft)" />
            <StatCard icon="user" label="Unique Customers" value={state.data.unique_customers || 0} bg="var(--mint)" />
            <StatCard icon="photo" label="Products Tagged" value={session.classifyCount} bg="var(--lavender)" note="This session" />
            <StatCard icon="chat" label="Concierge Chats" value={session.chatCount} bg="var(--cream)" note="This session" />'''
    edit(old_stats, NEW_STATS_JSX, "clickable stat cards")

    # ── 8. insights panel renders the real cards ────────────────────────────
    old_ins = '''              <p style={{ fontSize: 12, color: "var(--text-soft)", marginBottom: 14 }}>Illustrative observations - a preview of what deeper analysis could surface.</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {insightCards.map((t, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "12px 14px", background: "var(--cream)", borderRadius: 14 }}>
                    <Icon name="star" size={14} style={{ color: "var(--pink)", marginTop: 2, flexShrink: 0 }} />
                    <p style={{ fontSize: 13, lineHeight: 1.5 }}>{t}</p>
                  </div>
                ))}
              </div>'''
    edit(old_ins, NEW_INSIGHTS_JSX, "insights panel")

    # ── 9. mount the drill-down + upgrade StatCard ──────────────────────────
    tail = '''        </>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, bg, note }) {
  return (
    <div className="card" style={{ padding: "20px 20px" }}>
      <div style={{ width: 38, height: 38, borderRadius: "50%", background: bg, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--pink-dark)", marginBottom: 14 }}>
        <Icon name={icon} size={17} />
      </div>
      <p style={{ fontSize: 26, fontFamily: "'Playfair Display', serif", fontWeight: 700 }}><StatNumber value={value} /></p>
      <p style={{ fontSize: 12.5, color: "var(--text-soft)", fontWeight: 500 }}>{label}{note && <span style={{ marginLeft: 6, fontSize: 10.5, color: "var(--pink-dark)", background: "var(--pink-soft)", padding: "2px 7px", borderRadius: 999 }}>{note}</span>}</p>
    </div>
  );
}'''
    new_tail = '''        </>
      )}

      {drill && <StatDetailModal kind={drill} onClose={() => setDrill(null)} />}
    </div>
  );
}

function StatCard({ icon, label, value, bg, note, onClick }) {
  return (
    <div className="card" onClick={onClick}
         title={onClick ? "Open the real numbers" : undefined}
         style={{ padding: "20px 20px", cursor: onClick ? "pointer" : "default", transition: "transform 0.18s ease, box-shadow 0.18s ease" }}
         onMouseEnter={(e) => { if (onClick) { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "var(--shadow-lift)"; } }}
         onMouseLeave={(e) => { if (onClick) { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "var(--shadow)"; } }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ width: 38, height: 38, borderRadius: "50%", background: bg, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--pink-dark)", marginBottom: 14 }}>
          <Icon name={icon} size={17} />
        </div>
        {onClick && <span style={{ color: "var(--text-soft)", opacity: 0.65, marginTop: 8 }}><Icon name="chevron" size={15} /></span>}
      </div>
      <p style={{ fontSize: 26, fontFamily: "'Playfair Display', serif", fontWeight: 700 }}><StatNumber value={value} /></p>
      <p style={{ fontSize: 12.5, color: "var(--text-soft)", fontWeight: 500 }}>{label}{note && <span style={{ marginLeft: 6, fontSize: 10.5, color: "var(--pink-dark)", background: "var(--pink-soft)", padding: "2px 7px", borderRadius: 999 }}>{note}</span>}</p>
    </div>
  );
}'''
    edit(tail, new_tail, "drill-down panel + clickable cards")

    # ── 10. Lookbook: likes ─────────────────────────────────────────────────
    edit(
        """function LookbookPage({ cart, setCart }) {
  const [products, setProducts] = useState([]);
  const [addedLook, setAddedLook] = useState(null);
""",
        """function LookbookPage({ cart, setCart }) {
  const [products, setProducts] = useState([]);
  const [addedLook, setAddedLook] = useState(null);
  const [likes, setLikes] = useState({});

  useEffect(() => {
    api.lookbookLikes(getCustomerId()).then((res) => { if (res.ok) setLikes(res.data.looks || {}); });
  }, []);

  function liked(lookId) { return Boolean(likes[lookId] && likes[lookId].liked); }

  function likeCount(lookId) { return (likes[lookId] && likes[lookId].count) || 0; }

  function toggleLike(look) {
    api.lookbookLike(look.id, getCustomerId()).then((res) => {
      if (!res.ok) return;
      setLikes((prev) => ({ ...prev, [look.id]: { count: res.data.like_count, liked: res.data.liked } }));
      logEvent("look_like", null, { look_id: look.id, liked: res.data.liked });
    });
  }
""",
        "lookbook like state",
    )

    edit(
        """                <button className="btn btn-sm" onClick={() => addLook(look)} style={{ minWidth: 150 }}>
                  {addedLook === look.id ? "Added to your bag!" : "Add whole look"}
                </button>""",
        """                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => toggleLike(look)}
                          title={liked(look.id) ? "Take back your like" : "Like this look"}
                          aria-label="Like this look"
                          style={{ padding: "9px 15px", background: liked(look.id) ? "var(--pink-soft)" : "#fff" }}>
                    <Icon name="heart" size={14} fill={liked(look.id) ? "var(--pink-dark)" : "none"}
                          style={{ color: liked(look.id) ? "var(--pink-dark)" : "currentColor" }} />
                    {likeCount(look.id)}
                  </button>
                  <button className="btn btn-sm" onClick={() => addLook(look)} style={{ minWidth: 150 }}>
                    {addedLook === look.id ? "Added to your bag!" : "Add whole look"}
                  </button>
                </div>""",
        "lookbook like button",
    )

    # ── 11. drop the drill-down component in ────────────────────────────────
    app_anchor = "\nfunction App() {"
    if "function StatDetailModal(" in text:
        note("already", "drill-down component")
    elif app_anchor in text:
        text = text.replace(app_anchor, DRILLDOWN_JSX + "\nfunction App() {", 1)
        note("added", "drill-down component")

    if text == original:
        note("--", "no changes needed")
        return report

    if dry:
        note("WOULD WRITE", f"{len(text) - len(original):+d} characters")
        return report

    shutil.copy2(path, Path(str(path) + BACKUP))
    path.write_text(text, encoding="utf-8")
    note("written", f"{len(text) - len(original):+d} characters, backup saved")
    return report


# ═══════════════════════════════════════════════════════════════════ main

def main() -> int:
    ap = argparse.ArgumentParser(description="Install the dashboard + speed update.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    ap.add_argument("--check", action="store_true", help="dry run - report only")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    dry = args.check

    problems = []
    if not (root / "app").is_dir():
        problems.append("no app/ folder here")
    if not (root / "public" / "index.html").exists() and not (root / "frontend" / "index.html").exists():
        problems.append("no public/index.html or frontend/index.html")
    if not PAYLOAD.is_dir():
        problems.append(f"update_payload/ folder is missing next to this script ({PAYLOAD})")
    if problems:
        print("Cannot install from here:")
        for p in problems:
            print(f"  - {p}")
        print(f"\nResolved project root: {root}")
        return 2

    print(f"Project root : {root}")
    print(f"Mode         : {'DRY RUN' if dry else 'INSTALL'}\n")

    print("Backend files")
    for rel in BACKEND_FILES:
        src, dst = PAYLOAD / rel, root / rel
        if not src.exists():
            print(f"  SKIP         {rel:<38} not in the update")
            continue
        if dry:
            print(f"  WOULD COPY   {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.copy2(dst, Path(str(dst) + BACKUP))
        shutil.copy2(src, dst)
        print(f"  copied       {rel:<38} backup written" if dst.exists() else f"  copied       {rel}")

    print("\nNew data files (only created if missing - your data is never overwritten)")
    for rel in DATA_FILES:
        src, dst = PAYLOAD / rel, root / rel
        if dst.exists():
            print(f"  kept         {rel:<38} already exists")
            continue
        if dry:
            print(f"  WOULD CREATE {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  created      {rel}")

    print("\nGraphics (the speed fix)")
    for name in GRAPHIC_FILES:
        src = GRAPHICS / name
        dst = root / "data" / "graphics" / name
        if not src.exists():
            print(f"  SKIP         {name:<38} not in the update")
            continue
        if dry:
            print(f"  WOULD COPY   data/graphics/{name}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  copied       data/graphics/{name:<25} {src.stat().st_size // 1024} KB")

    print("\nFrontend files")
    for rel in HTML_TARGETS:
        target = root / rel
        if not target.exists():
            print(f"  not found    {rel}")
            continue
        for status, name, extra in patch_html(target, dry):
            print(f"  {status:<12} {rel:<18} {extra}")

    if not dry:
        print("\nDone. Next:")
        print("  1. pytest tests/ -v          (expect 27 passed)")
        print("  2. uvicorn app.main:app --reload --port 8000")
        print("  3. open the storefront locally and click the stat cards")
        print("\nAnything you changed by mistake has a .pre-update.bak copy next to it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
