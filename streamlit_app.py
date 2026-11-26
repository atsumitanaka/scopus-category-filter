"""Scopus category filter — Streamlit app that classifies Scopus CSV exports."""
from __future__ import annotations

import io
import re

import pandas as pd
import streamlit as st

DEFAULT_COMP_PATTERNS = [
    r"\bDFT\b",
    r"density[- ]functional",
    r"first[- ]principles?",
    r"ab[- ]initio",
    r"\bVASP\b", r"Quantum ESPRESSO", r"WIEN2k", r"CASTEP",
    r"\bLAMMPS\b", r"GROMACS",
    r"molecular[- ]dynamics",
    r"Monte[- ]Carlo",
    r"phase[- ]field",
    r"\bCALPHAD\b",
    r"machine[- ]learning[- ]potential",
    r"neural[- ]network[- ]potential",
    r"tight[- ]binding",
    r"Hartree[- ]Fock",
    r"Boltzmann[- ]transport",
    r"cluster[- ]expansion",
    r"\bDMFT\b", r"\bDFPT\b",
    r"\bGGA\b", r"\bPBE\b", r"\bLDA\b", r"\bHSE\b", r"\bPBEsol\b",
    r"\bsimulat(ion|ed|ing)\b",
    r"\bcomputation(al|ally)\b",
    r"theoretical(ly)?[- ](predict|calculat|investigat|stud)",
    r"\bfinite[- ]element\b",
    r"\bNEB\b", r"nudged[- ]elastic[- ]band",
    r"\bQMC\b", r"quantum[- ]Monte[- ]Carlo",
]

DEFAULT_EXP_PATTERNS = [
    r"synthesi[sz]ed", r"synthesi[sz]ing", r"\bsynthesis\b",
    r"\bprepared\b", r"fabricat", r"\bgrown\b",
    r"\bmeasured\b", r"measurement",
    r"\bXRD\b", r"X[- ]ray[- ]diffraction",
    r"\bTEM\b", r"\bSEM\b", r"\bSTEM\b", r"\bHRTEM\b", r"\bAFM\b",
    r"\bRaman\b", r"\bFTIR\b", r"\bXPS\b", r"\bEDS\b", r"\bEDX\b", r"\bEELS\b",
    r"\bDSC\b", r"\bTGA\b", r"\bDTA\b",
    r"anneal",
    r"\bsinter",
    r"arc[- ]melt",
    r"melt[- ]spinning",
    r"spark[- ]plasma[- ]sintering", r"\bSPS\b",
    r"hot[- ]press",
    r"ball[- ]mill",
    r"Bridgman", r"Czochralski", r"zone[- ]melt",
    r"single[- ]crystal[- ]growth",
    r"chemical[- ]vapor[- ]deposition", r"\bCVD\b",
    r"physical[- ]vapor[- ]deposition", r"\bPVD\b",
    r"\bsputtering\b",
    r"\bexperimentally\b", r"\bexperiment(s|al)\b",
    r"characteri[sz]ed", r"characteri[sz]ation",
    r"Hall[- ](effect|measurement|coefficient)",
    r"Seebeck[- ]coefficient",
    r"\bresistivity[- ]measurement",
    r"as[- ]cast", r"as[- ]sintered", r"as[- ]deposited",
]


def _find_col(columns: list[str], candidates: list[str]) -> str | None:
    low = {c.strip().lower(): c for c in columns}
    for name in candidates:
        if name.lower() in low:
            return low[name.lower()]
    return None


def _count_hits(text: str, patterns: tuple[str, ...]) -> tuple[int, list[str]]:
    total = 0
    matched: list[str] = []
    for p in patterns:
        hits = re.findall(p, text, re.IGNORECASE)
        if hits:
            total += len(hits)
            matched.append(p)
    return total, matched


def _classify(exp_n: int, comp_n: int) -> str:
    if exp_n == 0 and comp_n == 0:
        return "unclear"
    if comp_n == 0:
        return "experimental"
    if exp_n == 0:
        return "computational"
    ratio = comp_n / (exp_n + comp_n)
    if ratio >= 0.7:
        return "computational"
    if ratio <= 0.3:
        return "experimental"
    return "mixed"


@st.cache_data(show_spinner="Classifying…")
def classify_csv(
    file_bytes: bytes,
    comp_patterns: tuple[str, ...],
    exp_patterns: tuple[str, ...],
) -> tuple[pd.DataFrame, str | None]:
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    cols = list(df.columns)
    abs_col = _find_col(cols, ["Abstract"])
    if abs_col is None:
        return df, "Abstract column not found. Re-export from Scopus with the Abstract column included."
    title_col = _find_col(cols, ["Title"])
    akw_col = _find_col(cols, ["Author Keywords"])
    ikw_col = _find_col(cols, ["Index Keywords"])

    cats: list[str] = []
    exp_hits: list[int] = []
    comp_hits: list[int] = []
    comp_matched: list[str] = []
    for _, row in df.iterrows():
        parts = [
            row.get(title_col, "") if title_col else "",
            row.get(abs_col, ""),
            row.get(akw_col, "") if akw_col else "",
            row.get(ikw_col, "") if ikw_col else "",
        ]
        text = " ".join(p for p in parts if isinstance(p, str) and p)
        exp_n, _m = _count_hits(text, exp_patterns)
        comp_n, cm = _count_hits(text, comp_patterns)
        cats.append(_classify(exp_n, comp_n))
        exp_hits.append(exp_n)
        comp_hits.append(comp_n)
        comp_matched.append("; ".join(cm))

    df["category"] = cats
    df["exp_hits"] = exp_hits
    df["comp_hits"] = comp_hits
    df["comp_matched"] = comp_matched
    return df, None


