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
        "📂 Upload & Validate",
        "⚙️ Intermediate File",
        "📊 Final Output",
        "🔧 Global Settings",
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
            "🐙 Load from GitHub repository URL",
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

    # ── Option 2 : GitHub URL ─────────────────────────────────────────────────
    elif source == "🐙 Load from GitHub repository URL":
        import requests

        st.markdown("""
        Enter the URL of a GitHub repository or subfolder. The tool will look for the
        standard input file names at that location.

        **Examples:**
        - `https://github.com/Manudulux/APAC8reasonsforInventory`
        - `https://github.com/YourOrg/YourRepo/tree/main/data/inputs`
        """)

        gh_url   = st.text_input("GitHub repository / folder URL",
                                  placeholder="https://github.com/Manudulux/APAC8reasonsforInventory")
        subfolder = st.text_input("Subfolder within repo (leave blank for root)",
                                   placeholder="e.g. data/inputs").strip()

        def gh_to_raw(url: str, sub: str) -> str:
            url = url.strip().rstrip("/")
            url = url.replace("https://github.com/", "https://raw.githubusercontent.com/")
            url = url.replace("/tree/", "/")
            parts = url.replace("https://raw.githubusercontent.com/", "").split("/")
            if len(parts) == 2:          # no branch — assume main
                url += "/main"
            if sub:
                url = url.rstrip("/") + "/" + sub.strip("/")
            return url

        if st.button("🔍 Fetch files from GitHub", disabled=not gh_url.strip()):
            raw_base = gh_to_raw(gh_url, subfolder)
            progress = st.progress(0)
            status   = st.empty()
            gh_found, gh_missing = {}, []

            for idx, (key, (label, filename)) in enumerate(FILE_META.items()):
                status.text(f"Fetching {filename}…")
                try:
                    r = requests.get(f"{raw_base}/{filename}", timeout=15)
                    if r.status_code == 200:
                        gh_found[key] = r.content
                    else:
                        gh_missing.append(label)
                except Exception:
                    gh_missing.append(label)
                progress.progress((idx + 1) / len(FILE_META))

            progress.empty(); status.empty()
            st.session_state["_github_files"] = gh_found
            if gh_found:
                st.success(f"✅ {len(gh_found)}/{len(FILE_META)} files loaded from GitHub.")
            if gh_missing:
                st.warning("⚠️ Could not fetch: " + ", ".join(gh_missing))

        if st.session_state.get("_github_files"):
            file_bytes = dict(st.session_state["_github_files"])
            missing_gh = [k for k in FILE_META if k not in file_bytes]
            if missing_gh:
                with st.expander("📎 Upload missing files manually"):
                    cols = st.columns(2)
                    for i, key in enumerate(missing_gh):
                        with cols[i % 2]:
                            f = st.file_uploader(FILE_META[key][0], type=["xlsx", "xls"], key=f"gh_up_{key}")
                            if f:
                                file_bytes[key] = f.read()
                                st.session_state["_github_files"][key] = file_bytes[key]

    # ── Option 3 : manual upload ──────────────────────────────────────────────
    else:
        st.markdown("Upload each of the 12 required Excel files below.")
        cols = st.columns(2)
        for i, (key, (label, _)) in enumerate(FILE_META.items()):
            with cols[i % 2]:
                f = st.file_uploader(label, type=["xlsx", "xls"], key=f"up_{key}")
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
