import streamlit as st
import pandas as pd
import base64
import os
import glob
from io import BytesIO

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="8 Reasons Inventory Tool – Goodyear",
    page_icon="🔴",
    layout="wide",
)

# ── Imports ────────────────────────────────────────────────────────────────────
from src.helper import GLOBAL_CONFIG
from src.helper.gobal_parameters import global_parameter_class
from src.helper.ValidateSheets import Validation
from src.helper.J2S import JSONtoSheets
from src.helper.utils import FileUtils
from src.utils.validate_multi import IntermediateFile
from src.component.calculations import GenerateIntermediateOutput
from src.final_output.main import EightReasons
from src.helper import base64_to_dataframe

# ── Session state ──────────────────────────────────────────────────────────────
for key in ["validated_data", "intermediate_data", "rm_seg_b64",
            "final_output_b64", "consumption_merged_b64", "rm_seg_merged_b64"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Constants ──────────────────────────────────────────────────────────────────
# Maps internal variable name -> (display label, filename on disk / in GitHub)
FILE_META = {
    "Consumption_Invoice_Hist":  ("Consumption (Invoice Hist)",   "Consumption_(Invoice_Hist).xlsx"),
    "BOM_Forecast_Data_Future":  ("6M Forecast (Future)",         "BOM_(Forecast_Data_Future).xlsx"),
    "BOM_Forecast_Data_History": ("12M Historical Forecast",      "BOM_(Forecast_Data_History).xlsx"),
    "Supply_Parameters":         ("Supply Parameters",            "Supply_Parameters.xlsx"),
    "Sourcing_Data":             ("Sourcing Data",                 "Sourcing_Data.xlsx"),
    "Shipping_Interval":         ("Shipping Interval",            "Shipping_Interval.xlsx"),
    "Supply&Shipping_Var":       ("Supply & Shipping Variance",   "Supply&Shipping_Var.xlsx"),
    "Local_TT":                  ("Local Transit Time",           "Local_TT.xlsx"),
    "Actual_Inventory":          ("Actual Inventory",             "Actual_Inventory.xlsx"),
    "Product_Master":            ("Product Master",               "Product_Master.xlsx"),
    "SKU_Transition":            ("SKU Transition",               "SKU_Transition.xlsx"),
    "Supplier_Transition":       ("Supplier Transition",          "Supplier_Transition.xlsx"),
}

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Helpers ────────────────────────────────────────────────────────────────────
def bytes_to_b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("utf-8")

def b64_to_bytes(b64_str: str) -> bytes:
    return base64.b64decode(b64_str)

def make_download_button(b64_str: str, filename: str, label: str):
    st.download_button(
        label=label,
        data=b64_to_bytes(b64_str),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def run_validation(file_bytes: dict):
    """Build sheets JSON, run Validation, return (result_dict, error_list)."""
    sheets_json = {"Sheets": []}
    for key, raw in file_bytes.items():
        b64 = bytes_to_b64(raw)
        sheets_json["Sheets"].append({
            "Name": key, "NameExpression": "", "Variable": key,
            "Columns": [], "Errors": [], "Data": b64,
            "FileName": FILE_META.get(key, ("", f"{key}.xlsx"))[1],
        })
    input_class = JSONtoSheets().ConvertJSONToSheets(sheets_json)
    result = Validation().validatesheets(input_class)
    errors = []
    for sheet in result.get("Sheets", []):
        if sheet.get("Errors"):
            errors.append(f"**{sheet.get('Variable','?')}**: {sheet['Errors']}")
    return result, errors

def scan_local_files(directory: str) -> dict:
    """Return {variable_key: file_bytes} for all matching xlsx files in directory."""
    found = {}
    for key, (label, filename) in FILE_META.items():
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                found[key] = f.read()
    return found

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Goodyear_logo.svg/200px-Goodyear_logo.svg.png",
        width=140,
    )
    st.title("8 Reasons Inventory")
    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠 Home",
        "🔧 Global Settings",
        "📂 Upload & Validate",
        "⚙️ Intermediate File",
        "📊 Final Output",
        "📊 Dashboard 1",
        "🗺️ Dashboard 2",
        "📈 Dashboard 3",
    ])
    st.markdown("---")
    st.markdown("**Pipeline status**")
    st.markdown("✅ Validated"         if st.session_state["validated_data"]   else "⬜ Not yet validated")
    st.markdown("✅ Intermediate ready" if st.session_state["intermediate_data"] else "⬜ Not yet generated")
    st.markdown("✅ Final output ready" if st.session_state["final_output_b64"] else "⬜ Not yet calculated")
    st.markdown("---")
    st.caption("Goodyear IMS v2 — Streamlit Edition")

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.title("🔴 8 Reasons Inventory Management Tool")
    st.markdown("""
    Welcome to the **Goodyear 8 Reasons Inventory Tool**. This application calculates
    scientifically grounded inventory targets based on **8 key drivers**:

    | # | Reason | Description |
    |---|--------|-------------|
    | R1 | **Information Cycle** | Half the review period — how often orders are placed |
    | R2 | **Manufacturing Lot Size** | Buffer from minimum order quantities |
    | R3 | **Shipping Lot Size** | Buffer from minimum shipment sizes |
    | R4 | **Shipping Interval** | How often shipments depart |
    | R5 | **Geography** | Transit lead time from source to plant |
    | R6 | **Shipping Variation** | Unpredictability in transit time |
    | R7 | **Supply Variation** | Supplier delivery reliability |
    | R8 | **Demand Variation** | Forecast accuracy / demand uncertainty |

    ### Workflow
    1. **Upload & Validate** — Load your 12 input files (from disk, GitHub, or manual upload).
    2. **Intermediate File** — Generate supply parameters and RM segmentation.
    3. **Final Output** — Run the full 8 Reasons calculation and download results.
    4. **Global Settings** — Tune parameters like caps, segmentation, and production days.
    """)
    st.info("👈 Use the sidebar to navigate between steps.")

# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD & VALIDATE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📂 Upload & Validate":
    st.title("📂 Upload & Validate Input Files")

    source = st.radio(
        "**How would you like to load the input files?**",
        [
            "📁 Load from script directory (files already in repo)",
            "⬆️ Upload files manually",
        ],
        horizontal=False,
    )
    st.markdown("---")

    file_bytes: dict = {}   # key → bytes

    # ── Option 1 : script directory ──────────────────────────────────────────
    if source == "📁 Load from script directory (files already in repo)":
        st.markdown(f"""
        This option scans the **same folder as `app.py`** for the standard input file names.
        On Streamlit Cloud that is the **root of your GitHub repository**.

        Detected directory: `{APP_DIR}`
        """)

        if st.button("🔍 Scan directory for input files"):
            found = scan_local_files(APP_DIR)
            st.session_state["_local_files"] = found

        if st.session_state.get("_local_files"):
            found = st.session_state["_local_files"]
            file_bytes = dict(found)
            missing = [FILE_META[k][0] for k in FILE_META if k not in found]

            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ **{len(found)}/{len(FILE_META)} files found** on disk:")
                for k in found:
                    st.markdown(f"  - ✅ {FILE_META[k][0]}")
            with col2:
                if missing:
                    st.warning(f"⚠️ **{len(missing)} file(s) not found** — upload them below:")
                    for label in missing:
                        st.markdown(f"  - ❌ {label}")

            # Allow manual top-up for missing files
            if missing:
                st.markdown("**Upload missing files:**")
                cols = st.columns(2)
                for i, (key, (label, _)) in enumerate(FILE_META.items()):
                    if key not in found:
                        with cols[i % 2]:
                            f = st.file_uploader(label, type=["xlsx", "xls"], key=f"local_up_{key}")
                            if f:
                                file_bytes[key] = f.read()
                                st.session_state["_local_files"][key] = file_bytes[key]

    # ── Option 2 : multi-file upload ─────────────────────────────────────────
    else:
        st.markdown("""
        Drop all **12 Excel files at once** into the box below, or click to browse.
        The tool will automatically match each file to the correct input slot by filename.
        """)

        # Expected filename → variable key mapping (reverse lookup)
        FILENAME_TO_KEY = {v[1].lower(): k for k, v in FILE_META.items()}

        uploaded_multi = st.file_uploader(
            "Drop all 12 input files here",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key="multi_upload",
            help="You can select or drop all 12 files in one go."
        )

        if uploaded_multi:
            unmatched = []
            for uf in uploaded_multi:
                fname_lower = uf.name.lower()
                matched_key = None
                # Try exact filename match first
                if fname_lower in FILENAME_TO_KEY:
                    matched_key = FILENAME_TO_KEY[fname_lower]
                else:
                    # Fuzzy: check if any key substring appears in filename
                    for key, (label, fname) in FILE_META.items():
                        if fname.lower().replace(".xlsx","") in fname_lower or \
                           fname_lower.replace(".xlsx","") in fname.lower().replace(".xlsx",""):
                            matched_key = key
                            break
                if matched_key:
                    file_bytes[matched_key] = uf.read()
                else:
                    unmatched.append(uf.name)

            # Show match status
            c_ok, c_miss = st.columns(2)
            with c_ok:
                if file_bytes:
                    st.success(f"✅ **{len(file_bytes)}/{len(FILE_META)} files matched:**")
                    for k in file_bytes:
                        st.markdown(f"  - ✅ {FILE_META[k][0]}")
            with c_miss:
                missing_keys = [k for k in FILE_META if k not in file_bytes]
                if missing_keys:
                    st.warning(f"⚠️ **{len(missing_keys)} still needed:**")
                    for k in missing_keys:
                        st.markdown(f"  - ❌ {FILE_META[k][0]}")
                if unmatched:
                    st.error(f"Could not match: {', '.join(unmatched)}")

        # Individual uploaders for any remaining unmatched files
        missing_keys = [k for k in FILE_META if k not in file_bytes]
        if missing_keys:
            with st.expander(f"📎 Upload remaining {len(missing_keys)} file(s) individually"):
                cols = st.columns(2)
                for i, key in enumerate(missing_keys):
                    with cols[i % 2]:
                        f = st.file_uploader(FILE_META[key][0], type=["xlsx","xls"], key=f"ind_{key}")
                        if f:
                            file_bytes[key] = f.read()

    st.markdown(f"**{len(file_bytes)} / {len(FILE_META)} files ready**")
    st.markdown("---")

    # ── Validate ──────────────────────────────────────────────────────────────
    if st.button("✅ Validate Files", disabled=len(file_bytes) == 0, type="primary"):
        with st.spinner("Validating files…"):
            try:
                result, errors = run_validation(file_bytes)
                if errors:
                    st.error("❌ Validation failed:")
                    for msg in errors:
                        st.markdown(f"- {msg}")
                else:
                    st.session_state["validated_data"]    = result
                    st.session_state["intermediate_data"] = None   # reset downstream
                    st.session_state["final_output_b64"]  = None
                    st.success("✅ All files validated successfully!")
                    st.balloons()
                    st.info("👈 Proceed to **Intermediate File** in the sidebar.")
            except Exception as e:
                import traceback
                st.error(f"Unexpected error during validation: {e}")
                st.code(traceback.format_exc())

    if st.session_state.get("validated_data"):
        with st.expander("📋 Validated sheet summary"):
            for sheet in st.session_state["validated_data"].get("Sheets", []):
                icon = "✅" if not sheet.get("Errors") else "❌"
                st.markdown(f"{icon} `{sheet.get('Variable', sheet.get('Name','?'))}`")