def _init_state() -> None:
    if "comp_patterns_text" not in st.session_state:
        st.session_state.comp_patterns_text = "\n".join(DEFAULT_COMP_PATTERNS)
    if "exp_patterns_text" not in st.session_state:
        st.session_state.exp_patterns_text = "\n".join(DEFAULT_EXP_PATTERNS)


def _patterns_from_text(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))


st.set_page_config(
    page_title="Scopus category filter",
    page_icon=":material/filter_alt:",
    layout="wide",
)
_init_state()

st.title(":material/filter_alt: Scopus category filter")
st.caption("Classify Scopus CSV exports into experimental, computational, mixed, or unclear.")

with st.sidebar:
    st.header("Keywords")
    st.caption("One pattern per line (Python regex); `#` for comments.")
    with st.expander("Computational keywords", expanded=False):
        st.text_area(
            "Computational",
            key="comp_patterns_text",
            height=300,
            label_visibility="collapsed",
        )
    with st.expander("Experimental keywords", expanded=False):
        st.text_area(
            "Experimental",
            key="exp_patterns_text",
            height=300,
            label_visibility="collapsed",
        )
    if st.button(":material/restart_alt: Reset to defaults", width="stretch"):
        st.session_state.comp_patterns_text = "\n".join(DEFAULT_COMP_PATTERNS)
        st.session_state.exp_patterns_text = "\n".join(DEFAULT_EXP_PATTERNS)
        st.rerun()

uploaded = st.file_uploader(
    "Drop a Scopus CSV",
    type=["csv"],
    help="A Scopus export (Export > CSV) that includes the Abstract column.",
)

if uploaded is None:
    st.info(
        "Export from Scopus via **Export > CSV** with **Abstract & keywords** included, then upload the file here.",
        icon=":material/upload_file:",
    )
    st.stop()

comp_patterns = _patterns_from_text(st.session_state.comp_patterns_text)
exp_patterns = _patterns_from_text(st.session_state.exp_patterns_text)

df, error = classify_csv(uploaded.getvalue(), comp_patterns, exp_patterns)
if error:
    st.error(error, icon=":material/error:")
    st.stop()

total = len(df)
counts = df["category"].value_counts().to_dict()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("total", total)
m2.metric(":material/science: experimental", int(counts.get("experimental", 0)))
m3.metric(":material/sync_alt: mixed", int(counts.get("mixed", 0)))
m4.metric(":material/calculate: computational", int(counts.get("computational", 0)))
m5.metric(":material/help: unclear", int(counts.get("unclear", 0)))

st.divider()

categories = st.pills(
    "Categories to show",
    ["experimental", "mixed", "computational", "unclear"],
    selection_mode="multi",
    default=["experimental", "mixed"],
)
filtered = df[df["category"].isin(categories)] if categories else df.iloc[0:0]

st.write(f"Showing **{len(filtered)}** of **{total}** papers")

preferred_order = [
    "category", "comp_hits", "exp_hits", "comp_matched",
    "Title", "Year", "Source title", "Authors", "DOI", "Abstract",
    "Author Keywords", "Index Keywords",
]
ordered_cols = [c for c in preferred_order if c in filtered.columns]
ordered_cols += [c for c in filtered.columns if c not in ordered_cols]

column_config: dict[str, object] = {
    "category": st.column_config.TextColumn("category", width="small"),
    "comp_hits": st.column_config.NumberColumn("comp", width="small"),
    "exp_hits": st.column_config.NumberColumn("exp", width="small"),
    "comp_matched": st.column_config.TextColumn("matched patterns", width="medium"),
    "Title": st.column_config.TextColumn("Title", width="large"),
    "Abstract": st.column_config.TextColumn("Abstract", width="large"),
}
if "DOI" in filtered.columns:
    column_config["DOI"] = st.column_config.LinkColumn(
        "DOI",
        display_text=r"https?://(?:dx\.)?doi\.org/(.+)",
        help="Opens doi.org in a new tab",
    )
    display_df = filtered.copy()
    display_df["DOI"] = display_df["DOI"].apply(
        lambda v: f"https://doi.org/{v}" if v and not v.startswith("http") else v
    )
else:
    display_df = filtered

st.dataframe(
    display_df[ordered_cols],
    width="stretch",
    height=600,
    hide_index=True,
    column_config=column_config,
    alt="Classified papers table",
)

csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    ":material/download: Download filtered CSV",
    data=csv_bytes,
    file_name="scopus_classified.csv",
    mime="text/csv",
    width="stretch",
    type="primary",
)
