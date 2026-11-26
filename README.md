# Scopus category filter

A small Streamlit app that classifies a Scopus CSV export into **experimental**, **computational**, **mixed**, or **unclear** categories by keyword matching on the title, abstract, and keyword fields.

Built to pre-screen papers before registering them in [Starrydata2](https://www.starrydata2.org/), filtering out computational / theoretical papers that slip through Scopus's native filters.

## How to use

1. Open the app URL.
2. In Scopus, export your search results as CSV with **Abstract & keywords** included.
3. Drop the CSV onto the app.
4. Use the category pills to filter, then download the filtered CSV.

Classification is pure keyword matching (Python regex); the keyword lists are editable in the sidebar. Papers with both experimental and computational signals are classified as `mixed` and should be reviewed manually.

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run streamlit_app.py
```
