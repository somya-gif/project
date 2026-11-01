# Portfolio display and deployment

Recommended presentation: one GitHub repository, a Streamlit customer explorer, an actual Power BI PBIX download after Windows acceptance, and a 2–3 minute walkthrough video. The Streamlit app is the interactive ML showcase. It does not need a paid model API, GPU or Docker.

## Streamlit hosting

This delivery is local and tested; no public URL has been provisioned. A hosting option is Streamlit Community Cloud. Verify current account/resource availability before relying on a free plan: https://docs.streamlit.io/deploy/streamlit-community-cloud

1. Put the contents of `repeat_purchase` at your repository root. Keep the model, metrics and code. Customer-level data is excluded from the repository. Run the pipeline locally to generate `data/processed`; obtain an approved persistent data source before cloud deployment. Exclude raw workbook, caches and secrets.
2. Use `app.py` as entrypoint and Python 3.12. Dependencies are pinned in requirements.txt.
3. Deploy from the repository using the host's own account flow. No Groq or OpenAI key is needed.
4. Test all five app pages on the hosted URL; confirm historical date banner is visible; select a customer; export a shortlist; try a CSV containing an unknown ID.
5. Do not remove the historical-demo label or claim the model predicts current customers. Public exposure is suitable for these anonymized public-data IDs; do not replace them with private store records without access controls.

The app's uploaded ID list is processed in memory for the current session and not intentionally written to disk. It only looks up bundled historical predictions; it is not a general new-transaction ingestion endpoint. Uploaded IDs override audience filters. Unknown IDs have blank probability and no decision.

## Power BI portfolio display

After the Windows checklist, upload the verified PBIX to your repository/release with a report screenshot or exported PDF generated from Desktop. Browser embedding, sharing and publication depend on your Power BI account/tenant permissions. Do not use public embedding for private customer data. A screenshot is a useful public preview, but it does not replace the required working PBIX.

## 3-minute video outline

- 0:00–0:25: Business question, dataset and historical limitation.
- 0:25–1:00: Power BI sales trend; explain net invoiced sales vs profit; show retention vs returning share.
- 1:00–1:40: Select a Streamlit customer; explain 30-day probability, threshold and observed history.
- 1:40–2:10: Filter/download shortlist; explain why probability is not marketing uplift.
- 2:10–2:45: Show test AP 0.557, base rate 20.8%, temporal split and leakage safeguards.
- 2:45–3:00: Repository structure, test evidence and next production improvements.