# ══════════════════════════════════════════════════════════════════════════════
# INTERMEDIATE FILE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Intermediate File":
    st.title("⚙️ Generate Intermediate File")

    if not st.session_state.get("validated_data"):
        st.warning("⚠️ Please complete the **Upload & Validate** step first.")
        st.stop()

    st.markdown("""
    The intermediate step calculates:
    - **Supply Parameters** — minimum order qty, supply reliability, service level
    - **RM Segmentation** — ABC-123 classification by volume and variability
    - **Sourcing Data** — transit times, shipping intervals, lot sizes
    """)

    if st.button("🔄 Generate Intermediate Output", type="primary"):
        with st.spinner("Calculating… (this may take a minute)"):
            try:
                validated_data    = st.session_state["validated_data"]
                intermediate_output = GenerateIntermediateOutput(validated_data).generate_intermediate_response()
                response          = IntermediateFile(validated_data).make_response(intermediate_output)

                if isinstance(response, str) and response.lower().startswith("error"):
                    st.error(f"❌ {response}")
                else:
                    st.session_state["intermediate_data"] = response
                    st.session_state["rm_seg_b64"]        = response.get("RM_Segmentation_Output", "")
                    st.session_state["final_output_b64"]  = None
                    st.success("✅ Intermediate file generated!")

            except Exception as e:
                import traceback
                st.error(f"Error during intermediate calculation: {e}")
                st.code(traceback.format_exc())

    if st.session_state.get("intermediate_data"):
        st.success("✅ Intermediate output is ready.")
        st.subheader("📥 Download Intermediate Sheets")
        cols = st.columns(3)
        for i, sheet in enumerate(st.session_state["intermediate_data"].get("Sheets", [])):
            b64  = sheet.get("Data", "")
            name = sheet.get("Variable", f"Sheet_{i}")
            if b64:
                with cols[i % 3]:
                    make_download_button(b64, f"{name}.xlsx", f"⬇ {name}")

        rm_b64 = st.session_state.get("rm_seg_b64", "")
        if rm_b64:
            st.markdown("---")
            make_download_button(rm_b64, "RM_Segmentation_Output.xlsx", "⬇ RM Segmentation Output")

        st.info("👈 Proceed to **Final Output** in the sidebar.")

