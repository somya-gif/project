# Publication and remaining acceptance

Repository: https://github.com/somya-gif/project

Source code, a trained model, aggregate evaluation reports, Power BI report definitions and documentation are published. Customer-level CSV exports are deliberately excluded. Automatic upload review rejected customer-level dataset/prediction payloads; they were not added to the published Git tree. The source is the public UCI Online Retail II dataset (CC BY 4.0); attribution and download code are retained.

Run `python -m src.pipeline` once after cloning to download the public source and regenerate all required local tables. `START_WINDOWS.bat` performs this step automatically when prediction data is missing. First setup requires internet, RAM and training time. CI regenerates the data on its temporary runner and tests it without committing data files or uploading data artifacts.

Streamlit Community Cloud should not run training on every app rerun. Before public deployment, provide an approved persistent data source or an explicitly approved dataset bundle. No public app URL is included in this delivery.

The actual `.pbix` remains outstanding: open the supplied PBIP in Windows Power BI Desktop after data generation, refresh, inspect all pages, Save As PBIX, and reopen it. Follow POWER_BI_WINDOWS.md. JSON schema validation cannot replace this Desktop acceptance step.
