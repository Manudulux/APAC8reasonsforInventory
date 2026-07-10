import streamlit as st
import pandas as pd
import base64
import os
import glob
import json
import pickle
import re
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

# ── Server persistence ─────────────────────────────────────────────────────────
# These files are written on the Streamlit server after an admin runs the final
# 8 Reasons calculation. They are then automatically loaded for every user so
# dashboards can be opened without repeating the admin pipeline.
PERSIST_ROOT = os.path.join(APP_DIR, "server_outputs")
PLANT_ROOT = os.path.join(PERSIST_ROOT, "plants")
PLANT_REGISTRY_FILE = os.path.join(PLANT_ROOT, "plants.json")
os.makedirs(PLANT_ROOT, exist_ok=True)

# Configured after plant selection.
PERSIST_DIR = None
PERSISTED_FILES = {}
PLANT_STATE_FILE = None
PLANT_CONFIG_FILE = None

PLANT_SCOPED_SESSION_KEYS = [
    "validated_data", "intermediate_data", "rm_seg_b64",
    "final_output_b64", "consumption_merged_b64", "rm_seg_merged_b64",
    "_local_files",
]

PERSISTED_FILE_NAMES = {
    "final_output_b64": "8Reasons_Final_Output.xlsx",
    "consumption_merged_b64": "Consumption_Merged.xlsx",
    "rm_seg_merged_b64": "RM_Segmentation_Merged.xlsx",
}

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


