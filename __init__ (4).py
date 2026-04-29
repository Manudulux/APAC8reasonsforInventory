import pandas as pd
import base64
from io import BytesIO
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows


def generate_output_dataframes(final_df: pd.DataFrame) -> dict:
    try:
        grouped_dataframes = {}
        grouped_dataframes["SKU Level"] = final_df.copy()
        grouping_columns = ["Region", "Source Region", "Planning cycle", "INCO Term", "Plant Code", "RM Segmentation"]
        dsi_columns = ["Cycle (DSI)", "Transit (DSI)", "Safety (DSI)", "8 Reasons (DSI)"]
        units_columns = ["Cycle (Units)", "Transit (Units)", "Safety (Units)", "8 Reasons (Units)"]
        rm_segmentation_categories = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]

        for col in dsi_columns:
            daily_col_name = f"{col.lower().replace(' ', '_')}_avg_daily"
            final_df[daily_col_name] = final_df[col] * final_df["Average Daily Sales (Future)"]

        for group_col in grouping_columns:
            group_level_df = final_df.groupby(group_col).apply(
                lambda df: pd.Series({
                    col: (
                        round(df[f"{col.lower().replace(' ', '_')}_avg_daily"].sum() / denom, 3)
                        if (denom := df["Average Daily Sales (Future)"].sum()) != 0 else 0
                    )
                    for col in dsi_columns
                })
            ).reset_index()
            for col in units_columns:
                group_level_df[col] = final_df.groupby(group_col).apply(
                    lambda df: df[col].sum()
                ).reset_index(drop=True)
            total_sales = final_df["Average Daily Sales (Future)"].sum()
            result = {
                col: round(
                    final_df[f"{col.lower().replace(' ', '_')}_avg_daily"].sum() / total_sales if total_sales != 0 else 0, 3
                )
                for col in dsi_columns
            }
            for col in units_columns:
                result[col] = final_df[col].sum()
            total_row = pd.DataFrame([result])
            total_row[group_col] = "Total"
            group_level_df = pd.concat([group_level_df, total_row], ignore_index=True)
            grouped_dataframes[group_col] = group_level_df

        grouped_dataframes["RM Segmentation"] = pd.concat(
            [grouped_dataframes["RM Segmentation"]] +
            [pd.Series([seg] + [0] * (len(grouped_dataframes["RM Segmentation"].columns) - 1),
                       index=grouped_dataframes["RM Segmentation"].columns).to_frame().T
             for seg in rm_segmentation_categories
             if seg not in grouped_dataframes["RM Segmentation"]['RM Segmentation'].unique()],
            ignore_index=True
        ).sort_values(by='RM Segmentation', ascending=True)

        return grouped_dataframes
    except Exception as e:
        return str(e)


def generate_encoded_output(grouped_df: dict) -> str:
    """Write all grouped dataframes into a multi-sheet Excel workbook and return as base64."""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in grouped_df.items():
                safe_name = sheet_name[:31]  # Excel max sheet name length
                df.to_excel(writer, sheet_name=safe_name, index=False)
        output.seek(0)
        return base64.b64encode(output.read()).decode('utf-8')
    except Exception as e:
        return str(e)
