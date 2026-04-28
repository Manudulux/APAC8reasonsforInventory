# 8 Reasons Inventory Tool — Streamlit Edition

A Streamlit web app for Goodyear's 8 Reasons Inventory Management System.

## Deploy to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo and set the main file to `app.py`
4. Deploy!

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Workflow

1. **Upload & Validate** — Upload all 12 input Excel files
2. **Intermediate File** — Generate and review intermediate calculations
3. **Final Output** — Run the full 8 Reasons calculation
4. **Global Settings** — Tune parameters for your plant/region

## Input Files Required

| File | Description |
|------|-------------|
| Consumption (Invoice Hist) | Historical raw material consumption |
| 6M Forecast (Future) | Forward-looking 6-month BOM forecast |
| 12M Historical Forecast | Past 12-month BOM forecast |
| Supply Parameters | Supplier & material master data |
| Sourcing Data | Sourcing routes and supplier info |
| Shipping Interval | Historical shipment dates |
| Supply & Shipping Variance | ATD vs ETD data |
| Local Transit Time | Local supplier transit overrides |
| Actual Inventory | Current stock snapshot |
| Product Master | RM classification data |
| SKU Transition | Phase-in/out RM code mapping |
| Supplier Transition | Phase-in/out supplier code mapping |