# ══════════════════════════════════════════════════════════════════════════════
# FINAL OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Final Output":
    st.title("📊 Final Output — 8 Reasons Calculation")

    if not st.session_state.get("intermediate_data"):
        st.warning("⚠️ Please complete the **Intermediate File** step first.")
        st.stop()

    st.markdown("""
    Runs the full **8 Reasons** calculation and produces:
    - **SKU-level** DSI and unit targets (Cycle / Transit / Safety / 8 Reasons / Min / Max / On-Hand)
    - **Aggregated views** by Region, Plant, INCO Term, Planning Cycle, RM Segmentation
    - **Under Min / Over Max** value analysis
    """)

    if st.button("🚀 Run 8 Reasons Calculation", type="primary"):
        with st.spinner("Running 8 Reasons calculation… (may take several minutes for large datasets)"):
            try:
                intermediate_input = dict(st.session_state["intermediate_data"])
                rm_b64 = st.session_state.get("rm_seg_b64", "")
                if rm_b64:
                    intermediate_input["RM_Segmentation_Output"] = rm_b64

                json_sheets  = JSONtoSheets().ConvertJSONToSheets(intermediate_input)
                rm_df        = base64_to_dataframe(rm_b64) if rm_b64 else pd.DataFrame()
                final_response = EightReasons(json_sheets, rm_df).calculate()

                if isinstance(final_response, str) and "error" in final_response.lower():
                    st.error(f"❌ {final_response}")
                else:
                    st.session_state["final_output_b64"]        = final_response.get("Final_Output", "")
                    st.session_state["consumption_merged_b64"]  = final_response.get("Consumption_merged", "")
                    st.session_state["rm_seg_merged_b64"]       = final_response.get("RM_Seg_merged", "")
                    st.success("✅ 8 Reasons calculation complete!")
                    st.balloons()

            except Exception as e:
                import traceback
                st.error(f"Error during final calculation: {e}")
                st.code(traceback.format_exc())

    if st.session_state.get("final_output_b64"):
        st.success("✅ Final output is ready for download.")
        st.subheader("📥 Download Results")
        c1, c2, c3 = st.columns(3)
        with c1:
            make_download_button(st.session_state["final_output_b64"],
                                 "8Reasons_Final_Output.xlsx", "⬇ Final Output (multi-sheet)")
        with c2:
            if st.session_state.get("consumption_merged_b64"):
                make_download_button(st.session_state["consumption_merged_b64"],
                                     "Consumption_Merged.xlsx", "⬇ Consumption Merged")
        with c3:
            if st.session_state.get("rm_seg_merged_b64"):
                make_download_button(st.session_state["rm_seg_merged_b64"],
                                     "RM_Segmentation_Merged.xlsx", "⬇ RM Seg Merged")

        st.subheader("👁 Preview")
        try:
            raw = base64.b64decode(st.session_state["final_output_b64"])
            xls = pd.ExcelFile(BytesIO(raw))
            sheet_to_show = st.selectbox("Sheet to preview", xls.sheet_names)
            preview_df    = pd.read_excel(BytesIO(raw), sheet_name=sheet_to_show)
            st.dataframe(preview_df.head(200), use_container_width=True)
        except Exception as e:
            st.info(f"Preview unavailable: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔧 Global Settings":
    st.title("🔧 Global Parameters")
    st.markdown("Adjust global calculation parameters. Changes apply to the current session.")

    gp_class = global_parameter_class()
    config   = gp_class.get_global_config()
    params   = config["global_parameters"][0]

    with st.form("global_settings_form"):
        st.subheader("📈 Forecast Settings")
        c1, c2 = st.columns(2)
        with c1:
            weekly_split     = st.selectbox("Weekly Split Method", [0, 1],
                                             index=params["forecast"].get("weekly_split_method", 1))
            demand_var_method = st.selectbox("Demand Variation Method", ["Under", "Both"],
                                              index=0 if params["forecast"].get("demand_variation_method") == "Under" else 1)
        with c2:
            skewness = st.checkbox("Apply Skewness", value=params["forecast"].get("Skewness", True))

        st.subheader("🎯 Cappings")
        c1, c2, c3, c4 = st.columns(4)
        with c1: safety_cap    = st.number_input("Safety Stock Cap (DSI)",         value=params["cappings"].get("safety_stock_cap", 90),    min_value=0)
        with c2: transit_cap   = st.number_input("Transit Time Cap (DSI)",          value=params["cappings"].get("transit_time_cap", 50),    min_value=0)
        with c3: shipping_cap  = st.number_input("Shipping Interval Cap (DSI)",     value=params["cappings"].get("shipping_interval_cap", 10), min_value=0)
        with c4: max_demand_pct= st.number_input("Max Demand % of Forecast",       value=params["cappings"].get("Maximum Demand in % of Forecast", 120), min_value=0)

        st.subheader("⚙️ Cycle Stock Methodology")
        cycle_method = st.selectbox("Cycle Stock Method", ["Max", "Sum"],
                                     index=0 if params["cycle_stock"].get("calculation_methodology") == "Max" else 1)

        st.subheader("💱 Price Conversion")
        usd_value = st.number_input("USD Value (local currency per USD)",
                                     value=params["price_conversion"].get("USD_value", 84), min_value=1)

        st.subheader("🏭 Production Days per Month")
        prod_days    = params.get("production_days", {})
        pd_cols      = st.columns(6)
        new_prod_days = {}
        for i, (month, days) in enumerate(prod_days.items()):
            with pd_cols[i % 6]:
                new_prod_days[month] = st.number_input(month, value=days, min_value=0, max_value=31, key=f"pd_{month}")

        st.subheader("📦 Default Values")
        c1, c2   = st.columns(2)
        defaults = params.get("default_values", {})
        with c1:
            tt_local   = st.number_input("Transit Time Local (days)",       value=defaults.get("transit_time_local", 7),    min_value=0)
            tt_imported= st.number_input("Transit Time Imported (days)",    value=defaults.get("transit_time_imported", 30), min_value=0)
            supply_rel = st.number_input("Default Supply Reliability (%)",  value=defaults.get("supply_reliability", 90),   min_value=0, max_value=100)
        with c2:
            si_local   = st.number_input("Shipping Interval Local (days)",   value=defaults.get("shipping_interval_local", 30),    min_value=0)
            si_imported= st.number_input("Shipping Interval Imported (days)",value=defaults.get("shipping_interval_imported", 30), min_value=0)

        st.subheader("🔢 Tolerance")
        tol  = params.get("tolerance", {})
        c1, c2 = st.columns(2)
        with c1: tol_local    = st.number_input("Tolerance Local (days)",    value=tol.get("local", 1),    min_value=0)
        with c2: tol_imported = st.number_input("Tolerance Imported (days)", value=tol.get("imported", 7), min_value=0)

        submitted = st.form_submit_button("💾 Save Settings")

    if submitted:
        new_config = {"global_parameters": [{
            "forecast":        {"weekly_split_method": weekly_split, "demand_variation_method": demand_var_method, "Skewness": skewness},
            "cappings":        {"safety_stock_cap": safety_cap, "transit_time_cap": transit_cap, "shipping_interval_cap": shipping_cap, "Maximum Demand in % of Forecast": max_demand_pct},
            "cycle_stock":     {"calculation_methodology": cycle_method},
            "tolerance":       {"local": tol_local, "imported": tol_imported},
            "rm_segmentation": params.get("rm_segmentation", {}),
            "service_level_mapping": params.get("service_level_mapping", {}),
            "production_days": new_prod_days,
            "price_conversion": {"USD_value": usd_value},
            "default_values":  {"transit_time_local": tt_local, "transit_time_imported": tt_imported,
                                 "shipping_interval_local": si_local, "shipping_interval_imported": si_imported,
                                 "supply_reliability": supply_rel},
        }]}
        is_valid, msg = gp_class.validate_global_config(new_config)
        if is_valid:
            st.success(f"✅ {gp_class.update_global_config(new_config)}")
        else:
            st.error(f"❌ Validation errors: {msg}")

    with st.expander("📋 Current configuration (raw JSON)"):
        st.json(gp_class.get_global_config())

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD 1  ── RM Segmentation Overview (cards + consumption chart)
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD 1 — RM Segmentation Overview (matching original UI)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard 1":
    import plotly.graph_objects as go

    st.markdown("""
    <style>
    .gy-title {font-size:26px;font-weight:700;color:#1a1a2e;text-align:center;margin-bottom:4px}
    .kpi-card {background:#f8f9fa;border:1px solid #dee2e6;border-radius:10px;padding:16px 12px;text-align:center}
    .kpi-label {font-size:12px;color:#6c757d;font-weight:500}
    .kpi-value {font-size:22px;font-weight:800;color:#1a1a2e;margin:4px 0}
    .kpi-sub   {font-size:11px;color:#adb5bd}
    .seg-card  {border-radius:10px;padding:10px 12px;margin-bottom:6px;min-height:165px;position:relative}
    .seg-title {font-size:16px;font-weight:700;color:#1a1a2e}
    .seg-line  {font-size:11px;color:#333;margin:1px 0}
    .filter-row{background:#eef2ff;border-radius:8px;padding:10px 16px;margin-bottom:12px}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='gy-title'>8 Reasons of Inventory</div>", unsafe_allow_html=True)

    if not st.session_state.get("final_output_b64"):
        st.warning("⚠️ Please complete the **Final Output** step first.")
        st.stop()

    fo_bytes = b64_to_bytes(st.session_state["final_output_b64"])
    sku_df   = pd.read_excel(BytesIO(fo_bytes), sheet_name="SKU Level")
    cons_b64 = st.session_state.get("consumption_merged_b64", "")
    cons_df  = pd.read_excel(BytesIO(b64_to_bytes(cons_b64))) if cons_b64 else pd.DataFrame()

    def opts(col): return ["All"] + sorted(sku_df[col].dropna().unique().astype(str).tolist())

    # ── Filters ────────────────────────────────────────────────────────────
    with st.container():
        st.markdown("<div class='filter-row'>", unsafe_allow_html=True)
        fc = st.columns(5)
        f_country = fc[0].selectbox("Country",           opts("Region"),         key="d1_country")
        f_rm_desc = fc[1].selectbox("Raw Material Desc", ["All"] + sorted(sku_df["Material Desc"].dropna().unique().astype(str).tolist()), key="d1_rm")
        f_rm_seg  = fc[2].selectbox("RM Segmentation",   opts("RM Segmentation"), key="d1_seg")
        f_inco    = fc[3].selectbox("INCO Term",          opts("INCO Term"),       key="d1_inco")
        f_plan    = fc[4].selectbox("Planning Cycle",     opts("Planning cycle"),  key="d1_plan")
        fc2 = st.columns([1,1,1,1,0.5])
        f_plant   = fc2[0].selectbox("Plant Name",        opts("PLANT"),           key="d1_plant")
        f_cat     = fc2[1].selectbox("Category",          opts("Category"),        key="d1_cat")
        f_src     = fc2[2].selectbox("Source Country",    opts("Source Country"),  key="d1_src")
        f_rmcg    = fc2[3].selectbox("RM Class Group",    opts("RM Class Group"),  key="d1_rmcg")
        search    = fc2[4].button("🔍 Search", key="d1_search", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    fdf = sku_df.copy()
    if f_country != "All": fdf = fdf[fdf["Region"]         == f_country]
    if f_rm_seg  != "All": fdf = fdf[fdf["RM Segmentation"]== f_rm_seg]
    if f_inco    != "All": fdf = fdf[fdf["INCO Term"]       == f_inco]
    if f_plan    != "All": fdf = fdf[fdf["Planning cycle"]  == f_plan]
    if f_plant   != "All": fdf = fdf[fdf["PLANT"]           == f_plant]
    if f_cat     != "All": fdf = fdf[fdf["Category"]        == f_cat]
    if f_src     != "All": fdf = fdf[fdf["Source Country"]  == f_src]
    if f_rmcg    != "All": fdf = fdf[fdf["RM Class Group"]  == f_rmcg]
    if f_rm_desc != "All": fdf = fdf[fdf["Material Desc"]   == f_rm_desc]

    n_total   = len(fdf)
    avg_dsi   = round(fdf["8 Reasons (DSI)"].mean(), 1) if n_total else 0
    tot_units = fdf["8 Reasons (Units)"].sum()
    map_avg   = fdf["MAP"].mean() if n_total else 0
    tot_val   = round(tot_units * map_avg / 1e6, 2) if n_total else 0
    tot_tons  = round(tot_units / 1000, 1) if n_total else 0

    # ── KPI + Chart row ────────────────────────────────────────────────────
    left_col, right_col = st.columns([1.1, 1])

    with left_col:
        st.markdown("#### 🎯 Targets")
        k1, k2, k3 = st.columns(3)
        def kpi_card(col, title, sub1, value, sub2):
            col.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{title}</div>
                <div class="kpi-sub">—</div>
                <div class="kpi-label">{sub1}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{sub2}</div>
                <div class="kpi-sub">—</div>
            </div>""", unsafe_allow_html=True)

        kpi_card(k1, "Plant AOP DSI (days)",         "8 Reasons Inventory DSI",      f"{avg_dsi} days", "Target (%)")
        kpi_card(k2, "Plant AOP Value (million $)",   "8 Reasons Inventory Value",    f"${tot_val} M",   "Value (%)")
        kpi_card(k3, "Plant AOP Tonnage (MT)",        "8 Reasons Inventory Tonnage",  f"{tot_tons:,.1f} MT", "Tonnage (%)")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── RM Segmentation grid (3×3) ─────────────────────────────────────
        SEG_COLORS = {
            "A1": "#a5d6a7", "A2": "#c8e6c9", "A3": "#e8f5e9",
            "B1": "#b3e5fc", "B2": "#e1f5fe", "B3": "#f0f9ff",
            "C1": "#e1bee7", "C2": "#f3e5f5", "C3": "#fce4ec",
        }
        segs = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
        cols3 = st.columns(3)
        for i, seg in enumerate(segs):
            sub = fdf[fdf["RM Segmentation"] == seg]
            n   = len(sub)
            pct = round(n / n_total * 100, 1) if n_total else 0
            tot_qty  = round(sub["8 Reasons (Units)"].sum() / 1000, 1)
            tot_inv  = round(sub["8 Reasons (Units)"].sum() * sub["MAP"].mean() / 1e6, 2) if n else 0
            tot_sp   = round(sub["8 Reasons (Units)"].sum() * sub["MAP"].mean() / 1e6 / 1000, 3) if n else 0
            svc      = round(sub["Service Level (%)"].mean(), 0) if n else 0
            var      = round(sub["R8 Demand Variation (DSI)"].mean(), 1) if n else 0
            bg       = SEG_COLORS.get(seg, "#f5f5f5")
            with cols3[i % 3]:
                st.markdown(f"""
                <div class="seg-card" style="background:{bg}">
                    <div class="seg-title">{seg}
                        <span style="float:right;font-size:11px;color:#555">⬆ ⬇</span>
                    </div>
                    <div class="seg-line"># of items: <b>{n}/{n_total}</b> ({pct}%)</div>
                    <div class="seg-line">Total req qty: <b>{tot_qty:,.1f}MT</b></div>
                    <div class="seg-line">Total inv: <b>{tot_inv:.2f}M$</b></div>
                    <div class="seg-line">Total spend: <b>{tot_sp:.3f}M$</b></div>
                    <div class="seg-line">Service level: <b>{svc:.0f}%</b></div>
                    <div class="seg-line">Average variability: <b>{var:.1f}</b></div>
                </div>""", unsafe_allow_html=True)

    # ── Right column: 12M Consumption chart ────────────────────────────────
    with right_col:
        st.markdown("#### 📅 Last 12M Consumption")
        chart_type = st.selectbox("", ["Bar", "Line"], key="d1_ctype", label_visibility="collapsed")

        if not cons_df.empty and "Post Date" in cons_df.columns:
            c_filt = cons_df.copy()
            if f_plant != "All" and "Plant Name" in c_filt.columns:
                c_filt = c_filt[c_filt["Plant Name"] == f_plant]
            c_filt["Post Date"] = pd.to_datetime(c_filt["Post Date"], dayfirst=True, errors="coerce")
            c_filt["Month"]     = c_filt["Post Date"].dt.to_period("M")
            monthly = (c_filt.groupby("Month")["Movement Qty"]
                       .sum().abs().reset_index()
                       .sort_values("Month").tail(12))
            monthly["MonthStr"] = monthly["Month"].dt.strftime("%b %Y").str.upper()

            if chart_type == "Bar":
                fig_c = go.Figure(go.Bar(
                    x=monthly["MonthStr"], y=monthly["Movement Qty"],
                    marker_color="#1e3a7b",
                    text=monthly["Movement Qty"].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition="inside", textfont=dict(color="gold", size=9)
                ))
            else:
                fig_c = go.Figure(go.Scatter(
                    x=monthly["MonthStr"], y=monthly["Movement Qty"],
                    mode="lines+markers+text",
                    line=dict(color="#1e3a7b", width=2),
                    marker=dict(size=6, color="#1e3a7b"),
                    text=monthly["Movement Qty"].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition="top center", textfont=dict(size=9)
                ))
            fig_c.update_layout(
                margin=dict(l=10,r=10,t=10,b=30), height=280,
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(autorange="reversed", gridcolor="#e9ecef", title="Qty (MT)"),
                xaxis=dict(tickfont=dict(size=8), tickangle=-30),
                legend=dict(orientation="h")
            )
            fig_c.add_annotation(
                xref="paper", yref="paper", x=0, y=1.05,
                text="Consumption Qty (MT)", showarrow=False,
                font=dict(size=10, color="white"), bgcolor="#1e3a7b",
                borderpad=4
            )
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.info("Consumption data not available.")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD 2 — Region / Plant DSI + Supply Source Maps
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Dashboard 2":
    import plotly.graph_objects as go

    st.markdown("""
    <style>
    .d2-title {font-size:26px;font-weight:700;color:#1a1a2e;text-align:center;margin-bottom:8px}
    .chart-box {background:white;border:1px solid #dee2e6;border-radius:10px;padding:12px}
    </style>""", unsafe_allow_html=True)
    st.markdown("<div class='d2-title'>8 Reasons of Inventory</div>", unsafe_allow_html=True)

    if not st.session_state.get("final_output_b64"):
        st.warning("⚠️ Please complete the **Final Output** step first.")
        st.stop()

    fo_bytes = b64_to_bytes(st.session_state["final_output_b64"])
    sku_df   = pd.read_excel(BytesIO(fo_bytes), sheet_name="SKU Level")

    def opts2(col): return ["All"] + sorted(sku_df[col].dropna().unique().astype(str).tolist())

    # ── Filters ────────────────────────────────────────────────────────────
    with st.container():
        fc = st.columns([1,1,1,1,1,1,0.6])
        f2_country = fc[0].selectbox("Country",        opts2("Region"),        key="d2_country")
        f2_rm_seg  = fc[1].selectbox("RM Segmentation",opts2("RM Segmentation"),key="d2_seg")
        f2_inco    = fc[2].selectbox("INCO Term",       opts2("INCO Term"),     key="d2_inco")
        f2_cat     = fc[3].selectbox("Category",        opts2("Category"),      key="d2_cat")
        f2_src     = fc[4].selectbox("Source Country",  opts2("Source Country"),key="d2_src")
        f2_rmcg    = fc[5].selectbox("RM Class Group",  opts2("RM Class Group"),key="d2_rmcg")
        fc[6].markdown("<br>", unsafe_allow_html=True)
        fc[6].button("🔍", key="d2_search", use_container_width=True)

    fdf2 = sku_df.copy()
    if f2_country != "All": fdf2 = fdf2[fdf2["Region"]         == f2_country]
    if f2_rm_seg  != "All": fdf2 = fdf2[fdf2["RM Segmentation"]== f2_rm_seg]
    if f2_inco    != "All": fdf2 = fdf2[fdf2["INCO Term"]       == f2_inco]
    if f2_cat     != "All": fdf2 = fdf2[fdf2["Category"]        == f2_cat]
    if f2_src     != "All": fdf2 = fdf2[fdf2["Source Country"]  == f2_src]
    if f2_rmcg    != "All": fdf2 = fdf2[fdf2["RM Class Group"]  == f2_rmcg]

    # Weighted-avg DSI helper
    def weighted_dsi(df, group_col):
        ads_col = "Average Daily Sales (Future)"
        grp = df.groupby(group_col).apply(
            lambda g: round(
                (g["8 Reasons (DSI)"] * g[ads_col]).sum() / g[ads_col].sum()
                if g[ads_col].sum() != 0 else 0, 1)
        ).reset_index(name="8 Reasons (DSI)")
        return grp

    # ── Region & Plant bar charts ──────────────────────────────────────────
    c1, c2 = st.columns(2)
    def make_bar(df, group_col, title):
        grp = weighted_dsi(df, group_col)
        fig = go.Figure(go.Bar(
            x=grp[group_col], y=grp["8 Reasons (DSI)"],
            marker_color="#1e3a7b",
            text=grp["8 Reasons (DSI)"].apply(lambda v: f"{v:.0f}"),
            textposition="inside", textfont=dict(color="gold", size=13, family="Arial Black")
        ))
        fig.update_layout(
            title=dict(text=title, x=0.04, font=dict(size=13, color="#1a1a2e")),
            margin=dict(l=10,r=10,t=40,b=10), height=280,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(gridcolor="#e9ecef", title="DSI (days)"),
            xaxis=dict(tickfont=dict(size=10))
        )
        return fig

    with c1:
        region_fig = make_bar(fdf2, "Region", "Region Wise 8 Reasons DSI")
        st.plotly_chart(region_fig, use_container_width=True)
    with c2:
        plant_fig  = make_bar(fdf2, "PLANT",  "Plant Wise 8 Reasons DSI")
        st.plotly_chart(plant_fig,  use_container_width=True)

    # ── Supply source maps ─────────────────────────────────────────────────
    st.markdown("#### 🌍 Plant Wise 8 Reasons DSI — Supply Source Map")

    COUNTRY_COORDS = {
        "India": (20.6, 78.9), "China": (35.9, 104.2), "VIETNAM": (14.1, 108.3),
        "Thailand": (15.9, 100.9), "Korea": (37.6, 127.0), "South Africa": (-29.0, 25.1),
        "Indonesia": (-0.8, 113.9), "USA": (37.1, -95.7), "Taiwan": (23.7, 121.0),
        "Netherland": (52.1, 5.3), "Netherlands": (52.1, 5.3), "Germany": (51.2, 10.5),
        "BELGIUM": (50.5, 4.5), "Belgium": (50.5, 4.5), "France": (46.2, 2.2),
        "Russia": (61.5, 105.3), "Singapore": (1.4, 103.8), "Saudi Arabia": (23.9, 45.1),
        "S.KOREA": (36.5, 127.8), "Malaysia": (4.2, 101.9), "Japan": (36.2, 138.3),
        "Brazil": (-10.0, -55.0), "Mexico": (23.6, -102.6), "Turkey": (38.9, 35.2),
        "UK": (52.4, -1.9), "Italy": (41.9, 12.6), "Poland": (51.9, 19.1),
        "Local(Imported)": (20.6, 78.9),
    }
    PLANT_COORDS = {
        "Aurangabad": (19.88, 75.34),
        "Ballabgarh": (28.34, 77.33),
        "Pulandian":  (39.40, 121.97),
    }

    plants = sorted(fdf2["PLANT"].dropna().unique().tolist())
    if not plants:
        st.info("No plant data after filters.")
    else:
        map_cols = st.columns(min(len(plants), 3))
        for pi, plant in enumerate(plants):
            plant_df     = fdf2[fdf2["PLANT"] == plant]
            src_countries= plant_df["Source Country"].dropna().unique().tolist()
            plant_lat, plant_lon = PLANT_COORDS.get(plant, (20.0, 78.0))
            plant_dsi    = round((plant_df["8 Reasons (DSI)"] * plant_df["Average Daily Sales (Future)"]).sum()
                                  / plant_df["Average Daily Sales (Future)"].sum()
                                  if plant_df["Average Daily Sales (Future)"].sum() != 0 else 0, 1)

            fig_map = go.Figure()
            for sc in src_countries:
                coords = COUNTRY_COORDS.get(sc)
                if coords:
                    fig_map.add_trace(go.Scattergeo(
                        lon=[coords[1], plant_lon], lat=[coords[0], plant_lat],
                        mode="lines", line=dict(width=1.5, color="red"),
                        showlegend=False
                    ))
                    fig_map.add_trace(go.Scattergeo(
                        lon=[coords[1]], lat=[coords[0]], mode="markers",
                        marker=dict(size=7, color="red", symbol="circle"),
                        showlegend=False, hovertext=sc, hoverinfo="text"
                    ))
            # Plant marker
            fig_map.add_trace(go.Scattergeo(
                lon=[plant_lon], lat=[plant_lat], mode="markers+text",
                marker=dict(size=12, color="#1e3a7b", symbol="star"),
                text=[plant], textposition="top center",
                textfont=dict(size=10, color="#1e3a7b"),
                showlegend=False, hovertext=f"{plant}: {plant_dsi} DSI"
            ))
            fig_map.update_layout(
                title=dict(text=f"<b>{plant}</b>  ({plant_dsi} DSI days)", x=0.5,
                           font=dict(size=13, color="#1a1a2e")),
                geo=dict(
                    showland=True, landcolor="#e8f5e9",
                    showocean=True, oceancolor="#bbdefb",
                    showcountries=True, countrycolor="#bbb",
                    projection_type="natural earth",
                    showframe=False,
                ),
                margin=dict(l=0,r=0,t=36,b=0), height=340, paper_bgcolor="white"
            )
            with map_cols[pi % 3]:
                st.plotly_chart(fig_map, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD 3 — R1–R8 Deep Dive + Segmentation Matrix
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Dashboard 3":
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("""
    <style>
    .d3-title {font-size:26px;font-weight:700;color:#1a1a2e;text-align:center;margin-bottom:8px}
    </style>""", unsafe_allow_html=True)
    st.markdown("<div class='d3-title'>8 Reasons of Inventory — R1–R8 Deep Dive</div>", unsafe_allow_html=True)

    if not st.session_state.get("final_output_b64"):
        st.warning("⚠️ Please complete the **Final Output** step first.")
        st.stop()

    fo_bytes = b64_to_bytes(st.session_state["final_output_b64"])
    sku_df   = pd.read_excel(BytesIO(fo_bytes), sheet_name="SKU Level")

    def opts3(col): return ["All"] + sorted(sku_df[col].dropna().unique().astype(str).tolist())

    # ── Filters ────────────────────────────────────────────────────────────
    fc = st.columns([1,1,1,1,1,0.6])
    f3_plant  = fc[0].selectbox("Plant",           opts3("PLANT"),           key="d3_plant")
    f3_seg    = fc[1].selectbox("RM Segmentation", opts3("RM Segmentation"), key="d3_seg")
    f3_cat    = fc[2].selectbox("Category",         opts3("Category"),        key="d3_cat")
    f3_inco   = fc[3].selectbox("INCO Term",        opts3("INCO Term"),       key="d3_inco")
    f3_plan   = fc[4].selectbox("Planning Cycle",   opts3("Planning cycle"),  key="d3_plan")
    fc[5].markdown("<br>", unsafe_allow_html=True)
    fc[5].button("🔍", key="d3_search", use_container_width=True)

    fdf3 = sku_df.copy()
    if f3_plant != "All": fdf3 = fdf3[fdf3["PLANT"]           == f3_plant]
    if f3_seg   != "All": fdf3 = fdf3[fdf3["RM Segmentation"] == f3_seg]
    if f3_cat   != "All": fdf3 = fdf3[fdf3["Category"]        == f3_cat]
    if f3_inco  != "All": fdf3 = fdf3[fdf3["INCO Term"]       == f3_inco]
    if f3_plan  != "All": fdf3 = fdf3[fdf3["Planning cycle"]  == f3_plan]

    R_COLS   = ["R1 Information Cycle (DSI)","R2 Manufacturing Lot Size (DSI)",
                "R3 Shipping Lot Size (DSI)","R4 Shipping Interval (DSI)",
                "R5 Geography (DSI)","R6 Shipping Variation (DSI)",
                "R7 Supply Variation (DSI)","R8 Demand Variation (DSI)"]
    R_LABELS = ["R1 Info Cycle","R2 Mfg Lot","R3 Ship Lot","R4 Ship Interval",
                "R5 Geography","R6 Ship Var","R7 Supply Var","R8 Demand Var"]
    R_COLORS = ["#1565C0","#1976D2","#1E88E5","#42A5F5",
                "#EF6C00","#F57C00","#FB8C00","#FFA726"]

    n3 = len(fdf3)

    # ── KPI row ────────────────────────────────────────────────────────────
    k_cols = st.columns(4)
    k_cols[0].metric("Total SKUs",          n3)
    k_cols[1].metric("Avg 8 Reasons (DSI)", f"{round(fdf3['8 Reasons (DSI)'].mean(),1) if n3 else 0} days")
    k_cols[2].metric("Avg Safety (DSI)",    f"{round(fdf3['Safety (DSI)'].mean(),1)     if n3 else 0} days")
    k_cols[3].metric("Avg Transit (DSI)",   f"{round(fdf3['Transit (DSI)'].mean(),1)    if n3 else 0} days")
    st.markdown("---")

    c1, c2 = st.columns(2)

    # ── R1–R8 average DSI horizontal bar ──────────────────────────────────
    with c1:
        st.markdown("**Average R1–R8 DSI Contribution**")
        avgs = [round(fdf3[c].mean(), 2) if n3 else 0 for c in R_COLS]
        fig1 = go.Figure(go.Bar(
            y=R_LABELS, x=avgs, orientation="h",
            marker_color=R_COLORS,
            text=[f"{v:.2f}" for v in avgs], textposition="outside"
        ))
        fig1.update_layout(
            margin=dict(l=10,r=60,t=10,b=10), height=320,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(gridcolor="#e9ecef", title="DSI (days)"),
            yaxis=dict(tickfont=dict(size=11))
        )
        st.plotly_chart(fig1, use_container_width=True)

    # ── Stacked DSI by INCO term ──────────────────────────────────────────
    with c2:
        st.markdown("**Cycle / Transit / Safety DSI by INCO Term**")
        grp_inco = fdf3.groupby("INCO Term")[["Cycle (DSI)","Transit (DSI)","Safety (DSI)"]].mean().reset_index()
        fig2 = go.Figure()
        for col, color in [("Cycle (DSI)","#1565C0"),("Transit (DSI)","#42A5F5"),("Safety (DSI)","#FFA726")]:
            fig2.add_trace(go.Bar(name=col, x=grp_inco["INCO Term"],
                                  y=grp_inco[col].round(1), marker_color=color))
        fig2.update_layout(
            barmode="stack", margin=dict(l=10,r=10,t=10,b=10), height=320,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(gridcolor="#e9ecef", title="DSI (days)"),
            legend=dict(orientation="h", y=-0.25)
        )
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    # ── RM Segmentation heatmap matrix ────────────────────────────────────
    with c3:
        st.markdown("**RM Segmentation Matrix — Avg 8 Reasons DSI**")
        st.caption("Rows = Consumption Value (A=High → C=Low) | Cols = Variability (1=Low → 3=High)")
        # Build matrix values, per-cell labels, and hover text
        seg_rows   = ["A","B","C"]
        seg_cols_l = ["1","2","3"]
        matrix, cell_text, hover_text = [], [], []
        for r in seg_rows:
            row_vals, row_text, row_hover = [], [], []
            for cl in seg_cols_l:
                seg = r + cl
                sub = fdf3[fdf3["RM Segmentation"] == seg]
                v   = round(sub["8 Reasons (DSI)"].mean(), 1) if len(sub) else 0
                n_s = len(sub)
                row_vals.append(v)
                row_text.append(f"<b>{v}</b> DSI<br>{n_s} SKUs")
                row_hover.append(f"<b>{seg}</b><br>{v} DSI | {n_s} SKUs")
            matrix.append(row_vals)
            cell_text.append(row_text)
            hover_text.append(row_hover)

        # Highlight A1 cell with a border annotation
        fig3 = go.Figure(go.Heatmap(
            z=matrix,
            x=["Low Var (1)","Med Var (2)","High Var (3)"],
            y=["High Value (A)","Med Value (B)","Low Value (C)"],
            colorscale=[[0,"#e8f5e9"],[0.5,"#1976D2"],[1,"#0d47a1"]],
            text=cell_text,
            hovertext=hover_text,
            hoverinfo="text",
            texttemplate="%{text}",
            textfont=dict(size=12, color="white"),
            showscale=True, colorbar=dict(title="DSI")
        ))
        # Box around A1 (top-left = index [0][0])
        fig3.add_shape(type="rect", x0=-0.5, x1=0.5, y0=1.5, y1=2.5,
                       line=dict(color="#43a047", width=3))
        fig3.update_layout(
            margin=dict(l=10,r=10,t=10,b=10), height=300, paper_bgcolor="white",
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Under Min / Over Max by Plant ──────────────────────────────────────
    with c4:
        st.markdown("**Under Min / Over Max Value by Plant ($M)**")
        grp_pl = fdf3.groupby("PLANT")[["Under Min (Val)","Over Max (Val)"]].sum().reset_index()
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(name="Under Min ($M)", x=grp_pl["PLANT"],
                               y=grp_pl["Under Min (Val)"].round(3), marker_color="#EF5350"))
        fig4.add_trace(go.Bar(name="Over Max ($M)",  x=grp_pl["PLANT"],
                               y=grp_pl["Over Max (Val)"].abs().round(3), marker_color="#42A5F5"))
        fig4.update_layout(
            barmode="group", margin=dict(l=10,r=10,t=10,b=10), height=300,
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(gridcolor="#e9ecef", title="Value ($M)"),
            legend=dict(orientation="h", y=-0.25)
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── SKU-level detail table ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**📋 SKU-Level Detail**")
    display_cols = ["PLANT","Material Code","Material Desc","RM Segmentation","Category",
                    "INCO Term","Planning cycle","8 Reasons (DSI)","Cycle (DSI)",
                    "Transit (DSI)","Safety (DSI)","8 Reasons (Units)",
                    "Under Min (Val)","Over Max (Val)","Historical Data Quality"]
    available = [c for c in display_cols if c in fdf3.columns]
    st.dataframe(
        fdf3[available].reset_index(drop=True)
                       .style.format({col: "{:.2f}" for col in available if fdf3[col].dtype in ["float64","float32"]},
                                     na_rep="—"),
        use_container_width=True, height=380
    )
