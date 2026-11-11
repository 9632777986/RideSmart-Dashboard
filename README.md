# RideSmart Streamlit Dashboard

## GitHub upload structure

Upload the contents of this ZIP to the ROOT of your GitHub repository.
Do not upload the outer ZIP file itself.

The repository should look like this:

ridesmart-dashboard/
  app.py
  requirements.txt
  README.md
  STREAMLIT_DEPLOYMENT.txt
  data/
    capacity_data.csv
    movement_results.csv
    strategy_comparison.csv
    previous_strategy_summary.csv

## Deploy on Streamlit Community Cloud

1. Create or open your GitHub repository.
2. Upload/extract all files and folders from this package into the repository root.
3. Confirm that `app.py` is visible on the repository's main page.
4. Confirm that the `data` folder is visible on the repository's main page.
5. On Streamlit Community Cloud, choose this repository and branch.
6. Set Main file path to: app.py
7. Deploy.

The dashboard reads its CSV files from the `data` folder. Keep the folder name and CSV filenames unchanged.

## Run locally

Install dependencies:
    pip install -r requirements.txt

Run:
    streamlit run app.py

This is an academic simulation dashboard, not a live dispatch system.
