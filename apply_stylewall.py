#!/usr/bin/env python3
"""
apply_stylewall.py — installs the Style Wall update into Bubblegum Atelier.

Does three things, all with backups:

  1. Copies the new/updated backend files from ./stylewall_payload/ into place
  2. Patches public/index.html and frontend/index.html:
       - removes the Customer Memory page (and its API calls)
       - adds the Style Wall page: photo upload, star rating, cheer, comments
  3. Removes the Customer Memory model files (face LBPH, haar cascade, visits log)

Run from the PROJECT ROOT (the folder that contains app/ and public/):

    python apply_stylewall.py                 # full install
    python apply_stylewall.py --check         # dry run: report only, change nothing
    python apply_stylewall.py --keep-memory   # don't delete the face model files

Every file it touches is copied to <name>.pre-stylewall.bak first.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent / "stylewall_payload"
BACKUP_SUFFIX = ".pre-stylewall.bak"

# Files that belong to Customer Memory and are removed from the repo
MEMORY_FILES = [
    "app/models/face_db.pkl",
    "app/models/face_lbph.yml",
    "app/models/haarcascade_frontalface_default.xml",
    "data/customer_visits.csv",
    "data/funnel.db",
]

# --------------------------------------------------------------------------- payload copy

BACKEND_FILES = [
    "app/main.py",
    "app/routers/stylewall.py",
    "app/routers/vision.py",
    "app/routers/events.py",
    "app/services/cv_service.py",
    "tests/test_endpoints.py",
]


def copy_backend(root: Path, dry: bool) -> list:
    report = []
    for rel in BACKEND_FILES:
        src = PAYLOAD / rel
        dst = root / rel
        if not src.exists():
            report.append(("SKIP", rel, "not in payload"))
            continue
        if dry:
            report.append(("WOULD COPY", rel, f"{src} -> {dst}"))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.copy2(dst, dst.with_suffix(dst.suffix + BACKUP_SUFFIX))
        shutil.copy2(src, dst)
        report.append(("copied", rel, "backup written"))
    return report


def remove_memory_files(root: Path, dry: bool, keep: bool) -> list:
    report = []
    if keep:
        return [("KEPT", f, "memory files left in place (--keep-memory)") for f in MEMORY_FILES]
    for rel in MEMORY_FILES:
        path = root / rel
        if not path.exists():
            report.append(("gone", rel, "already absent"))
            continue
        if dry:
            report.append(("WOULD DELETE", rel, ""))
            continue
        try:
            path.unlink()
            report.append(("deleted", rel, ""))
        except OSError as exc:
            report.append(("FAILED", rel, str(exc)))
    return report


# --------------------------------------------------------------------------- html patching

STYLEWALL_PAGE_JSX = r'''
/* =======================================================================
   PAGE: STYLE WALL (shoppers share what they bought)
======================================================================= */
const WALL_SENTIMENT = {
  positive: { label: "Loved It", color: "#EC4899" },
  neutral: { label: "Mixed Feelings", color: "#8B7CE8" },
  negative: { label: "Needs Love", color: "#22996F" },
};

function timeAgo(iso) {
  if (!iso) return "";
  const stamp = iso.includes("Z") || iso.includes("+") ? iso : iso + "Z";
  const then = new Date(stamp).getTime();
  if (isNaN(then)) return "";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hours = Math.round(mins / 60);
  if (hours < 24) return hours + "h ago";
  const days = Math.round(hours / 24);
  if (days < 30) return days + "d ago";
  return new Date(then).toLocaleDateString();
}

function wallMood(post) {
  const s = post.sentiment;
  if (!s || !WALL_SENTIMENT[s.sentiment]) return null;
  if ((s.confidence || 0) < 0.5) return null;               // too unsure to show a label
  const r = post.rating || 0;
  if (r >= 4 && s.sentiment === "negative") return null;    // never contradict the stars
  if (r <= 2 && s.sentiment === "positive") return null;
  return WALL_SENTIMENT[s.sentiment];
}

function StarRow({ value, size = 15, onChange }) {
  return (
    <span style={{ display: "inline-flex", gap: 2 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i}
              onClick={onChange ? () => onChange(i) : undefined}
              style={{ cursor: onChange ? "pointer" : "default", lineHeight: 0 }}>
          <Icon name="star" size={size} fill={i <= value ? "#FFB020" : "none"}
                style={{ color: i <= value ? "#FFB020" : "var(--text-soft)" }} />
        </span>
      ))}
    </span>
  );
}

function StyleWallPage({ profile }) {
  const [state, setState] = useState({ loading: true, error: null, posts: [] });
  const [draft, setDraft] = useState({ rating: 5, caption: "", productId: "" });
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [posting, setPosting] = useState(false);
  const [notice, setNotice] = useState("");
  const [products, setProducts] = useState([]);
  const [openComments, setOpenComments] = useState({});
  const [commentDrafts, setCommentDrafts] = useState({});
  const fileRef = useRef(null);

  const me = getCustomerId();
  const myName = (profile && profile.name) || "A guest";

  const load = useCallback(() => {
    setState({ loading: true, error: null, posts: [] });
    api.stylewallList(me).then((res) => {
      if (res.ok) setState({ loading: false, error: null, posts: res.data.posts || [] });
      else setState({ loading: false, error: res.message, posts: [] });
    });
  }, [me]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    api.getProducts().then((res) => { if (res.ok) setProducts(res.data.products || []); });
  }, []);

  function pickPhoto(file) {
    if (!file) return;
    setPhoto(file);
    setPreview(URL.createObjectURL(file));
    setNotice("");
  }

  function share() {
    if (!photo) { setNotice("Add a photo of your piece first"); return; }
    setPosting(true);
    setNotice("");
    api.stylewallCreate({
      photo, rating: draft.rating, caption: draft.caption, customer: myName, productId: draft.productId,
    }).then((res) => {
      setPosting(false);
      if (!res.ok) { setNotice(res.message || "Couldn't share that just now."); return; }
      setState((s) => ({ ...s, posts: [res.data, ...s.posts] }));
      setPhoto(null);
      setPreview(null);
      setDraft({ rating: 5, caption: "", productId: "" });
      if (fileRef.current) fileRef.current.value = "";
      setNotice("Shared! Your look is on the wall");
      logEvent("wall_post", draft.productId || null, { rating: draft.rating });
    });
  }

  function cheer(post) {
    api.stylewallCheer(post.id, me).then((res) => {
      if (!res.ok) return;
      setState((s) => ({
        ...s,
        posts: s.posts.map((p) =>
          p.id === post.id ? { ...p, cheered: res.data.cheered, cheer_count: res.data.cheer_count } : p),
      }));
      if (res.data.cheered) logEvent("wall_cheer", post.product_id || null);
    });
  }

  function addComment(post) {
    const text = (commentDrafts[post.id] || "").trim();
    if (!text) return;
    api.stylewallComment(post.id, myName, text).then((res) => {
      if (!res.ok) { setNotice(res.message || "That comment didn't go through."); return; }
      setState((s) => ({
        ...s,
        posts: s.posts.map((p) => p.id === post.id
          ? { ...p, comments: [...(p.comments || []), res.data], comment_count: (p.comment_count || 0) + 1 }
          : p),
      }));
      setCommentDrafts((d) => ({ ...d, [post.id]: "" }));
      logEvent("wall_comment", post.product_id || null);
    });
  }

  const totalCheers = state.posts.reduce((n, p) => n + (p.cheer_count || 0), 0);
  const rated = state.posts.filter((p) => p.rating);
  const average = rated.length ? (rated.reduce((n, p) => n + p.rating, 0) / rated.length) : null;

  return (
    <div>
      <PageHeader icon="camera" title="Style Wall"
                  subtitle="Looks from our shoppers - add yours, cheer the ones you love, leave a note." />

      {/* ---------------- composer ---------------- */}
      <div className="card fade-up" style={{ padding: 20, marginBottom: 22 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ width: 42, height: 42, borderRadius: "50%", background: "var(--pink-soft)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--pink-dark)", flexShrink: 0 }}>
            <Icon name="camera" size={19} />
          </div>
          <div>
            <p style={{ fontWeight: 700, fontSize: 15 }}>Share your look</p>
            <p style={{ fontSize: 12.5, color: "var(--text-soft)" }}>
              Snap what you bought - the studio reads the photo and the mood for you.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div onClick={() => fileRef.current && fileRef.current.click()}
               title="Add a photo"
               style={{ width: 132, height: 132, borderRadius: 18, border: "1.5px dashed var(--pink-soft)", background: preview ? "transparent" : "var(--cream)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", overflow: "hidden", flexShrink: 0 }}>
            {preview
              ? <img src={preview} alt="your look" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              : <span style={{ textAlign: "center", color: "var(--pink-dark)", fontSize: 12, fontWeight: 600 }}>
                  <Icon name="image" size={22} />
                  <br />Add photo
                </span>}
          </div>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
                 onChange={(e) => pickPhoto(e.target.files[0])} />

          <div style={{ flex: 1, minWidth: 240, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12.5, color: "var(--text-soft)", fontWeight: 600 }}>Your rating</span>
              <StarRow value={draft.rating} size={20} onChange={(r) => setDraft((d) => ({ ...d, rating: r }))} />
            </div>
            <input value={draft.caption}
                   onChange={(e) => setDraft((d) => ({ ...d, caption: e.target.value }))}
                   placeholder="Say a few words about it..."
                   style={{ padding: "11px 16px", borderRadius: 999, border: "1px solid var(--border)", fontSize: 13.5, fontFamily: "inherit", outline: "none", background: "#fff" }} />
            <select value={draft.productId}
                    onChange={(e) => setDraft((d) => ({ ...d, productId: e.target.value }))}
                    style={{ padding: "11px 16px", borderRadius: 999, border: "1px solid var(--border)", fontSize: 13.5, fontFamily: "inherit", outline: "none", background: "#fff", color: draft.productId ? "var(--text)" : "var(--text-soft)" }}>
              <option value="">Which piece? (optional)</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <button className="btn btn-sm" onClick={share} disabled={posting}>
                {posting ? "Sharing..." : "Share to the wall"}
              </button>
              {notice && (
                <span style={{ fontSize: 12.5, fontWeight: 600, color: notice.startsWith("Shared") ? "#22996F" : "var(--pink-dark)" }}>
                  {notice}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- wall ---------------- */}
      {state.loading && <LoadingState label="Opening the wall..." />}
      {state.error && !state.loading && <ErrorState message={state.error} onRetry={load} />}

      {!state.loading && !state.error && (
        <>
          {state.posts.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
              <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--pink-soft)", color: "var(--pink-dark)" }}>
                {state.posts.length} {state.posts.length === 1 ? "look" : "looks"} shared
              </span>
              {average !== null && (
                <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--cream)", color: "var(--text)" }}>
                  {average.toFixed(1)} average rating
                </span>
              )}
              {totalCheers > 0 && (
                <span style={{ fontSize: 12, fontWeight: 700, padding: "6px 13px", borderRadius: 999, background: "var(--lavender)", color: "#8B7CE8" }}>
                  {totalCheers} cheers
                </span>
              )}
            </div>
          )}

          {state.posts.length === 0 && (
            <div className="card">
              <EmptyState icon="camera" title="The wall is waiting for its first look"
                          subtitle="Be the first to share a piece you bought - your photo goes up right away." />
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 18 }}>
            {state.posts.map((post) => (
              <article key={post.id} className="card fade-up" style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <div style={{ position: "relative", background: "var(--pink-soft)" }}>
                  <img src={API_CONFIG.baseUrl + post.photo_url}
                       alt={post.caption || "Shared look"}
                       loading="lazy" decoding="async"
                       style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "cover", display: "block" }} />
                  {post.cv_tag && post.cv_tag.category && (
                    <span style={{ position: "absolute", left: 10, bottom: 10, display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.94)", color: "var(--text)", fontSize: 11.5, fontWeight: 700, padding: "5px 11px", borderRadius: 999, boxShadow: "var(--shadow)" }}>
                      <Icon name="sparkle" size={12} />
                      Recognized: {post.cv_tag.category}
                    </span>
                  )}
                </div>

                <div style={{ padding: "14px 16px 16px", display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                      <span style={{ width: 26, height: 26, borderRadius: "50%", background: "var(--pink-soft)", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "var(--pink-dark)", flexShrink: 0 }}>
                        <Icon name="user" size={14} />
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {post.customer}
                      </span>
                    </div>
                    <span style={{ fontSize: 11.5, color: "var(--text-soft)", whiteSpace: "nowrap" }}>{timeAgo(post.timestamp)}</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <StarRow value={post.rating || 0} />
                    {wallMood(post) && (
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "var(--lavender)", color: wallMood(post).color }}>
                        {wallMood(post).label}
                      </span>
                    )}
                  </div>

                  {post.caption && <p style={{ fontSize: 13.5, lineHeight: 1.5 }}>{post.caption}</p>}

                  <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: 10, paddingTop: 4 }}>
                    <button onClick={() => cheer(post)} className="btn btn-ghost btn-sm"
                            title={post.cheered ? "Take back your cheer" : "Cheer this look"}
                            aria-label={post.cheered ? "Take back your cheer" : "Cheer this look"}
                            style={{ padding: "7px 15px", background: post.cheered ? "var(--pink-soft)" : "#fff" }}>
                      <Icon name="heart" size={14} fill={post.cheered ? "var(--pink-dark)" : "none"}
                            style={{ color: post.cheered ? "var(--pink-dark)" : "currentColor" }} />
                      {post.cheer_count || 0}
                    </button>
                    <button onClick={() => setOpenComments((o) => ({ ...o, [post.id]: !o[post.id] }))}
                            className="btn btn-ghost btn-sm" style={{ padding: "7px 15px" }}
                            title={openComments[post.id] ? "Hide comments" : "Show comments"}
                            aria-label="Comments">
                      <Icon name="chat" size={14} />
                      {post.comment_count || 0}
                    </button>
                  </div>

                  {openComments[post.id] && (
                    <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, display: "flex", flexDirection: "column", gap: 9 }}>
                      {(post.comments || []).map((c) => (
                        <div key={c.id} style={{ fontSize: 12.5, lineHeight: 1.45 }}>
                          <span style={{ fontWeight: 700 }}>{c.customer}</span>{" "}
                          <span style={{ color: "var(--text-soft)", fontSize: 11 }}>{timeAgo(c.timestamp)}</span>
                          <p style={{ color: "var(--text)" }}>{c.text}</p>
                        </div>
                      ))}
                      {!(post.comments || []).length && (
                        <p style={{ fontSize: 12.5, color: "var(--text-soft)" }}>No comments yet - say something kind.</p>
                      )}
                      <div style={{ display: "flex", gap: 8 }}>
                        <input value={commentDrafts[post.id] || ""}
                               onChange={(e) => setCommentDrafts((d) => ({ ...d, [post.id]: e.target.value }))}
                               onKeyDown={(e) => { if (e.key === "Enter") addComment(post); }}
                               placeholder="Add a comment..."
                               style={{ flex: 1, minWidth: 0, padding: "10px 14px", borderRadius: 999, border: "1px solid var(--border)", fontSize: 13, fontFamily: "inherit", outline: "none" }} />
                        <button className="btn btn-sm" onClick={() => addComment(post)} title="Post comment"
                                style={{ padding: "10px 14px" }}>
                          <Icon name="send" size={14} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

'''


def patch_html(path: Path, dry: bool) -> list:
    """Apply every Style Wall edit to one HTML file. Returns a report list."""
    report = []
    text = path.read_text(encoding="utf-8")
    original = text

    def note(status, what):
        report.append((status, path.name, what))

    # ---- 1. remove the Customer Memory page ------------------------------------
    memory_block = re.compile(
        r"/\* ={10,}\n   PAGE: CUSTOMER MEMORY.*?\n(/\* ={10,}\n   PAGE: AI INSIGHTS)",
        re.S,
    )
    if "PAGE: CUSTOMER MEMORY" in text:
        text, n = memory_block.subn(r"\1", text)
        note("removed", f"Customer Memory page ({n} block)" if n else "Customer Memory page NOT MATCHED")
    else:
        note("gone", "Customer Memory page already absent")

    # ---- 2. remove the face API calls ------------------------------------------
    face_api = re.compile(
        r"\n  registerFace: \(name, files\) => \{.*?\n  \},\n  recognizeFace: \(file\) => \{.*?\n  \},",
        re.S,
    )
    if "registerFace" in text:
        text, n = face_api.subn("", text)
        note("removed", f"api.registerFace / api.recognizeFace ({n})")
    else:
        note("gone", "face API calls already absent")

    # ---- 3. drop the memory route line -----------------------------------------
    route = '          {page === "memory" && <CustomerMemoryPage />}\n'
    if route in text:
        text = text.replace(route, "")
        note("removed", "memory route")

    # ---- 4. new API calls ------------------------------------------------------
    api_anchor = "  favRemove: (productId) => apiRequest(\"/favorites\", { method: \"DELETE\", body: JSON.stringify({ customer: getCustomerId(), product_id: productId }) }),\n"
    api_add = (
        "  stylewallList: (customer) => apiRequest(`/stylewall/posts${customer ? `?customer=${encodeURIComponent(customer)}` : \"\"}`, { method: \"GET\" }),\n"
        "  stylewallCreate: ({ photo, rating, caption, customer, productId }) => {\n"
        "    const fd = new FormData();\n"
        "    fd.append(\"photo\", photo);\n"
        "    fd.append(\"rating\", String(rating));\n"
        "    fd.append(\"caption\", caption || \"\");\n"
        "    fd.append(\"customer\", customer || \"\");\n"
        "    if (productId) fd.append(\"product_id\", productId);\n"
        "    return apiRequest(\"/stylewall/posts\", { method: \"POST\", body: fd, isForm: true });\n"
        "  },\n"
        "  stylewallCheer: (postId, customer) => apiRequest(`/stylewall/posts/${postId}/cheer`, { method: \"POST\", body: JSON.stringify({ customer }) }),\n"
        "  stylewallComment: (postId, customer, text) => apiRequest(`/stylewall/posts/${postId}/comments`, { method: \"POST\", body: JSON.stringify({ customer, text }) }),\n"
    )
    if "stylewallList" in text:
        note("gone", "Style Wall API calls already present")
    elif api_anchor in text:
        text = text.replace(api_anchor, api_anchor + api_add, 1)
        note("added", "4 Style Wall API calls")
    else:
        note("FAILED", "could not find the api object anchor")

    # ---- 5. nicer error messages (show FastAPI's detail field) ------------------
    old_err = "{ ok: false, status: res.status, message: (data && data.message) || `Something went wrong (${res.status}). Please try again.`, data }"
    new_err = "{ ok: false, status: res.status, message: (data && (data.message || data.detail)) || `Something went wrong (${res.status}). Please try again.`, data }"
    if new_err in text:
        note("gone", "error detail already handled")
    elif old_err in text:
        text = text.replace(old_err, new_err, 1)
        note("added", "server detail in error messages")

    # ---- 6. nav item -----------------------------------------------------------
    nav_anchor = '  { id: "concierge", label: "Concierge", icon: "chat" },\n'
    nav_add = '  { id: "wall", label: "Style Wall", icon: "camera" },\n'
    if '"wall"' in text and "Style Wall" in text:
        note("gone", "nav item already present")
    elif nav_anchor in text:
        text = text.replace(nav_anchor, nav_anchor + nav_add, 1)
        note("added", "nav item")
    else:
        note("FAILED", "could not find NAV_ITEMS anchor")

    # ---- 7. make it visible for shoppers + owners ------------------------------
    shopper_old = 'const shopperNav = ["shop", "foryou", "wishlist", "lookbook", "cart", "concierge"];'
    shopper_new = 'const shopperNav = ["shop", "wall", "foryou", "wishlist", "lookbook", "cart", "concierge"];'
    if shopper_new in text:
        note("gone", "shopper nav already updated")
    elif shopper_old in text:
        text = text.replace(shopper_old, shopper_new, 1)
        note("added", "Style Wall in shopper nav")
    else:
        note("FAILED", "could not find shopperNav")

    owner_old = 'const ownerNav = ["overview", "mood", "shop"];'
    owner_new = 'const ownerNav = ["overview", "mood", "wall", "shop"];'
    if owner_new in text:
        note("gone", "owner nav already updated")
    elif owner_old in text:
        text = text.replace(owner_old, owner_new, 1)
        note("added", "Style Wall in owner nav")
    else:
        note("FAILED", "could not find ownerNav")

    # ---- 8. the page component -------------------------------------------------
    app_anchor = "\nfunction App() {"
    if "function StyleWallPage(" in text:
        note("gone", "StyleWallPage already defined")
    elif app_anchor in text:
        text = text.replace(app_anchor, STYLEWALL_PAGE_JSX + "\nfunction App() {", 1)
        note("added", "StyleWallPage component")
    else:
        note("FAILED", "could not find the App() anchor")

    # ---- 9. the route ----------------------------------------------------------
    route_anchor = '          {page === "lookbook" && <LookbookPage cart={cart} setCart={setCart} />}\n'
    route_add = '          {page === "wall" && <StyleWallPage profile={profile} />}\n'
    if 'page === "wall"' in text:
        note("gone", "wall route already present")
    elif route_anchor in text:
        text = text.replace(route_anchor, route_anchor + route_add, 1)
        note("added", "wall route")
    else:
        note("FAILED", "could not find the page router anchor")

    if text == original:
        note("--", "no changes needed")
        return report

    if dry:
        note("WOULD WRITE", f"{len(text) - len(original):+d} characters")
        return report

    shutil.copy2(path, Path(str(path) + BACKUP_SUFFIX))
    path.write_text(text, encoding="utf-8")
    note("written", f"{len(text) - len(original):+d} characters, backup saved")
    return report


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Install the Style Wall update.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    ap.add_argument("--check", action="store_true", help="dry run - report only")
    ap.add_argument("--keep-memory", action="store_true", help="keep the face model files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    dry = args.check

    problems = []
    if not (root / "app").is_dir():
        problems.append("no app/ folder here")
    if not (root / "public" / "index.html").exists() and not (root / "frontend" / "index.html").exists():
        problems.append("no public/index.html or frontend/index.html")
    if not PAYLOAD.is_dir():
        problems.append(f"payload folder missing next to this script: {PAYLOAD}")
    if problems:
        print("Cannot install from here:")
        for p in problems:
            print(f"  - {p}")
        print(f"\nResolved project root: {root}")
        return 2

    print(f"Project root : {root}")
    print(f"Mode         : {'DRY RUN' if dry else 'INSTALL'}\n")

    print("Backend files")
    for status, name, extra in copy_backend(root, dry):
        print(f"  {status:<12} {name:<34} {extra}")

    print("\nFrontend files")
    for target in (root / "public" / "index.html", root / "frontend" / "index.html"):
        if not target.exists():
            print(f"  not found    {target}")
            continue
        for status, name, extra in patch_html(target, dry):
            print(f"  {status:<12} {name:<18} {extra}")

    print("\nCustomer Memory files")
    for status, name, extra in remove_memory_files(root, dry, args.keep_memory):
        print(f"  {status:<12} {name:<46} {extra}")

    if not dry:
        print("\nDone. Next:")
        print("  1. pytest tests/ -v                      (expect 17 passed)")
        print("  2. uvicorn app.main:app --reload         (try /docs -> Style Wall)")
        print("  3. open public/index.html via Live Server and sign in")
        print("\nIf it's tracked in git, untrack the removed files too:")
        print("  git rm --cached app/models/face_db.pkl app/models/face_lbph.yml \\")
        print("                 app/models/haarcascade_frontalface_default.xml data/customer_visits.csv")
        print("\nChanged a file by mistake? Every overwritten file has a .pre-stylewall.bak copy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
