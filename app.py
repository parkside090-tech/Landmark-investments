"""
Landmark Retail Group · Customer Intelligence dashboard
=======================================================
Run:   pip install -r requirements.txt      then      streamlit run app.py

Data:  put `landmark_outputs.zip` (downloaded by the last cell of the Colab notebook) next to this file.
       It is unzipped automatically into `outputs/`. The app only reads CSV/JSON outputs; it never refits a
       model, so every number here is exactly what the notebook computed.
"""
import os

import streamlit as st

st.set_page_config(page_title="Landmark · Customer Intelligence", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

_ver = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
if _ver < (1, 66):
    st.error(f"This dashboard needs Streamlit 1.66 or newer; you have {st.__version__}. In a terminal, run "
             "`pip install -U streamlit` and then `streamlit run app.py` again.")
    st.stop()

from lmk import data, ui                                                          # noqa: E402
from lmk.theme import (STATUS, STATUS_X, STATUS_GLYPH, STATUS_RULE, SEG_ORDER, BANNERS, BANNERS_X,   # noqa: E402
                       VIVA_STATUS, inject_css)
from lmk.pages import (overview, segments, retention, value, routing, bundles,   # noqa: E402
                       member, models, method, campaign)

inject_css()

folder = data.find_outputs()
if folder is None:
    st.title("Landmark · Customer Intelligence")
    st.error("No data found. Put **landmark_outputs.zip** (downloaded by the last cell of the Colab notebook) in the "
             "same folder as `app.py`, then refresh this page.")
    st.stop()

D0 = data.load(folder, os.path.getmtime(os.path.join(folder, "customer_view.csv")))
st.session_state.setdefault("f_link", st.query_params.get("link") == "1")      # ?link=1 opens with the Explorer on

# ── Identity Link Explorer (what-if switch, top of the sidebar) ─────────────────────────────
with st.sidebar:
    st.toggle("Identity Link Explorer", key="f_link",
              help="Adds Viva Rewards purchases to Shukran members whose card numbers share the same last four digits.")
    st.markdown(
        '<div class="lmk-callout link">⚠ <b>What-if view.</b> This pairs Viva Rewards and Shukran cards that share the same last '
        'four digits (VR50<b>0123</b> ↔ SHK10<b>0123</b>). We tested this pairing and the paired members look no more alike than '
        'random pairs, so it is probably not the same people. Use it to see how much the answers <i>would</i> change if Viva '
        'could be linked, not as fact. Anonymous Viva baskets (35% of Viva spend) are never included.</div>',
        unsafe_allow_html=True)
LINK = bool(st.session_state.f_link)
D = dict(D0)
if LINK:                                   # swap in the linked member table, transactions and baskets
    D.update(M=D0["link"]["M"], tx=D0["link"]["tx"], baskets=D0["link"]["baskets"])
M_all = D["M"]
STATUSES = STATUS_X if LINK else STATUS
# keep filter values valid when the switch changes what exists
if not LINK and st.session_state.get("f_status"):
    st.session_state.f_status = [s for s in st.session_state.f_status if s != VIVA_STATUS]
max_spend = data.init_state(M_all)
prev = st.session_state.get("_max_spend")
lo_, hi_ = st.session_state.f_spend
if prev is not None and prev != max_spend:
    st.session_state.f_spend = (min(lo_, max_spend), max_spend if hi_ >= prev else min(hi_, max_spend))
st.session_state["_max_spend"] = max_spend

# ── global filters (sidebar) ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("#### Global filters")
    st.caption("These apply to every page. Clicking a segment, status or emirate in a chart sets the filter for you.")
    st.pills("Segment", SEG_ORDER, selection_mode="multi", key="f_seg")
    st.pills("Member status", STATUSES, selection_mode="multi", key="f_status",
             format_func=lambda s: f"{STATUS_GLYPH[s]} {s}",
             help=" · ".join(f"{s}: {STATUS_RULE[s].lower()}" for s in STATUSES))
    st.multiselect("Emirate", sorted(M_all.emirate.unique()), key="f_emirate", placeholder="All emirates")
    st.segmented_control("Home banner", ["All", "Home Centre", "Homebox", "None yet"], key="f_home")
    st.segmented_control("Fashion banner", ["All", "Splash", "Max", "None yet"], key="f_fashion")
    st.segmented_control("Household", ["All", "With children", "No children"], key="f_kids")
    st.segmented_control("Gender", ["All", "Women", "Men"], key="f_gender")
    st.slider("Age", 20, 65, key="f_age")
    st.slider("Lifetime spend (AED)" + (", incl. linked Viva" if LINK else ""), 0, max_spend, step=250, key="f_spend")
    st.button("Clear all filters", on_click=data.reset_filters, args=(max_spend,), key="side_reset", **ui.BTN_W)

mask = data.apply_filters(M_all)
M = M_all[mask]
st.sidebar.caption(f"**{len(M):,}** of {len(M_all):,} members selected · "
                   f"{M.monetary.sum() / max(M_all.monetary.sum(), 1):.0%} of lifetime spend")
st.sidebar.markdown("---")
st.sidebar.caption(("With the Identity Link Explorer on, spend, status and baskets include Viva purchases attached by the "
                    "unverified 4-digit pairing. Model scores (churn, CLV, routing) stay Shukran-only.") if LINK else
                   ("Every figure is Shukran-only. Viva supermarket uses its own loyalty IDs, so its spend cannot be "
                    "linked to these members (see *Method & data*)."))

ctx = data.Ctx(D=D, M_all=M_all, M=M, mask=mask, max_spend=max_spend, link=LINK,
               banners=list(BANNERS_X if LINK else BANNERS), statuses=list(STATUSES))
data.CURRENT = ctx

PAGES = {
    "overview": st.Page(overview.render, title="Executive summary", url_path="summary", default=True),
    "segments": st.Page(segments.render, title="Segments", url_path="segments"),
    "retention": st.Page(retention.render, title="Retention", url_path="retention"),
    "value": st.Page(value.render, title="Customer value", url_path="value"),
    "routing": st.Page(routing.render, title="Banner routing", url_path="routing"),
    "bundles": st.Page(bundles.render, title="Bundles", url_path="bundles"),
    "member": st.Page(member.render, title="Member 360", url_path="member"),
    "models": st.Page(models.render, title="Models", url_path="models"),
    "method": st.Page(method.render, title="Method & data", url_path="method"),
    "campaign": st.Page(campaign.render, title="Campaign plan", url_path="campaign"),
}
ctx.pages = PAGES
nav = st.navigation(list(PAGES.values()), position="top")

goto = st.session_state.get("_goto")
if goto:
    st.session_state._goto = None
    if goto in PAGES and nav.title != PAGES[goto].title:
        st.switch_page(PAGES[goto])

st.session_state["_pnl"] = 0          # panel keys restart every run so they stay stable
ui.brand_band(ctx)
ui.breadcrumb(ctx)
nav.run()
st.markdown("---")
st.caption("Built from customers.csv, transactions.csv and viva_transactions.csv with a reproducible Python pipeline "
           "(notebook `Landmark_Capstone.ipynb`, fixed random seed 42). Synthetic case-study data, not real Landmark customers.")
