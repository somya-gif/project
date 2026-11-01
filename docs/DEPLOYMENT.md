# Deployment

## Streamlit hosting

The app runs locally out of the box. For public hosting, [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) works well:

1. Push the repo to GitHub. Keep the model and metrics; customer CSVs are git-ignored.
2. Run the pipeline locally first to generate `data/processed/`. For cloud deployment, provide a persistent data source.
3. Set `app.py` as the entrypoint, Python 3.12. Dependencies are in `requirements.txt`.
4. Deploy and verify all five pages load correctly.

## Power BI

After completing the [Power BI setup](POWER_BI_WINDOWS.md), save as `.pbix` and include it in the repo or as a release asset. A screenshot or exported PDF is useful for the README.