def sanitize_plant_slug(plant_name: str) -> str:
    """Create a stable folder-safe slug for a plant name."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(plant_name).strip()).strip("_")
    return slug or "plant"


def load_plant_registry() -> list:
    """Return configured plants. Aurangabad is seeded by default."""
    default_plants = ["Aurangabad"]
    if not os.path.isfile(PLANT_REGISTRY_FILE):
        os.makedirs(os.path.dirname(PLANT_REGISTRY_FILE), exist_ok=True)
        with open(PLANT_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_plants, f, indent=2)
        return default_plants
    try:
        with open(PLANT_REGISTRY_FILE, "r", encoding="utf-8") as f:
            plants = json.load(f)
        plants = [str(p).strip() for p in plants if str(p).strip()]
        return plants or default_plants
    except Exception:
        return default_plants


def save_plant_registry(plants: list):
    clean = []
    for p in plants:
        name = str(p).strip()
        if name and name not in clean:
            clean.append(name)
    if "Aurangabad" not in clean:
        clean.insert(0, "Aurangabad")
    os.makedirs(os.path.dirname(PLANT_REGISTRY_FILE), exist_ok=True)
    with open(PLANT_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return clean


def current_plant() -> str:
    return st.session_state.get("active_plant", "")


def current_plant_slug() -> str:
    return sanitize_plant_slug(current_plant())


def configure_active_plant_paths():
    """Configure persistence globals for the selected plant."""
    global PERSIST_DIR, PERSISTED_FILES, PLANT_STATE_FILE, PLANT_CONFIG_FILE
    plant = current_plant()
    if not plant:
        return
    plant_dir = os.path.join(PLANT_ROOT, sanitize_plant_slug(plant))
    PERSIST_DIR = os.path.join(plant_dir, "outputs")
    os.makedirs(PERSIST_DIR, exist_ok=True)
    PERSISTED_FILES = {k: os.path.join(PERSIST_DIR, v) for k, v in PERSISTED_FILE_NAMES.items()}
    PLANT_STATE_FILE = os.path.join(plant_dir, "session_state.pkl")
    PLANT_CONFIG_FILE = os.path.join(plant_dir, "global_settings.json")


def reset_plant_scoped_session_state():
    for key in PLANT_SCOPED_SESSION_KEYS:
        st.session_state[key] = None if key != "_local_files" else {}


def persist_plant_session_state():
    """Persist plant-scoped pipeline state; validated upload payloads include file content as base64."""
    if not PLANT_STATE_FILE:
        return []
    os.makedirs(os.path.dirname(PLANT_STATE_FILE), exist_ok=True)
    payload = {key: st.session_state.get(key) for key in PLANT_SCOPED_SESSION_KEYS}
    with open(PLANT_STATE_FILE, "wb") as f:
        pickle.dump(payload, f)
    return [PLANT_STATE_FILE]


def load_plant_session_state():
    reset_plant_scoped_session_state()
    loaded = []
    if PLANT_STATE_FILE and os.path.isfile(PLANT_STATE_FILE):
        try:
            with open(PLANT_STATE_FILE, "rb") as f:
                payload = pickle.load(f)
            for key in PLANT_SCOPED_SESSION_KEYS:
                if key in payload:
                    st.session_state[key] = payload[key]
                    loaded.append(key)
        except Exception:
            pass
    return loaded


def persist_current_outputs():
    """Persist generated output workbooks and plant-scoped session state."""
    saved = []
    for state_key, path in PERSISTED_FILES.items():
        b64_value = st.session_state.get(state_key)
        if b64_value:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b64_to_bytes(b64_value))
            saved.append(path)
    saved.extend(persist_plant_session_state())
    return saved


def load_persisted_outputs_into_session():
    """Load output workbooks for the selected plant."""
    loaded = []
    for state_key, path in PERSISTED_FILES.items():
        if not st.session_state.get(state_key) and os.path.isfile(path):
            with open(path, "rb") as f:
                st.session_state[state_key] = bytes_to_b64(f.read())
            loaded.append(state_key)
    return loaded


def get_plant_global_config(gp_class):
    """Return plant-specific global settings, seeded from the app default when absent."""
    if PLANT_CONFIG_FILE and os.path.isfile(PLANT_CONFIG_FILE):
        try:
            with open(PLANT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    config = gp_class.get_global_config()
    save_plant_global_config(config, gp_class=gp_class, apply_to_runtime=False)
    return config


def save_plant_global_config(config, gp_class=None, apply_to_runtime=True):
    if PLANT_CONFIG_FILE:
        os.makedirs(os.path.dirname(PLANT_CONFIG_FILE), exist_ok=True)
        with open(PLANT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    if apply_to_runtime:
        gp = gp_class or global_parameter_class()
        return gp.update_global_config(config)
    return "Plant configuration saved"


def apply_plant_global_config():
    gp = global_parameter_class()
    config = get_plant_global_config(gp)
    gp.update_global_config(config)
    return config


def render_plant_landing_screen():
    plants = load_plant_registry()
    st.markdown("""
    <style>
    .plant-landing{max-width:760px;margin:4rem auto 1rem auto;padding:2rem;border:1px solid #dbeafe;border-radius:18px;background:#f8fbff;}
    .plant-title{font-size:34px;font-weight:850;color:#0a192f;margin-bottom:.4rem;}
    .plant-subtitle{font-size:16px;color:#475569;}
    </style>
    <div class="plant-landing"><div class="plant-title">Select plant</div><div class="plant-subtitle">All uploads, output files, dashboards and global settings are linked to the selected plant.</div></div>
    """, unsafe_allow_html=True)
    selected = st.selectbox("Plant", plants, index=0, key="plant_landing_select")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Open selected plant", type="primary", use_container_width=True):
            st.session_state["active_plant"] = selected
            configure_active_plant_paths()
            load_plant_session_state()
            load_persisted_outputs_into_session()
            st.rerun()
    with c2:
        with st.expander("Add another plant"):
            new_plant = st.text_input("New plant name", key="new_plant_name")
            if st.button("Add plant", key="add_plant_btn"):
                if new_plant.strip():
                    save_plant_registry(plants + [new_plant.strip()])
                    st.success(f"Added plant: {new_plant.strip()}")
                    st.rerun()
                else:
                    st.warning("Please enter a plant name.")


def render_plant_banner():
    plant = current_plant()
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0a192f,#1d4ed8);color:white;padding:18px 24px;border-radius:14px;margin:0 0 18px 0;box-shadow:0 3px 14px rgba(15,23,42,.18);">
      <div style="font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.78;">Active plant</div>
      <div style="font-size:30px;font-weight:850;line-height:1.15;">🏭 {plant}</div>
      <div style="font-size:13px;opacity:.85;margin-top:4px;">All files, outputs, dashboards and global settings are scoped to this plant.</div>
    </div>
    """, unsafe_allow_html=True)


def first_existing_col(df: pd.DataFrame, candidates):
    """Return the first existing column from candidate names."""
    return next((c for c in candidates if c in df.columns), None)


def to_numeric_safe(values) -> pd.Series:
    """
    Safely convert Excel/text numeric values to float.

    Handles:
    - normal numeric dtypes
    - blanks / NaN
    - currency symbols
    - thousands separators
    - accounting negatives: (1,234.56)
    - US format: 1,234.56
    - European format: 1.234,56
    """
    s = pd.Series(values).copy()
    original_index = s.index

    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce").fillna(0.0)

    s = s.astype(str).str.strip()
    neg_mask = s.str.match(r"^\(.*\)$", na=False)

    # Remove currency symbols and spaces, keep decimal/thousand separators for parsing.
    s = s.str.replace(r"[\$€£¥\s]", "", regex=True)
    s = s.str.replace(r"^\((.*)\)$", r"", regex=True)
    s = s.replace({"": "0", "nan": "0", "None": "0", "NULL": "0", "-": "0"})

    def parse_one(x):
        x = str(x).strip()
        if not x:
            return 0.0
        if "," in x and "." in x:
            # Last separator determines decimal separator.
            if x.rfind(",") > x.rfind("."):
                # European: 1.234,56 -> 1234.56
                x = x.replace(".", "").replace(",", ".")
            else:
                # US: 1,234.56 -> 1234.56
                x = x.replace(",", "")
        elif "," in x:
            # If comma looks like decimal comma, convert it; otherwise remove thousands commas.
            parts = x.split(",")
            if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
                x = x.replace(",", ".")
            else:
                x = x.replace(",", "")
        elif x.count(".") > 1:
            # Multiple dots are most likely thousands separators: 1.234.567 -> 1234567
            x = x.replace(".", "")
        try:
            return float(x)
        except Exception:
            return 0.0

    out = s.map(parse_one).astype(float)
    out.loc[neg_mask] = -out.loc[neg_mask].abs()
    out.index = original_index
    return out.fillna(0.0)


def numeric_sum(df: pd.DataFrame, col: str) -> float:
    """Safe numeric sum for possibly text-formatted Excel columns."""
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(to_numeric_safe(df[col]).sum())


def sku_identity_columns(df: pd.DataFrame):
    """Columns used to count unique SKUs while excluding supplier duplicates."""
    candidates = [
        ["PLANT", "Material Code"],
        ["Plant", "Material Code"],
        ["Plant Name", "Material Code"],
        ["Material Code"],
        ["Material Desc"],
    ]
    for cols in candidates:
        if all(c in df.columns for c in cols):
            return cols
    return []


def unique_sku_count(df: pd.DataFrame) -> int:
    """Count unique SKUs without double-counting multiple supplier/source rows."""
    if df is None or df.empty:
        return 0
    cols = sku_identity_columns(df)
    if cols:
        return int(df[cols].astype(str).drop_duplicates().shape[0])
    return int(df.drop_duplicates().shape[0])


def inventory_value_dollars(df: pd.DataFrame) -> float:
    """
    Correct 8 Reasons Inventory Value calculation in dollars.

    Business formula requested:
        SUM(row-level 8 Reasons Units × row-level MAP) / 100

    The result is displayed as a full dollar amount, for example:
        $ 12,135,518
    """
    if df is None or df.empty:
        return 0.0

    units_col = first_existing_col(df, [
        "8 Reasons (Units)",
        "8 Reasons Units",
        "8 Reasons Inventory Units",
        "Target Inventory Units",
        "Inventory Units",
    ])
    price_col = first_existing_col(df, [
        "MAP",
        "Material Average Price",
        "Material Average Price per unit ($)",
        "Average Price",
        "Unit Price",
        "Price",
    ])

    if units_col and price_col:
        units = to_numeric_safe(df[units_col])
        price = to_numeric_safe(df[price_col])
        return round(float((units * price).sum() / 100), 0)

    # Fallback: if a value column already exists, sum it as dollars.
    value_col = first_existing_col(df, [
        "8 Reasons Inventory Value",
        "8 Reasons Value",
        "8 Reasons (Value)",
        "Inventory Value",
        "Value",
    ])
    if value_col:
        return round(float(to_numeric_safe(df[value_col]).sum()), 0)

    return 0.0


def inventory_value_million(df: pd.DataFrame) -> float:
    """
    Backward-compatible wrapper.

    Despite the historical function name, Dashboard 1 now uses this value as
    full dollars based on:
        SUM(row-level 8 Reasons Units × row-level MAP) / 100
    """
    return inventory_value_dollars(df)


def inventory_value_detail_by_material(df: pd.DataFrame):
    """
    Build a material-level audit table for Dashboard 1.

    The KPI shown in Dashboard 1 is exactly the grand total of:
        Formula numerator = 8 Reasons Units × MAP
        8 Reasons Inventory Value ($) = Formula numerator / 100

    Returns:
        detail_df: material-level table including a final TOTAL row
        diagnostics: dictionary describing source columns and data quality checks
    """
    diagnostics = {
        "units_col": None,
        "price_col": None,
        "source_rows": 0,
        "unique_skus": 0,
        "materials": 0,
        "zero_or_blank_units_rows": 0,
        "zero_or_blank_map_rows": 0,
        "calculated_total_dollars": 0.0,
    }

    if df is None or df.empty:
        return pd.DataFrame(), diagnostics

    units_col = first_existing_col(df, [
        "8 Reasons (Units)",
        "8 Reasons Units",
        "8 Reasons Inventory Units",
        "Target Inventory Units",
        "Inventory Units",
    ])
    price_col = first_existing_col(df, [
        "MAP",
        "Material Average Price",
        "Material Average Price per unit ($)",
        "Average Price",
        "Unit Price",
        "Price",
    ])

    diagnostics["units_col"] = units_col
    diagnostics["price_col"] = price_col
    diagnostics["source_rows"] = int(len(df))
    diagnostics["unique_skus"] = unique_sku_count(df)

    if not units_col or not price_col:
        return pd.DataFrame(), diagnostics

    work = df.copy()
    work["_8R_Units"] = to_numeric_safe(work[units_col])
    work["_MAP"] = to_numeric_safe(work[price_col])
    work["_Formula_Numerator"] = work["_8R_Units"] * work["_MAP"]
    work["_8R_Value_$"] = work["_Formula_Numerator"] / 100

    diagnostics["zero_or_blank_units_rows"] = int((work["_8R_Units"] == 0).sum())
    diagnostics["zero_or_blank_map_rows"] = int((work["_MAP"] == 0).sum())
    diagnostics["calculated_total_dollars"] = round(float(work["_8R_Value_$"].sum()), 0)

    material_code_col = first_existing_col(work, ["Material Code", "Material", "RM Code", "Item Code"])
    material_desc_col = first_existing_col(work, ["Material Desc", "Raw Material Desc", "Raw Material Description", "RM Description"])
    plant_col = first_existing_col(work, ["PLANT", "Plant", "Plant Name"])
    seg_col = first_existing_col(work, ["RM Segmentation", "Segmentation"])

    group_cols = []
    if material_code_col:
        group_cols.append(material_code_col)
    if material_desc_col and material_desc_col not in group_cols:
        group_cols.append(material_desc_col)
    if not group_cols:
        work["_Material"] = "All materials"
        group_cols = ["_Material"]

    diagnostics["materials"] = int(work[group_cols].astype(str).drop_duplicates().shape[0])

    rows = []
    for keys, sub in work.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_dict = dict(zip(group_cols, keys))

        units_sum = float(sub["_8R_Units"].sum())
        numerator_sum = float(sub["_Formula_Numerator"].sum())
        value_sum = float(sub["_8R_Value_$"].sum())
        weighted_map = float(numerator_sum / units_sum) if units_sum else 0.0

        rows.append({
            "Material Code": key_dict.get(material_code_col, "") if material_code_col else "",
            "Material Desc": key_dict.get(material_desc_col, key_dict.get("_Material", "")) if material_desc_col or "_Material" in key_dict else "",
            "Plants": int(sub[plant_col].astype(str).nunique()) if plant_col else 0,
            "RM Segmentation": (
                sub[seg_col].dropna().astype(str).iloc[0]
                if seg_col and sub[seg_col].dropna().astype(str).nunique() == 1
                else ("Multiple" if seg_col and sub[seg_col].dropna().astype(str).nunique() > 1 else "")
            ),
            "Unique SKUs": unique_sku_count(sub),
            "Source Rows": int(len(sub)),
            "8 Reasons Units": units_sum,
            "Weighted MAP": weighted_map,
            "Formula Numerator (Units × MAP)": numerator_sum,
            "8 Reasons Inventory Value ($)": value_sum,
        })

    detail_df = pd.DataFrame(rows)
    if detail_df.empty:
        return detail_df, diagnostics

    total_value = float(detail_df["8 Reasons Inventory Value ($)"].sum())
    detail_df["Share of Total Value"] = detail_df["8 Reasons Inventory Value ($)"] / total_value if total_value else 0.0
    detail_df = detail_df.sort_values("8 Reasons Inventory Value ($)", ascending=False).reset_index(drop=True)

    total_units = float(detail_df["8 Reasons Units"].sum())
    total_numerator = float(detail_df["Formula Numerator (Units × MAP)"].sum())
    total_row = {
        "Material Code": "TOTAL",
        "Material Desc": "All selected materials",
        "Plants": int(work[plant_col].astype(str).nunique()) if plant_col else 0,
        "RM Segmentation": "",
        "Unique SKUs": unique_sku_count(work),
        "Source Rows": int(len(work)),
        "8 Reasons Units": total_units,
        "Weighted MAP": float(total_numerator / total_units) if total_units else 0.0,
        "Formula Numerator (Units × MAP)": total_numerator,
        "8 Reasons Inventory Value ($)": total_value,
        "Share of Total Value": 1.0 if total_value else 0.0,
    }
    detail_df = pd.concat([detail_df, pd.DataFrame([total_row])], ignore_index=True)
    return detail_df, diagnostics


# ── Plant selection gate ───────────────────────────────────────────────────────
if "active_plant" not in st.session_state:
    st.session_state["active_plant"] = None

if not st.session_state["active_plant"]:
    render_plant_landing_screen()
    st.stop()

configure_active_plant_paths()
load_plant_session_state()
load_persisted_outputs_into_session()
apply_plant_global_config()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Goodyear_logo.svg/200px-Goodyear_logo.svg.png",
        width=140,
    )
    st.title("8 Reasons Inventory")
    st.markdown(f"**Active plant:** 🏭 `{current_plant()}`")
    if st.button("Change plant", key="change_plant_btn"):
        persist_plant_session_state()
        st.session_state["active_plant"] = None
        reset_plant_scoped_session_state()
        st.rerun()
    st.markdown("---")

    st.markdown("### Dashboards")
    dashboard_page = st.radio("Navigation", [
        "🏠 Home",
        "📊 Dashboard 1",
        "🗺️ Dashboard 2",
        "📈 Dashboard 3",
        "🔬 Dashboard 4",
    ], key="dashboard_navigation")
    page = dashboard_page

    st.markdown("---")
    with st.expander("🔐 For Admin only", expanded=False):
        if "admin_unlocked" not in st.session_state:
            st.session_state["admin_unlocked"] = False

        if not st.session_state["admin_unlocked"]:
            admin_password = st.text_input(
                "Admin password",
                type="password",
                key="admin_password_input",
                help="Enter the admin password to access Global Settings, Upload & Validate, Intermediate File, and Final Output.",
            )
            if st.button("Unlock admin section", key="admin_unlock_button"):
                if admin_password == "Aletheia":
                    st.session_state["admin_unlocked"] = True
                    st.success("Admin section unlocked.")
                else:
                    st.error("Incorrect password.")

        if st.session_state["admin_unlocked"]:
            st.caption("✅ Admin access unlocked")
            admin_page = st.radio("Admin navigation", [
                "— Select admin page —",
                "🔧 Global Settings",
                "📂 Upload & Validate",
                "⚙️ Intermediate File",
                "📊 Final Output",
            ], key="admin_navigation")
            if admin_page != "— Select admin page —":
                page = admin_page

            if st.button("Lock admin section", key="admin_lock_button"):
                # Important: do NOT write to st.session_state["admin_navigation"] here.
                # That key belongs to the Admin navigation radio widget. Streamlit
                # raises StreamlitAPIException if a widget-backed session_state key
                # is modified after the widget has been instantiated in the same run.
                st.session_state["admin_unlocked"] = False
                page = dashboard_page
                st.info("Admin section locked.")

    st.markdown("---")
    st.markdown("**Pipeline status**")
    st.markdown("✅ Validated"         if st.session_state["validated_data"]   else "⬜ Not yet validated")
    st.markdown("✅ Intermediate ready" if st.session_state["intermediate_data"] else "⬜ Not yet generated")
    st.markdown("✅ Final output ready" if st.session_state["final_output_b64"] else "⬜ Not yet calculated")
    if any(os.path.isfile(p) for p in PERSISTED_FILES.values()):
        st.caption(f"Server output available: {PERSIST_DIR}")
    st.markdown("---")
    st.caption("Goodyear IMS v2 — Streamlit Edition")

render_plant_banner()

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# SHARED FILTERS — used by all dashboards
# ══════════════════════════════════════════════════════════════════════════════
def render_shared_filters(sku_df):
    """Render shared filters at the top of any dashboard. Returns filtered df and filter values."""
    st.markdown("""
    <style>
    .shared-filter-box {
        background: #eef2ff;
        border: 1px solid #c7d2fe;
        border-radius: 10px;
        padding: 12px 16px 6px 16px;
        margin-bottom: 14px;
    }
    .shared-filter-title {
        font-size: 12px;
        font-weight: 700;
        color: #3730a3;
        text-transform: uppercase;
        letter-spacing: .06em;
        margin-bottom: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    def opts(col):
        return ["All"] + sorted(sku_df[col].dropna().unique().astype(str).tolist())

    st.markdown("<div class='shared-filter-box'>", unsafe_allow_html=True)
    st.markdown("<div class='shared-filter-title'>🔎 Global Filters — applied to all dashboards</div>", unsafe_allow_html=True)
    fc = st.columns(5)
    f_country = fc[0].selectbox("Country",           opts("Region"),          key="sf_country")
    f_rm_desc = fc[1].selectbox("Raw Material Desc", ["All"] + sorted(sku_df["Material Desc"].dropna().unique().astype(str).tolist()), key="sf_rm")
    f_rm_seg  = fc[2].selectbox("RM Segmentation",   opts("RM Segmentation"), key="sf_seg")
    f_inco    = fc[3].selectbox("INCO Term",          opts("INCO Term"),       key="sf_inco")
    f_plan    = fc[4].selectbox("Planning Cycle",     opts("Planning cycle"),  key="sf_plan")
    fc2 = st.columns(4)
    f_plant   = fc2[0].selectbox("Plant Name",        opts("PLANT"),           key="sf_plant")
    f_cat     = fc2[1].selectbox("Category",          opts("Category"),        key="sf_cat")
    f_src     = fc2[2].selectbox("Source Country",    opts("Source Country"),  key="sf_src")
    f_rmcg    = fc2[3].selectbox("RM Class Group",    opts("RM Class Group"),  key="sf_rmcg")
    st.markdown("</div>", unsafe_allow_html=True)

    fdf = sku_df.copy()
    if f_country != "All": fdf = fdf[fdf["Region"]          == f_country]
    if f_rm_seg  != "All": fdf = fdf[fdf["RM Segmentation"] == f_rm_seg]
    if f_inco    != "All": fdf = fdf[fdf["INCO Term"]        == f_inco]
    if f_plan    != "All":
        try:
            fdf = fdf[fdf["Planning cycle"] == int(f_plan)]
        except (ValueError, TypeError):
            fdf = fdf[fdf["Planning cycle"].astype(str) == str(f_plan)]
    if f_plant   != "All": fdf = fdf[fdf["PLANT"]            == f_plant]
    if f_cat     != "All": fdf = fdf[fdf["Category"]         == f_cat]
    if f_src     != "All": fdf = fdf[fdf["Source Country"]   == f_src]
    if f_rmcg    != "All": fdf = fdf[fdf["RM Class Group"]   == f_rmcg]
    if f_rm_desc != "All": fdf = fdf[fdf["Material Desc"]    == f_rm_desc]

    return fdf, f_country, f_rm_desc, f_rm_seg, f_inco, f_plan, f_plant, f_cat, f_src, f_rmcg


def weighted_dsi_scalar(df):
    """Weighted-average DSI using Average Daily Sales (Future) as weight. Same as D2/D3."""
    ads_col = "Average Daily Sales (Future)"
    if df.empty or ads_col not in df.columns or "8 Reasons (DSI)" not in df.columns:
        return 0.0
    denom = df[ads_col].sum()
    if denom == 0:
        return round(float(df["8 Reasons (DSI)"].mean()), 1) if len(df) else 0.0
    return round(float((df["8 Reasons (DSI)"] * df[ads_col]).sum() / denom), 1)



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
        Active plant: `{current_plant()}`
        """)

        if st.button("🔍 Scan directory for input files"):
            found = scan_local_files(APP_DIR)
            st.session_state["_local_files"] = found
            persist_plant_session_state()

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
                            f = st.file_uploader(label, type=["xlsx", "xls"], key=f"local_up_{current_plant_slug()}_{key}")
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
            key=f"multi_upload_{current_plant_slug()}",
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
                    persist_plant_session_state()
                    st.success(f"✅ All files validated successfully for {current_plant()}!")
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
                apply_plant_global_config()
                validated_data      = st.session_state["validated_data"]
                intermediate_output = GenerateIntermediateOutput(validated_data).generate_intermediate_response()
                response            = IntermediateFile(validated_data).make_response(intermediate_output)

                if isinstance(response, str) and response.lower().startswith("error"):
                    st.error(f"❌ {response}")
                else:
                    st.session_state["intermediate_data"] = response
                    st.session_state["rm_seg_b64"]        = response.get("RM_Segmentation_Output", "")
                    st.session_state["final_output_b64"]  = None
                    persist_plant_session_state()
                    st.success(f"✅ Intermediate file generated for {current_plant()}!")

            except Exception as e:
                import traceback
                st.error(f"Error during intermediate calculation: {e}")
                st.code(traceback.format_exc())

    if st.session_state.get("intermediate_data"):
        st.success("✅ Intermediate output is ready.")
        st.markdown("---")

        # ── Build list of all sheets (regular + RM Segmentation) ────────────
        all_sheets = []   # list of {"name": str, "session_key": str, "b64": str}
        for sheet in st.session_state["intermediate_data"].get("Sheets", []):
            b64  = sheet.get("Data", "")
            name = sheet.get("Variable", "")
            if b64 and name:
                all_sheets.append({"name": name, "b64": b64, "is_rm_seg": False})
        rm_b64 = st.session_state.get("rm_seg_b64", "")
        if rm_b64:
            all_sheets.append({"name": "RM_Segmentation_Output", "b64": rm_b64, "is_rm_seg": True})

        # ── Tab layout: Download | Upload & Override ──────────────────────
        tab_dl, tab_ul = st.tabs(["📥 Download Intermediate Sheets", "📤 Upload & Override Sheets"])

        # ── Download tab ──────────────────────────────────────────────────
        with tab_dl:
            st.markdown(
                "Download any sheet, edit it in Excel, then upload it back in the **Upload & Override** tab "
                "before running the Final Output."
            )
            cols = st.columns(3)
            for i, s in enumerate(all_sheets):
                with cols[i % 3]:
                    make_download_button(s["b64"], f"{s['name']}.xlsx", f"⬇ {s['name']}")

        # ── Upload & Override tab ─────────────────────────────────────────
        with tab_ul:
            st.markdown("""
            Upload modified versions of **Supply Parameters** or **Sourcing Data**.
            The uploaded file will **replace** the generated sheet before the Final Output runs.
            """)

            EDITABLE_SHEETS = {"Supply_Parameters", "Sourcing_Data"}
            editable = [s for s in all_sheets if s["name"] in EDITABLE_SHEETS]
            override_cols = st.columns(len(editable))
            any_overridden = False

            for i, s in enumerate(editable):
                with override_cols[i]:
                    uf = st.file_uploader(
                        f"Replace **{s['name']}**",
                        type=["xlsx", "xls"],
                        key=f"override_{s['name']}",
                    )
                    if uf:
                        new_b64 = base64.b64encode(uf.read()).decode("utf-8")
                        any_overridden = True
                        sheets_list = st.session_state["intermediate_data"]["Sheets"]
                        for sheet in sheets_list:
                            if sheet.get("Variable") == s["name"]:
                                sheet["Data"] = new_b64
                                break
                        st.success(f"✅ {s['name']} overridden")

            if any_overridden:
                st.info(
                    "✏️ One or more sheets have been overridden. "
                    "Proceed to **Final Output** to run the calculation with your modified data."
                )
            else:
                st.caption("No overrides applied yet — all sheets will use the generated values.")

        st.markdown("---")
        st.info("👈 Proceed to **Final Output** in the sidebar.")


# ══════════════════════════════════════════════════════════════════════════════
# FINAL OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Final Output":
    st.title("📊 Final Output — 8 Reasons Calculation")

    if not st.session_state.get("intermediate_data") and not st.session_state.get("final_output_b64"):
        st.warning("⚠️ No server output is available yet. An admin must run the pipeline once from the admin section.")
        st.stop()

    st.markdown("""
    Runs the full **8 Reasons** calculation and produces:
    - **SKU-level** DSI and unit targets (Cycle / Transit / Safety / 8 Reasons / Min / Max / On-Hand)
    - **Aggregated views** by Region, Plant, INCO Term, Planning Cycle, RM Segmentation
    - **Under Min / Over Max** value analysis
    """)

    if not st.session_state.get("intermediate_data"):
        st.info("A server-side final output is already available. To regenerate it, first complete the admin Intermediate File step.")

    if st.session_state.get("intermediate_data") and st.button("🚀 Run 8 Reasons Calculation", type="primary"):
        with st.spinner("Running 8 Reasons calculation… (may take several minutes for large datasets)"):
            try:
                apply_plant_global_config()
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
                    saved_files = persist_current_outputs()
                    st.success("✅ 8 Reasons calculation complete and saved permanently on the server!")
                    if saved_files:
                        st.caption("Saved files: " + ", ".join(os.path.basename(p) for p in saved_files))
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
    config   = get_plant_global_config(gp_class)
    params   = config["global_parameters"][0]
    st.info(f"These global settings are scoped to plant: **{current_plant()}**")

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

        st.subheader("📦 RM Segmentation")
        st.caption("Plant-specific RM segmentation thresholds. Defaults: Variance 1=0–41, 2=41–60, 3=60–100; Segment A=0–80, B=80–96, C=96–100.")
        rm_seg = params.get("rm_segmentation", {}) or {}
        def _rm_default(section, band, key, default):
            item = (rm_seg.get(section, {}) or {}).get(str(band), {})
            return float(item.get(key, default)) if isinstance(item, dict) else float(default)
        vc, sc = st.columns(2)
        with vc:
            st.markdown("**Variance bands**")
            v1_min = st.number_input("Variance 1 min", value=_rm_default("variance", "1", "min", 0), min_value=0.0, max_value=100.0, key="rm_v1_min")
            v1_max = st.number_input("Variance 1 max", value=_rm_default("variance", "1", "max", 41), min_value=0.0, max_value=100.0, key="rm_v1_max")
            v2_min = st.number_input("Variance 2 min", value=_rm_default("variance", "2", "min", 41), min_value=0.0, max_value=100.0, key="rm_v2_min")
            v2_max = st.number_input("Variance 2 max", value=_rm_default("variance", "2", "max", 60), min_value=0.0, max_value=100.0, key="rm_v2_max")
            v3_min = st.number_input("Variance 3 min", value=_rm_default("variance", "3", "min", 60), min_value=0.0, max_value=100.0, key="rm_v3_min")
            v3_max = st.number_input("Variance 3 max", value=_rm_default("variance", "3", "max", 100), min_value=0.0, max_value=100.0, key="rm_v3_max")
        with sc:
            st.markdown("**ABC segment bands**")
            a_min = st.number_input("Segment A min", value=_rm_default("segment", "A", "min", 0), min_value=0.0, max_value=100.0, key="rm_a_min")
            a_max = st.number_input("Segment A max", value=_rm_default("segment", "A", "max", 80), min_value=0.0, max_value=100.0, key="rm_a_max")
            b_min = st.number_input("Segment B min", value=_rm_default("segment", "B", "min", 80), min_value=0.0, max_value=100.0, key="rm_b_min")
            b_max = st.number_input("Segment B max", value=_rm_default("segment", "B", "max", 96), min_value=0.0, max_value=100.0, key="rm_b_max")
            c_min = st.number_input("Segment C min", value=_rm_default("segment", "C", "min", 96), min_value=0.0, max_value=100.0, key="rm_c_min")
            c_max = st.number_input("Segment C max", value=_rm_default("segment", "C", "max", 100), min_value=0.0, max_value=100.0, key="rm_c_max")

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
            "rm_segmentation": {
                "variance": {
                    "1": {"min": v1_min, "max": v1_max},
                    "2": {"min": v2_min, "max": v2_max},
                    "3": {"min": v3_min, "max": v3_max},
                },
                "segment": {
                    "A": {"min": a_min, "max": a_max},
                    "B": {"min": b_min, "max": b_max},
                    "C": {"min": c_min, "max": c_max},
                },
            },
            "service_level_mapping": params.get("service_level_mapping", {}),
            "production_days": new_prod_days,
            "price_conversion": {"USD_value": usd_value},
            "default_values":  {"transit_time_local": tt_local, "transit_time_imported": tt_imported,
                                 "shipping_interval_local": si_local, "shipping_interval_imported": si_imported,
                                 "supply_reliability": supply_rel},
        }]}
        is_valid, msg = gp_class.validate_global_config(new_config)
        if is_valid:
            runtime_msg = save_plant_global_config(new_config, gp_class=gp_class, apply_to_runtime=True)
            st.success(f"✅ Plant-specific settings saved for {current_plant()}. {runtime_msg}")
        else:
            st.error(f"❌ Validation errors: {msg}")

    with st.expander("📋 Current plant configuration (raw JSON)"):
        st.json(get_plant_global_config(gp_class))

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
    .kpi-aop   {font-size:11px;font-weight:600}
    .seg-card  {border-radius:10px;padding:10px 12px;margin-bottom:6px;min-height:165px;position:relative}
    .seg-title {font-size:16px;font-weight:700;color:#1a1a2e}
    .seg-line  {font-size:11px;color:#333;margin:1px 0}
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

    # ── Shared Filters ──────────────────────────────────────────────────────
    fdf, f_country, f_rm_desc, f_rm_seg, f_inco, f_plan, f_plant, f_cat, f_src, f_rmcg = render_shared_filters(sku_df)

    # ── AOP Manual Targets ─────────────────────────────────────────────────
    with st.expander("🎯 AOP Targets (manual entry)", expanded=True):
        aop_cols = st.columns(3)
        aop_dsi  = aop_cols[0].number_input("AOP Target DSI (days)",        min_value=0.0, value=45.0,  step=0.5,  format="%.1f",  key="aop_dsi_input")
        aop_val  = aop_cols[1].number_input("AOP Target Value ($)",          min_value=0.0, value=10_000_000.0, step=100_000.0, format="%.0f", key="aop_val_dollars_input")
        aop_tons = aop_cols[2].number_input("AOP Target Tonnage (MT)",       min_value=0.0, value=500.0, step=10.0, format="%.0f",  key="aop_tons_input")

    n_total   = unique_sku_count(fdf)
    avg_dsi   = weighted_dsi_scalar(fdf)
    tot_units = numeric_sum(fdf, "8 Reasons (Units)")
    # 8 Reasons Inventory Value: row-level Units × row-level MAP.
    # This intentionally removes the old formula: total units × average MAP.
    tot_val   = inventory_value_dollars(fdf)
    value_detail_df, value_diag = inventory_value_detail_by_material(fdf)
    # Force the KPI to reconcile exactly with the TOTAL row in the audit table.
    if value_diag.get("calculated_total_dollars", 0.0):
        tot_val = value_diag["calculated_total_dollars"]
    tot_tons  = round(tot_units / 1000, 1) if n_total else 0

    pct_dsi  = round(avg_dsi  / aop_dsi  * 100, 1) if aop_dsi  > 0 else 0.0
    pct_val  = round(tot_val  / aop_val  * 100, 1) if aop_val  > 0 else 0.0
    pct_tons = round(tot_tons / aop_tons * 100, 1) if aop_tons > 0 else 0.0

    left_col, right_col = st.columns([1.1, 1])

    with left_col:
        st.markdown("#### 🎯 Targets vs AOP")
        k1, k2, k3 = st.columns(3)

        def kpi_card(col, title, sub1, value, aop_label, pct):
            color = "#28a745" if pct <= 100 else "#dc3545"
            col.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{title}</div>
                <div class="kpi-sub">—</div>
                <div class="kpi-label">{sub1}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">AOP: {aop_label}</div>
                <div class="kpi-aop" style="color:{color}">{pct}% of AOP</div>
            </div>""", unsafe_allow_html=True)

        kpi_card(k1, "Plant AOP DSI (days)",        "8 Reasons Inventory DSI",     f"{avg_dsi} days",     f"{aop_dsi:.1f} days", pct_dsi)
        kpi_card(k2, "Plant AOP Value ($)",          "8 Reasons Inventory Value",   f"$ {tot_val:,.0f}",   f"$ {aop_val:,.0f}",   pct_val)
        kpi_card(k3, "Plant AOP Tonnage (MT)",       "8 Reasons Inventory Tonnage", f"{tot_tons:,.1f} MT", f"{aop_tons:,.0f} MT", pct_tons)

        with st.expander("🔎 8 Reasons Inventory Value — calculation detail", expanded=True):
            st.markdown("""
            **Calculation used for the value KPI**

            The **8 Reasons Inventory Value** is calculated at row level and then summed:

            `Row numerator = 8 Reasons Units × MAP`

            `Row value ($) = Row numerator / 100`

            `Total 8 Reasons Inventory Value ($) = SUM(Row value $)`

            The material table below uses the **same filtered dataset** as Dashboard 1. The **TOTAL** row reconciles to the KPI card above.
            """)

            diag_cols = st.columns(4)
            diag_cols[0].metric("Rows used", f"{value_diag.get('source_rows', 0):,}")
            diag_cols[1].metric("Unique SKUs", f"{value_diag.get('unique_skus', 0):,}")
            diag_cols[2].metric("Materials", f"{value_diag.get('materials', 0):,}")
            diag_cols[3].metric("Reconciled total", f"$ {value_diag.get('calculated_total_dollars', 0.0):,.0f}")

            st.caption(
                f"Units column used: `{value_diag.get('units_col')}` | "
                f"MAP/price column used: `{value_diag.get('price_col')}` | "
                f"Rows with zero/blank units: {value_diag.get('zero_or_blank_units_rows', 0):,} | "
                f"Rows with zero/blank MAP: {value_diag.get('zero_or_blank_map_rows', 0):,}"
            )

            if value_detail_df.empty:
                st.warning("Unable to build the detail table because the required Units and/or MAP columns were not found.")
            else:
                show_all_materials = st.checkbox("Show all materials", value=False, key="d1_value_show_all_materials")
                table_to_show = value_detail_df.copy() if show_all_materials else pd.concat([
                    value_detail_df[value_detail_df["Material Code"] != "TOTAL"].head(25),
                    value_detail_df[value_detail_df["Material Code"] == "TOTAL"]
                ], ignore_index=True)

                st.dataframe(
                    table_to_show.style.format({
                        "Plants": "{:,.0f}",
                        "Unique SKUs": "{:,.0f}",
                        "Source Rows": "{:,.0f}",
                        "8 Reasons Units": "{:,.2f}",
                        "Weighted MAP": "{:,.4f}",
                        "Formula Numerator (Units × MAP)": "{:,.2f}",
                        "8 Reasons Inventory Value ($)": "$ {:,.0f}",
                        "Share of Total Value": "{:.1%}",
                    }),
                    use_container_width=True,
                    height=420,
                )

                st.download_button(
                    "⬇ Download value detail by material (CSV)",
                    data=value_detail_df.to_csv(index=False).encode("utf-8"),
                    file_name="dashboard1_8_reasons_inventory_value_detail.csv",
                    mime="text/csv",
                    key="d1_value_detail_csv",
                )

        st.markdown("<br>", unsafe_allow_html=True)

        SEG_COLORS = {
            "A1": "#a5d6a7", "A2": "#c8e6c9", "A3": "#e8f5e9",
            "B1": "#b3e5fc", "B2": "#e1f5fe", "B3": "#f0f9ff",
            "C1": "#e1bee7", "C2": "#f3e5f5", "C3": "#fce4ec",
        }
        segs = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
        cols3 = st.columns(3)
        for i, seg in enumerate(segs):
            sub = fdf[fdf["RM Segmentation"] == seg]
            n   = unique_sku_count(sub)
            pct = round(n / n_total * 100, 1) if n_total else 0
            tot_qty  = round(numeric_sum(sub, "8 Reasons (Units)") / 1000, 1)
            # RM Segmentation inventory value: row-level Units × row-level MAP.
            tot_inv  = inventory_value_dollars(sub) if n else 0
            tot_sp   = round(tot_inv, 0) if n else 0
            svc      = round(sub["Service Level (%)"].mean(), 0) if n else 0
            var      = round(sub["R8 Demand Variation (DSI)"].mean(), 1) if n else 0
            bg       = SEG_COLORS.get(seg, "#f5f5f5")
            with cols3[i % 3]:
                st.markdown(f"""
                <div class="seg-card" style="background:{bg}">
                    <div class="seg-title">{seg}
                        <span style="float:right;font-size:11px;color:#555">⬆ ⬇</span>
                    </div>
                    <div class="seg-line"># of SKUs: <b>{n}/{n_total}</b> ({pct}%)</div>
                    <div class="seg-line">Total req qty: <b>{tot_qty:,.1f}MT</b></div>
                    <div class="seg-line">Total inv: <b>$ {tot_inv:,.0f}</b></div>
                    <div class="seg-line">Total spend: <b>$ {tot_sp:,.0f}</b></div>
                    <div class="seg-line">Service level: <b>{svc:.0f}%</b></div>
                    <div class="seg-line">Average variability: <b>{var:.1f}</b></div>
                </div>""", unsafe_allow_html=True)

    with right_col:
        st.markdown("#### 📅 Last 12M Consumption")
        chart_type = st.selectbox("", ["Bar", "Line"], key="d1_ctype", label_visibility="collapsed")

        if not cons_df.empty and "Post Date" in cons_df.columns:
            c_filt = cons_df.copy()

            def apply_first_match(df, selected_value, candidate_cols, numeric=False):
                if selected_value == "All":
                    return df
                for col in candidate_cols:
                    if col in df.columns:
                        if numeric:
                            return df[df[col].astype(str) == str(selected_value)]
                        return df[df[col].astype(str).str.strip() == str(selected_value).strip()]
                return df

            c_filt = apply_first_match(c_filt, f_country, ["Region", "Country"])
            c_filt = apply_first_match(c_filt, f_plant,   ["Plant Name", "PLANT", "Plant"])
            c_filt = apply_first_match(c_filt, f_cat,     ["Category"])
            c_filt = apply_first_match(c_filt, f_src,     ["Source Country", "Source"])
            c_filt = apply_first_match(c_filt, f_rmcg,    ["RM Class Group", "RM Class Group "])
            c_filt = apply_first_match(c_filt, f_inco,    ["INCO Term", "Incoterm", "INCO"])
            c_filt = apply_first_match(c_filt, f_plan,    ["Planning cycle", "Planning Cycle"], numeric=True)
            c_filt = apply_first_match(c_filt, f_rm_seg,  ["Segmentation", "RM Segmentation"])

            if f_rm_desc != "All":
                desc_cols = [c for c in ["Material Desc", "Raw Material Desc", "Raw Material Description", "RM Description"] if c in c_filt.columns]
                code_cols = [c for c in ["Material Code", "Material", "Item Code", "RM Code"] if c in c_filt.columns]
                material_codes = []
                if "Material Code" in fdf.columns:
                    material_codes = fdf.loc[
                        fdf["Material Desc"].astype(str).str.strip() == str(f_rm_desc).strip(),
                        "Material Code"
                    ].dropna().astype(str).str.strip().unique().tolist()

                if desc_cols or (code_cols and material_codes):
                    mask = pd.Series(False, index=c_filt.index)
                    for col in desc_cols:
                        mask = mask | (c_filt[col].astype(str).str.strip() == str(f_rm_desc).strip())
                    if material_codes:
                        for col in code_cols:
                            mask = mask | c_filt[col].astype(str).str.strip().isin(material_codes)
                    c_filt = c_filt[mask]

            c_filt["Post Date"] = pd.to_datetime(c_filt["Post Date"], dayfirst=True, errors="coerce")
            c_filt = c_filt[c_filt["Post Date"].notna()].copy()
            c_filt["Month"]     = c_filt["Post Date"].dt.to_period("M")
            qty_col = "Movement Qty" if "Movement Qty" in c_filt.columns else ("Consumption Qty" if "Consumption Qty" in c_filt.columns else None)
            monthly = (c_filt.groupby("Month")[qty_col]
                       .sum().abs().reset_index()
                       .sort_values("Month").tail(12)) if qty_col else pd.DataFrame(columns=["Month", "MonthStr"])
            if not monthly.empty:
                monthly["MonthStr"] = monthly["Month"].dt.strftime("%b %Y").str.upper()

            if monthly.empty or qty_col is None:
                st.info("No consumption records match the selected filters.")
            elif chart_type == "Bar":
                fig_c = go.Figure(go.Bar(
                    x=monthly["MonthStr"], y=monthly[qty_col],
                    marker_color="#1e3a7b",
                    text=monthly[qty_col].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition="inside", textfont=dict(color="gold", size=9)
                ))
                fig_c.update_layout(
                    margin=dict(l=10,r=10,t=10,b=30), height=280,
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(gridcolor="#e9ecef", title="Qty (MT)"),
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
                fig_c = go.Figure(go.Scatter(
                    x=monthly["MonthStr"], y=monthly[qty_col],
                    mode="lines+markers+text",
                    line=dict(color="#1e3a7b", width=2),
                    marker=dict(size=6, color="#1e3a7b"),
                    text=monthly[qty_col].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition="top center", textfont=dict(size=9)
                ))
                fig_c.update_layout(
                    margin=dict(l=10,r=10,t=10,b=30), height=280,
                    plot_bgcolor="white", paper_bgcolor="white",
                    yaxis=dict(gridcolor="#e9ecef", title="Qty (MT)"),
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

    # ── Shared Filters ──────────────────────────────────────────────────────
    fdf2, f2_country, f2_rm_desc, f2_rm_seg, f2_inco, f2_plan, f2_plant, f2_cat, f2_src, f2_rmcg = render_shared_filters(sku_df)

    # Weighted-avg DSI helper
    def weighted_dsi(df, group_col):
        ads_col = "Average Daily Sales (Future)"
        if df.empty or group_col not in df.columns:
            return pd.DataFrame(columns=[group_col, "8 Reasons (DSI)"])
        records = []
        for grp_val, g in df.groupby(group_col):
            denom = g[ads_col].sum()
            val = round((g["8 Reasons (DSI)"] * g[ads_col]).sum() / denom if denom != 0 else 0, 1)
            records.append({group_col: grp_val, "8 Reasons (DSI)": val})
        if not records:
            return pd.DataFrame(columns=[group_col, "8 Reasons (DSI)"])
        return pd.DataFrame(records)

    c1, c2 = st.columns(2)
    def make_bar(df, group_col, title):
        grp = weighted_dsi(df, group_col)
        fig = go.Figure()
        if not grp.empty:
            fig.add_trace(go.Bar(
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
        map_cols = st.columns(1)
        for pi, plant in enumerate(plants):
            plant_df      = fdf2[fdf2["PLANT"] == plant]
            src_countries = plant_df["Source Country"].dropna().unique().tolist()
            plant_lat, plant_lon = PLANT_COORDS.get(plant, (20.0, 78.0))
            plant_dsi = round((plant_df["8 Reasons (DSI)"] * plant_df["Average Daily Sales (Future)"]).sum()
                               / plant_df["Average Daily Sales (Future)"].sum()
                               if plant_df["Average Daily Sales (Future)"].sum() != 0 else 0, 1)

            # Compute per-source-country volume (sum of 8 Reasons Units) for line scaling
            sc_vol = plant_df.groupby("Source Country")["8 Reasons (Units)"].sum()
            max_vol = sc_vol.max() if len(sc_vol) > 0 else 1
            if max_vol == 0:
                max_vol = 1

            fig_map = go.Figure()
            for sc in src_countries:
                coords = COUNTRY_COORDS.get(sc)
                if coords:
                    vol = sc_vol.get(sc, 0)
                    # Scale line width 1–8 based on volume relative to max
                    line_width = max(1.0, round(1.0 + 7.0 * (vol / max_vol), 1))
                    # Scale marker size 5–16
                    marker_size = max(5, int(5 + 11 * (vol / max_vol)))
                    fig_map.add_trace(go.Scattergeo(
                        lon=[coords[1], plant_lon], lat=[coords[0], plant_lat],
                        mode="lines",
                        line=dict(width=line_width, color="red"),
                        showlegend=False,
                        hovertext=f"{sc}: {int(vol):,} units", hoverinfo="text"
                    ))
                    fig_map.add_trace(go.Scattergeo(
                        lon=[coords[1]], lat=[coords[0]], mode="markers",
                        marker=dict(size=marker_size, color="red", symbol="circle"),
                        showlegend=False,
                        hovertext=f"{sc}: {int(vol):,} units", hoverinfo="text"
                    ))
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
                margin=dict(l=0,r=0,t=40,b=0), height=720, paper_bgcolor="white"
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

    # ── Shared Filters ──────────────────────────────────────────────────────
    fdf3, _, _, _, _, _, _, _, _, _ = render_shared_filters(sku_df)

    R_COLS   = ["R1 Information Cycle (DSI)","R2 Manufacturing Lot Size (DSI)",
                "R3 Shipping Lot Size (DSI)","R4 Shipping Interval (DSI)",
                "R5 Geography (DSI)","R6 Shipping Variation (DSI)",
                "R7 Supply Variation (DSI)","R8 Demand Variation (DSI)"]
    R_LABELS = ["R1 Info Cycle","R2 Mfg Lot","R3 Ship Lot","R4 Ship Interval",
                "R5 Geography","R6 Ship Var","R7 Supply Var","R8 Demand Var"]
    R_COLORS = ["#1565C0","#1976D2","#1E88E5","#42A5F5",
                "#EF6C00","#F57C00","#FB8C00","#FFA726"]

    n3 = unique_sku_count(fdf3)
    ads = "Average Daily Sales (Future)"

    def w_avg(df, col):
        """Weighted average of col by Average Daily Sales, matching Dashboard 2 method."""
        denom = df[ads].sum()
        if denom == 0 or len(df) == 0:
            return 0.0
        return round((df[col] * df[ads]).sum() / denom, 2)

    # ── KPI row ────────────────────────────────────────────────────────────
    k_cols = st.columns(4)
    k_cols[0].metric("Total SKUs",          n3)
    k_cols[1].metric("Avg 8 Reasons (DSI)", f"{w_avg(fdf3, '8 Reasons (DSI)')} days")
    k_cols[2].metric("Avg Safety (DSI)",    f"{w_avg(fdf3, 'Safety (DSI)')} days")
    k_cols[3].metric("Avg Transit (DSI)",   f"{w_avg(fdf3, 'Transit (DSI)')} days")
    st.markdown("---")

    c1, c2 = st.columns(2)

    # ── R1–R8 average DSI horizontal bar ──────────────────────────────────
    with c1:
        st.markdown("**Average R1–R8 DSI Contribution**")
        avgs = [w_avg(fdf3, c) for c in R_COLS]
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
                v   = w_avg(sub, "8 Reasons (DSI)") if len(sub) else 0
                n_s = unique_sku_count(sub)
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

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD 4 — Single Material Deep Dive: Full 8 Reasons Breakdown
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔬 Dashboard 4":
    import plotly.graph_objects as go
    import numpy as np

    # ── Styles ────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    .d4-hero { font-family:'IBM Plex Sans',sans-serif; font-size:28px; font-weight:700;
               color:#0a192f; letter-spacing:-0.5px; margin-bottom:2px }
    .d4-sub  { font-family:'IBM Plex Sans',sans-serif; font-size:13px; color:#64748b;
               margin-bottom:16px }

    .reason-card {
        background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;
        padding:16px 18px; margin-bottom:10px; position:relative;
        border-left:4px solid var(--accent);
        font-family:'IBM Plex Sans',sans-serif;
        box-shadow: 0 1px 4px rgba(0,0,0,.05);
    }
    .reason-card:hover { box-shadow:0 4px 16px rgba(0,0,0,.10); transform:translateY(-1px);
                         transition:all .15s ease; }
    .reason-title  { font-size:13px; font-weight:700; color:#0f172a; text-transform:uppercase;
                     letter-spacing:.06em; margin-bottom:6px }
    .reason-dsi    { font-size:28px; font-weight:700; color:var(--accent);
                     font-family:'IBM Plex Mono',monospace; }
    .reason-unit   { font-size:12px; color:#94a3b8; margin-left:4px }
    .reason-formula{ font-size:11px; color:#475569; background:#f8fafc; border-radius:6px;
                     padding:5px 8px; margin-top:8px; font-family:'IBM Plex Mono',monospace;
                     border:1px solid #e2e8f0; }
    .reason-explain{ font-size:11.5px; color:#64748b; margin-top:5px; line-height:1.5 }
    .reason-inputs { font-size:11px; color:#0f172a; margin-top:6px; }
    .reason-inputs b { color:#1e40af }

    .kpi-strip { display:flex; gap:12px; margin-bottom:18px; flex-wrap:wrap }
    .kpi-box   { background:#0a192f; border-radius:10px; padding:14px 20px; flex:1;
                 min-width:130px; text-align:center; }
    .kpi-box .val { font-size:24px; font-weight:700; color:#38bdf8;
                    font-family:'IBM Plex Mono',monospace; }
    .kpi-box .lbl { font-size:11px; color:#94a3b8; margin-top:3px;
                    font-family:'IBM Plex Sans',sans-serif; text-transform:uppercase;
                    letter-spacing:.05em }

    .summary-box { background:#f0f9ff; border:1px solid #bae6fd; border-radius:10px;
                   padding:14px 18px; margin-bottom:14px; font-family:'IBM Plex Sans',sans-serif }
    .summary-box h4 { color:#0369a1; font-size:14px; font-weight:700; margin:0 0 6px 0 }
    .summary-box p  { color:#0c4a6e; font-size:12.5px; margin:0; line-height:1.6 }

    .stock-bar { height:28px; border-radius:6px; display:flex; overflow:hidden;
                 margin:10px 0 4px 0; border:1px solid #e2e8f0 }
    .bar-seg   { display:flex; align-items:center; justify-content:center;
                 font-size:10px; font-weight:600; color:white; white-space:nowrap;
                 overflow:hidden; font-family:'IBM Plex Mono',monospace }
    .legend-row{ display:flex; gap:12px; flex-wrap:wrap; margin-top:4px }
    .legend-dot{ width:10px; height:10px; border-radius:50%; display:inline-block;
                 margin-right:4px; vertical-align:middle }
    .legend-lbl{ font-size:11px; color:#475569; font-family:'IBM Plex Sans',sans-serif }

    .section-header { font-family:'IBM Plex Sans',sans-serif; font-size:16px; font-weight:700;
                      color:#0a192f; border-bottom:2px solid #e2e8f0; padding-bottom:6px;
                      margin:18px 0 12px 0 }
    .tag { display:inline-block; background:#dbeafe; color:#1e40af; border-radius:20px;
           padding:2px 10px; font-size:11px; font-weight:600; margin-right:6px;
           font-family:'IBM Plex Sans',sans-serif }
    .tag-green { background:#dcfce7; color:#166534 }
    .tag-orange{ background:#ffedd5; color:#9a3412 }
    .tag-red   { background:#fee2e2; color:#991b1b }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("final_output_b64"):
        st.warning("⚠️ Please complete the **Final Output** step first.")
        st.stop()

    fo_bytes = b64_to_bytes(st.session_state["final_output_b64"])
    sku_df   = pd.read_excel(BytesIO(fo_bytes), sheet_name="SKU Level")

    # ── Material selector ─────────────────────────────────────────────────────
    st.markdown("<div class='d4-hero'>🔬 Material Deep Dive</div>", unsafe_allow_html=True)
    st.markdown("<div class='d4-sub'>Select a material to see its full 8 Reasons inventory calculation, all input parameters, and detailed formula breakdowns.</div>", unsafe_allow_html=True)

    # Build selector labels and relevant supplier options
    sku_df["_material_label"] = sku_df["Material Code"].astype(str) + " — " + sku_df["Material Desc"].astype(str)
    sku_df["_supplier_label"] = sku_df["Supplier Name"].astype(str) + " (" + sku_df["Supplier Code"].astype(str) + ")"
    sku_df["_selector"] = (
        sku_df["_material_label"] + "  [" +
        sku_df["PLANT"].astype(str) + " / " +
        sku_df["_supplier_label"] + "]"
    )

    sel_col1, sel_col2, sel_col3 = st.columns(3)

    # Independent filters: each list is built from the full dataset, not from
    # the other selected filters. Selections are combined only after selection.
    material_options = ["All"] + sorted(sku_df["_material_label"].dropna().unique().tolist())
    plant_options    = ["All"] + sorted(sku_df["PLANT"].dropna().unique().tolist())
    supplier_options = ["All"] + sorted(sku_df["_supplier_label"].dropna().unique().tolist())

    current_material = st.session_state.get("d4_material_filter", "All")
    current_plant    = st.session_state.get("d4_plant_filter", "All")
    current_supplier = st.session_state.get("d4_supplier_filter", "All")
    if current_material not in material_options: current_material = "All"
    if current_plant not in plant_options:       current_plant = "All"
    if current_supplier not in supplier_options: current_supplier = "All"

    with sel_col1:
        chosen_material = st.selectbox("Material", material_options, index=material_options.index(current_material), key="d4_material_filter")
    with sel_col2:
        chosen_plant = st.selectbox("Plant", plant_options, index=plant_options.index(current_plant), key="d4_plant_filter")
    with sel_col3:
        chosen_supplier = st.selectbox("Supplier", supplier_options, index=supplier_options.index(current_supplier), key="d4_supplier_filter")

    filtered_sel = sku_df.copy()
    if chosen_material != "All": filtered_sel = filtered_sel[filtered_sel["_material_label"] == chosen_material]
    if chosen_plant    != "All": filtered_sel = filtered_sel[filtered_sel["PLANT"] == chosen_plant]
    if chosen_supplier != "All": filtered_sel = filtered_sel[filtered_sel["_supplier_label"] == chosen_supplier]

    if filtered_sel.empty:
        st.warning("No materials match the selected filters.")
        st.stop()

    if len(filtered_sel) == 1:
        row = filtered_sel.iloc[0]
    else:
        chosen = st.selectbox("Matching record", filtered_sel["_selector"].tolist(), key="d4_material")
        row = filtered_sel[filtered_sel["_selector"] == chosen].iloc[0]

    st.markdown("---")

    # ── Helper: safe numeric ──────────────────────────────────────────────────
    def n(v, dec=2):
        try: return round(float(v), dec)
        except: return 0.0

    # ── Extract all values ─────────────────────────────────────────────────────
    mat_code    = row.get("Material Code","")
    mat_desc    = row.get("Material Desc","")
    plant       = row.get("PLANT","")
    plant_code  = row.get("Plant Code","")
    supplier    = row.get("Supplier Name","")
    sup_code    = row.get("Supplier Code","")
    region      = row.get("Region","")
    inco        = row.get("INCO Term","")
    category    = row.get("Category","")
    src_country = row.get("Source Country","")
    rm_class    = row.get("RM Class Group","")
    seg         = row.get("RM Segmentation","")
    plan_cycle  = n(row.get("Planning cycle", 0), 0)
    data_qual   = row.get("Historical Data Quality","")
    new_sku     = row.get("New SKU","")

    # Input parameters
    min_order   = n(row.get("MINIMUM ORDER QTY (Units)", 0))
    sup_rel     = n(row.get("Supply Reliability (%)", 0))
    info_cycle  = n(row.get("Information Cycle (Days)", 0))
    svc_level   = n(row.get("Service Level (%)", 0))
    transit_d   = n(row.get("Transit Time (Days)", 0))
    add_time    = n(row.get("Additional Time (Days)", 0))
    tt_std_pct  = n(row.get("Transit Time Std. Dev. (%)", 0))
    ship_int    = n(row.get("Shipping Interval (Days)", 0))
    ship_int_sd = n(row.get("Shipping Interval Std. Dev. (%)", 0))
    ship_lot    = n(row.get("Shipping Lot Size (Units)", 0))
    sob         = n(row.get("SOB", 0))
    map_val     = n(row.get("MAP", 0))
    on_hand_u   = n(row.get("On-Hand (Units)", 0))

    # Calculated intermediates
    z           = n(row.get("Service Level Factor (z)", 0))
    review_p    = n(row.get("Review Period (days)", 0))
    lead_t      = n(row.get("Lead Time (days)", 0))
    risk_h      = n(row.get("Risk-Horizon (days)", 0))
    ads         = n(row.get("Average Daily Sales", 0))
    ads_fut     = n(row.get("Average Daily Sales (Future)", 0))
    weekly_rmse = n(row.get("Weekly RMSE", 0))

    # R1-R8
    r1 = n(row.get("R1 Information Cycle (DSI)", 0))
    r2 = n(row.get("R2 Manufacturing Lot Size (DSI)", 0))
    r3 = n(row.get("R3 Shipping Lot Size (DSI)", 0))
    r4 = n(row.get("R4 Shipping Interval (DSI)", 0))
    r5 = n(row.get("R5 Geography (DSI)", 0))
    r6 = n(row.get("R6 Shipping Variation (DSI)", 0))
    r7 = n(row.get("R7 Supply Variation (DSI)", 0))
    r8 = n(row.get("R8 Demand Variation (DSI)", 0))

    # Outputs
    cycle_dsi   = n(row.get("Cycle (DSI)", 0))
    transit_dsi = n(row.get("Transit (DSI)", 0))
    safety_dsi  = n(row.get("Safety (DSI)", 0))
    total_dsi   = n(row.get("8 Reasons (DSI)", 0))
    min_dsi     = n(row.get("Min (DSI)", 0))
    onhand_dsi  = n(row.get("On-Hand (DSI)", 0))
    max_dsi     = n(row.get("Max (DSI)", 0))

    cycle_u     = n(row.get("Cycle (Units)", 0))
    transit_u   = n(row.get("Transit (Units)", 0))
    safety_u    = n(row.get("Safety (Units)", 0))
    total_u     = n(row.get("8 Reasons (Units)", 0))
    min_u       = n(row.get("Min (Units)", 0))
    max_u       = n(row.get("Max (Units)", 0))

    under_min   = n(row.get("Under Min (Val)", 0))
    over_max    = n(row.get("Over Max (Val)", 0))
    saf_cap     = n(row.get("Safety Stock Cap", 0), 0)
    max_dem_pct = n(row.get("Maximum Demand in % of Forecast", 0), 0)

    # ── Header identity strip ─────────────────────────────────────────────────
    h1, h2 = st.columns([2, 1])
    with h1:
        tag_seg   = f"<span class='tag'>{seg}</span>"
        tag_cat   = f"<span class='tag tag-green'>{category}</span>"
        tag_inco  = f"<span class='tag tag-orange'>{inco}</span>"
        tag_new   = f"<span class='tag tag-red'>NEW SKU</span>" if new_sku == "Yes" else ""
        st.markdown(f"""
        <div style='font-family:IBM Plex Sans,sans-serif'>
          <div style='font-size:22px;font-weight:700;color:#0a192f'>{mat_desc}</div>
          <div style='font-size:13px;color:#64748b;margin:2px 0 6px 0'>
            Code: <b>{mat_code}</b> &nbsp;|&nbsp; Plant: <b>{plant}</b> ({plant_code})
            &nbsp;|&nbsp; Supplier: <b>{supplier}</b> ({sup_code})
          </div>
          <div style='font-size:12px;color:#64748b;margin-bottom:8px'>
            Region: <b>{region}</b> &nbsp;|&nbsp; Source: <b>{src_country}</b>
            &nbsp;|&nbsp; Class: <b>{rm_class}</b> &nbsp;|&nbsp; Cycle: <b>{int(plan_cycle)} days</b>
            &nbsp;|&nbsp; Data Quality: <b>{data_qual}</b>
          </div>
          {tag_seg}{tag_cat}{tag_inco}{tag_new}
        </div>""", unsafe_allow_html=True)
    with h2:
        status_tag = "tag-red" if under_min > 0 else ("tag-orange" if over_max > 0 else "tag-green")
        status_lbl = "⚠️ Under Min" if under_min > 0 else ("📦 Over Max" if over_max > 0 else "✅ In Range")
        st.markdown(f"""
        <div style='background:#0a192f;border-radius:10px;padding:14px 18px;
                    font-family:IBM Plex Sans,sans-serif;text-align:center'>
          <div style='font-size:32px;font-weight:700;color:#38bdf8;
                      font-family:IBM Plex Mono,monospace'>{total_dsi}</div>
          <div style='font-size:11px;color:#94a3b8;text-transform:uppercase;
                      letter-spacing:.06em'>8 Reasons (DSI)</div>
          <div style='margin-top:8px'><span class='tag {status_tag}'>{status_lbl}</span></div>
          <div style='font-size:11px;color:#64748b;margin-top:6px'>
            Under Min: <b style='color:#f87171'>${under_min:.3f}M</b> &nbsp;
            Over Max: <b style='color:#34d399'>${abs(over_max):.3f}M</b>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── KPI strip ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class='kpi-strip'>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>Cycle DSI</div></div>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>Transit DSI</div></div>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>Safety DSI</div></div>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>Min DSI</div></div>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>On-Hand DSI</div></div>
      <div class='kpi-box'><div class='val'>{}</div><div class='lbl'>Max DSI</div></div>
    </div>""".format(cycle_dsi, transit_dsi, safety_dsi, min_dsi, onhand_dsi, max_dsi),
    unsafe_allow_html=True)

    # ── Visual stock position bar ─────────────────────────────────────────────
    bar_total = max_dsi if max_dsi > 0 else 1
    p_safety  = round(safety_dsi  / bar_total * 100, 1)
    p_transit = round(transit_dsi / bar_total * 100, 1)
    p_cycle   = round(cycle_dsi   / bar_total * 100, 1)
    p_rem     = max(0, 100 - p_safety - p_transit - p_cycle)

    st.markdown("<div class='section-header'>📊 Stock Position Overview</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='stock-bar'>
      <div class='bar-seg' style='width:{p_safety}%;background:#ef4444'>Safety {safety_dsi}</div>
      <div class='bar-seg' style='width:{p_transit}%;background:#f97316'>Transit {transit_dsi}</div>
      <div class='bar-seg' style='width:{p_cycle}%;background:#3b82f6'>Cycle {cycle_dsi}</div>
      <div class='bar-seg' style='width:{p_rem}%;background:#e2e8f0;color:#94a3b8'>Buffer</div>
    </div>
    <div class='legend-row'>
      <div><span class='legend-dot' style='background:#ef4444'></span><span class='legend-lbl'>Safety ({safety_dsi} DSI / {safety_u:,.0f} units)</span></div>
      <div><span class='legend-dot' style='background:#f97316'></span><span class='legend-lbl'>Transit ({transit_dsi} DSI / {transit_u:,.0f} units)</span></div>
      <div><span class='legend-dot' style='background:#3b82f6'></span><span class='legend-lbl'>Cycle ({cycle_dsi} DSI / {cycle_u:,.0f} units)</span></div>
      <div><span class='legend-dot' style='background:#e2e8f0'></span><span class='legend-lbl'>Max ceiling ({max_dsi} DSI / {max_u:,.0f} units)</span></div>
    </div>
    <div style='font-size:12px;color:#64748b;margin-top:8px;font-family:IBM Plex Sans,sans-serif'>
      On-Hand: <b>{on_hand_u:,.0f} units</b> ({onhand_dsi} DSI) &nbsp;|&nbsp;
      Total 8 Reasons: <b>{total_u:,.0f} units</b> &nbsp;|&nbsp;
      MAP: <b>${map_val:.3f}</b>
    </div>
    """, unsafe_allow_html=True)

    # ── Waterfall chart ───────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📉 R1–R8 Waterfall Breakdown</div>", unsafe_allow_html=True)

    wf_labels  = ["R1 Info Cycle","R2 Mfg Lot","R3 Ship Lot","R4 Ship Interval",
                  "= Cycle","R5 Geography","= Transit","R6 Ship Var","R7 Supply Var",
                  "R8 Demand Var","= Safety","TOTAL"]
    wf_vals    = [r1, r2, r3, r4, cycle_dsi, r5, transit_dsi, r6, r7, r8, safety_dsi, total_dsi]
    wf_measure = ["relative","relative","relative","relative","total",
                  "relative","total","relative","relative","relative","total","total"]
    wf_colors  = ["#3b82f6","#3b82f6","#3b82f6","#3b82f6","#1d4ed8",
                  "#f97316","#ea580c","#ef4444","#ef4444","#ef4444","#dc2626","#0a192f"]

    fig_wf = go.Figure(go.Waterfall(
        name="DSI", orientation="v",
        measure=wf_measure, x=wf_labels, y=wf_vals,
        text=[f"{v:.2f}" for v in wf_vals],
        textposition="outside",
        connector=dict(line=dict(color="#e2e8f0", width=1, dash="dot")),
        increasing=dict(marker=dict(color="#3b82f6")),
        decreasing=dict(marker=dict(color="#f59e0b")),
        totals=dict(marker=dict(color="#0a192f")),
    ))
    fig_wf.update_layout(
        height=380, margin=dict(l=10,r=10,t=20,b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(gridcolor="#f1f5f9", title="DSI (Days of Supply Inventory)"),
        xaxis=dict(tickfont=dict(size=10, family="IBM Plex Mono")),
        font=dict(family="IBM Plex Sans"),
        showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # ── R1–R8 detailed cards ──────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📋 Detailed R1–R8 Calculations</div>", unsafe_allow_html=True)

    REASONS = [
        {
            "num": "R1", "color": "#3b82f6",
            "title": "Information Cycle (DSI)",
            "dsi": r1,
            "explain": "Half the review period — the average time between two consecutive order placements. "
                       "Represents the cycle stock needed to cover demand while waiting for the next order.",
            "formula": "R1 = Review Period × 0.5",
            "inputs": {
                "Information Cycle (Days)": info_cycle,
                "Shipping Interval (Days)": ship_int,
                "Review Period = max(Info Cycle, Ship Interval)": review_p,
            },
            "calc": f"R1 = {review_p} × 0.5 = {r1} DSI",
        },
        {
            "num": "R2", "color": "#60a5fa",
            "title": "Manufacturing Lot Size (DSI)",
            "dsi": r2,
            "explain": "Buffer needed because the supplier ships in fixed minimum order quantities (MOQ). "
                       "Half the MOQ is held as average cycle stock.",
            "formula": "R2 = (Min Order Qty / Avg Daily Sales) × 0.5",
            "inputs": {
                "Minimum Order QTY (Units)": min_order,
                "Average Daily Sales (History)": ads,
            },
            "calc": f"R2 = ({min_order:,.0f} / {abs(ads):.1f}) × 0.5 = {r2} DSI",
        },
        {
            "num": "R3", "color": "#93c5fd",
            "title": "Shipping Lot Size (DSI)",
            "dsi": r3,
            "explain": "Buffer due to minimum shipping quantities. If the shipper requires a minimum load, "
                       "excess inventory accumulates on average as half the lot size.",
            "formula": "R3 = (Shipping Lot Size / Avg Daily Sales) × 0.5",
            "inputs": {
                "Shipping Lot Size (Units)": ship_lot,
                "Average Daily Sales (History)": ads,
            },
            "calc": f"R3 = ({ship_lot:,.0f} / {abs(ads):.1f}) × 0.5 = {r3} DSI",
        },
        {
            "num": "R4", "color": "#2563eb",
            "title": "Shipping Interval (DSI)",
            "dsi": r4,
            "explain": "Buffer for infrequent shipments — if a ship only sails once a week, "
                       "you need half that interval in stock on average between arrivals.",
            "formula": "R4 = Shipping Interval (Days) × 0.5",
            "inputs": {
                "Shipping Interval (Days)": ship_int,
                "Shipping Interval Std Dev (%)": ship_int_sd,
            },
            "calc": f"R4 = {ship_int} × 0.5 = {r4} DSI",
        },
        {
            "num": "R5", "color": "#f97316",
            "title": "Geography / Lead Time (DSI)",
            "dsi": r5,
            "explain": "Inventory in-transit. The material is physically on the road/sea — "
                       "those days of supply must be maintained as pipeline inventory.",
            "formula": "R5 = Lead Time (days)  [= Transit Time + Additional Time for CIF/EXW, else Additional Time only]",
            "inputs": {
                "Transit Time (Days)": transit_d,
                "Additional Time (Days)": add_time,
                "INCO Term": inco,
            },
            "calc": f"R5 = {lead_t} DSI  (Transit {transit_d} + Add. {add_time}, INCO={inco})",
        },
        {
            "num": "R6", "color": "#ef4444",
            "title": "Shipping Variation (DSI)",
            "dsi": r6,
            "explain": "Safety stock for variability in transit time. If ships arrive erratically, "
                       "extra buffer is needed proportional to the standard deviation of transit days.",
            "formula": "R6 = (Transit Time Std Dev % / 100) × Lead Time × z",
            "inputs": {
                "Transit Time Std Dev (%)": tt_std_pct,
                "Lead Time (days)": lead_t,
                "Service Level Factor (z)": z,
            },
            "calc": f"R6 = ({tt_std_pct}/100) × {lead_t} × {z} = {r6} DSI",
        },
        {
            "num": "R7", "color": "#dc2626",
            "title": "Supply Variation (DSI)",
            "dsi": r7,
            "explain": "Safety stock for supplier unreliability. If the supplier only delivers on-time "
                       "90% of the time, you need extra stock to cover the 10% late deliveries.",
            "formula": "R7 = (1 − Supply Reliability) × z × √Risk-Horizon",
            "inputs": {
                "Supply Reliability (%)": sup_rel,
                "Service Level Factor (z)": z,
                "Risk-Horizon (days)": risk_h,
                "Review Period (days)": review_p,
                "Lead Time (days)": lead_t,
            },
            "calc": f"R7 = (1 − {sup_rel/100:.2f}) × {z} × √{risk_h:.2f} = {r7} DSI",
        },
        {
            "num": "R8", "color": "#b91c1c",
            "title": "Demand Variation (DSI)",
            "dsi": r8,
            "explain": "Safety stock for forecast uncertainty. Based on the weekly RMSE (Root Mean Squared Error) "
                       "of the forecast, scaled over the risk horizon and adjusted for the service level target.",
            "formula": "R8 = (Weekly RMSE × √(Risk-Horizon / 7) × z) / Avg Daily Sales (Future)",
            "inputs": {
                "Weekly RMSE": weekly_rmse,
                "Risk-Horizon (days)": risk_h,
                "Service Level Factor (z)": z,
                "Average Daily Sales (Future)": ads_fut,
                "Service Level (%)": svc_level,
            },
            "calc": f"R8 = ({weekly_rmse:,.0f} × √({risk_h:.2f}/7) × {z}) / {ads_fut:.1f} = {r8} DSI",
        },
    ]

    # Render 2 columns of cards
    col_a, col_b = st.columns(2)
    for i, r in enumerate(REASONS):
        col = col_a if i % 2 == 0 else col_b
        inputs_html = "".join(
            f"<div>• {k}: <b>{v:,.3f}</b></div>" if isinstance(v, float)
            else f"<div>• {k}: <b>{v}</b></div>"
            for k, v in r["inputs"].items()
        )
        with col:
            st.markdown(f"""
            <div class='reason-card' style='--accent:{r["color"]}'>
              <div class='reason-title'>{r["num"]} — {r["title"]}</div>
              <div>
                <span class='reason-dsi'>{r["dsi"]}</span>
                <span class='reason-unit'>DSI</span>
                &nbsp;
                <span class='reason-unit'>= {round(r["dsi"] * ads_fut, 0):,.0f} units</span>
              </div>
              <div class='reason-explain'>{r["explain"]}</div>
              <div class='reason-formula'>{r["formula"]}</div>
              <div class='reason-inputs'>{inputs_html}</div>
              <div class='reason-formula' style='margin-top:8px;background:#eff6ff;
                   border-color:#bfdbfe;color:#1e40af'><b>→ {r["calc"]}</b></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Aggregation section ───────────────────────────────────────────────────
    st.markdown("<div class='section-header'>🧮 Aggregation: Cycle / Transit / Safety → 8 Reasons</div>",
                unsafe_allow_html=True)

    global_cfg = {}
    try:
        from src.helper import GLOBAL_CONFIG
        global_cfg = GLOBAL_CONFIG.get("global_parameters", [{}])[0]
    except Exception:
        pass
    cycle_method = global_cfg.get("cycle_stock", {}).get("calculation_methodology", "Max")

    st.markdown(f"""
    <div class='summary-box'>
      <h4>Cycle Stock = {cycle_method}(R1, R2, R3, R4)</h4>
      <p>
        {cycle_method}({r1}, {r2}, {r3}, {r4}) = <b>{cycle_dsi} DSI</b>
        &nbsp;→&nbsp; {cycle_u:,.0f} units
        &nbsp;&nbsp;<i>(Applied cap: Shipping Interval ≤ {global_cfg.get("cappings",{}).get("shipping_interval_cap","—")} DSI)</i>
      </p>
    </div>
    <div class='summary-box'>
      <h4>Transit Stock = R5 (Geography)</h4>
      <p>
        = {r5} DSI &nbsp;→&nbsp; {transit_u:,.0f} units
        &nbsp;&nbsp;<i>(Cap: Transit ≤ {global_cfg.get("cappings",{}).get("transit_time_cap","—")} DSI)</i>
      </p>
    </div>
    <div class='summary-box'>
      <h4>Safety Stock = √(R6² + R7² + R8²)</h4>
      <p>
        = √({r6}² + {r7}² + {r8}²)
        = √({round(r6**2,4)} + {round(r7**2,4)} + {round(r8**2,4)})
        = √{round(r6**2+r7**2+r8**2,4)}
        = <b>{safety_dsi} DSI</b> &nbsp;→&nbsp; {safety_u:,.0f} units
        &nbsp;&nbsp;<i>(Cap: Safety ≤ {saf_cap} DSI)</i>
      </p>
    </div>
    <div class='summary-box' style='background:#f0fdf4;border-color:#86efac'>
      <h4>8 Reasons (DSI) = Cycle + Transit + Safety</h4>
      <p>= {cycle_dsi} + {transit_dsi} + {safety_dsi} = <b>{total_dsi} DSI</b>
         &nbsp;→&nbsp; <b>{total_u:,.0f} units</b>
         &nbsp;|&nbsp; MAP ${map_val:.3f} &nbsp;|&nbsp;
         Value ≈ <b>${round(total_u * map_val / 1e6, 3)}M</b>
      </p>
    </div>
    <div class='summary-box' style='background:#fefce8;border-color:#fde68a'>
      <h4>Min / On-Hand / Max Stock Positions</h4>
      <p>
        <b>Min</b> = Safety = {min_dsi} DSI ({min_u:,.0f} units) &nbsp;|&nbsp;
        <b>On-Hand</b> = Safety + Cycle = {onhand_dsi} DSI ({on_hand_u:,.0f} units) &nbsp;|&nbsp;
        <b>Max</b> = Safety + 2×Cycle = {max_dsi} DSI ({max_u:,.0f} units)
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Input parameters table ────────────────────────────────────────────────
    st.markdown("<div class='section-header'>⚙️ All Input Parameters</div>", unsafe_allow_html=True)
    param_data = {
        "Parameter": [
            "Service Level (%)", "Service Level Factor z",
            "Information Cycle (Days)", "Review Period (days)",
            "Transit Time (Days)", "Additional Time (Days)", "Lead Time (days)", "Risk-Horizon (days)",
            "Shipping Interval (Days)", "Shipping Interval Std Dev (%)",
            "Transit Time Std Dev (%)",
            "Minimum Order QTY (Units)", "Shipping Lot Size (Units)",
            "Supply Reliability (%)",
            "Average Daily Sales — History", "Average Daily Sales — Future",
            "Weekly RMSE (Demand Variation)",
            "MAP ($/unit)", "Share of Business (SOB)",
            "Max Demand Cap (%)", "Safety Stock Cap (DSI)",
        ],
        "Value": [
            svc_level, z,
            info_cycle, review_p,
            transit_d, add_time, lead_t, risk_h,
            ship_int, ship_int_sd,
            tt_std_pct,
            min_order, ship_lot,
            sup_rel,
            ads, ads_fut,
            weekly_rmse,
            map_val, sob,
            max_dem_pct, saf_cap,
        ],
        "Description": [
            "Target customer service level for this material",
            "Normal distribution z-score for the service level",
            "Days between order reviews (from Supply Parameters)",
            "max(Information Cycle, Shipping Interval)",
            "Days from supplier to plant (transit only)",
            "Handling / customs additional days",
            "Total replenishment lead time",
            "Review Period + Lead Time — window for demand risk",
            "Average days between shipments",
            "Coefficient of variation of shipment timing",
            "Coefficient of variation of transit duration",
            "Supplier minimum order quantity in units",
            "Minimum batch shipped per delivery",
            "% of orders delivered on-time by supplier",
            "Historical avg daily consumption (for R2/R3)",
            "Future forecast-based avg daily sales (for R8 & units)",
            "Root Mean Square Error of weekly forecast",
            "Material Average Price per unit ($)",
            "Share of business allocated to this supplier",
            "Cap on demand used in forecast (vs actual)",
            "Maximum allowed Safety Stock in DSI",
        ]
    }
    st.dataframe(
        pd.DataFrame(param_data).style.format({"Value": lambda v: f"{v:,.3f}" if isinstance(v, float) else v}),
        use_container_width=True, height=680
    )

