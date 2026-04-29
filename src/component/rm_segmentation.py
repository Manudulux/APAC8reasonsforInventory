from src.component.generate_rm_input import generate_rm_input_file
import numpy as np
import re
import pandas as pd
from src.component import GLOBAL_CONFIG


class RmSegmentation:
    def __init__(self, dataframes) -> None:
        self.dataframes = dataframes
        self.actual_inventory = dataframes["Actual_Inventory"]
        self.future_df = dataframes["BOM_Forecast_Data_Future"]
        self.product_master = dataframes["Product_Master"]
        self.load_config()

    def load_config(self):
        self.service_mapping = GLOBAL_CONFIG['global_parameters'][0].get('service_level_mapping')
        self.value = GLOBAL_CONFIG['global_parameters'][0]['price_conversion']['USD_value'] * (10 ** 6)
        self.rm_segmentation = GLOBAL_CONFIG['global_parameters'][0]['rm_segmentation']

    def create_rm_df(self):
        rm_dataframe = generate_rm_input_file(self.dataframes)
        future_forecast = rm_dataframe.get("rm_input_file")
        future_forecast = future_forecast.drop_duplicates()
        future_forecast.fillna(0, inplace=True)
        return future_forecast

    def total_rmsales(self):
        future_forecast = self.create_rm_df()
        future_forecast.columns = future_forecast.columns.astype("str")
        pattern = r'^\d{2}\.?\d{4}$'
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, col)]
        future_forecast['Total_RM_Sales'] = future_forecast[sales_columns].sum(axis=1).round(5)

        # Work on a copy of actual_inventory to avoid mutating the original
        act_inv = self.actual_inventory.copy()
        act_inv["RM_Plant"] = (
            act_inv['CODE'].astype('int').astype('str') + "_" +
            act_inv['Plant Code'].astype('str')
        )
        code_map = dict(zip(act_inv['RM_Plant'], act_inv['MAP']))
        qty_map  = dict(zip(act_inv['RM_Plant'], act_inv['QTY']))

        future_forecast['RM_Plant'] = (
            future_forecast['RM Code'].astype('int').astype('str') + "_" +
            future_forecast['Plant Code'].astype('str')
        )
        future_forecast['MAP'] = future_forecast['RM_Plant'].map(code_map)
        future_forecast['QTY'] = future_forecast['RM_Plant'].map(qty_map)
        return future_forecast

    def year_req_val(self):
        future_forecast = self.total_rmsales()
        future_forecast["Year Req Val"] = round(
            (future_forecast["Total_RM_Sales"] * future_forecast["MAP"].fillna(0)) / self.value, 4
        )
        # FIX: pandas groupby.apply drops the grouping column in newer versions.
        # Sort within each Plant Code group without losing the column.
        future_forecast = (
            future_forecast
            .sort_values(['Plant Code', 'Year Req Val'], ascending=[True, False])
            .reset_index(drop=True)
        )
        return future_forecast

    def cummulative_contribution(self):
        future_forecast = self.year_req_val()
        # Restore Plant Code from RM_Plant if it was dropped by any groupby operation
        if 'Plant Code' not in future_forecast.columns and 'RM_Plant' in future_forecast.columns:
            future_forecast['Plant Code'] = future_forecast['RM_Plant'].str.split('_').str[1]

        total_y23_per_plant = future_forecast.groupby('Plant Code')['Year Req Val'].sum()

        # Avoid groupby.apply (drops grouping column in pandas >= 2.2).
        # Instead compute cumsum per plant using a merge.
        future_forecast = future_forecast.sort_values(
            ['Plant Code', 'Year Req Val'], ascending=[True, False]
        ).reset_index(drop=True)

        future_forecast['_cumsum'] = future_forecast.groupby('Plant Code')['Year Req Val'].cumsum()
        future_forecast['_total']  = future_forecast['Plant Code'].map(total_y23_per_plant)
        future_forecast['Contribution'] = (
            future_forecast['_cumsum'] / future_forecast['_total'].replace(0, pd.NA) * 100
        ).fillna(0).round(2)
        future_forecast.drop(columns=['_cumsum', '_total'], inplace=True)
        return future_forecast

    def determine_rm_segment(self, contribution):
        """Return segment letter; clamps to last defined segment if value exceeds all ranges."""
        segments = self.rm_segmentation.get('segment', {})
        last_seg = None
        for segment, range_values in segments.items():
            lower_bound, upper_bound = range_values
            last_seg = segment
            if lower_bound <= contribution <= upper_bound:
                return segment
        return last_seg  # fallback — e.g. 'C' for contribution > 100

    def rm_seg_volume(self):
        future_forecast = self.cummulative_contribution()
        future_forecast["RM Segment (Vol)"] = future_forecast["Contribution"].apply(self.determine_rm_segment)
        return future_forecast

    def oe_sku_mapping(self):
        future_forecast = self.rm_seg_volume()
        if "OE_SKU (Y/N)" in self.product_master.columns:
            future_forecast = future_forecast.merge(
                self.product_master[["SKU", "OE_SKU (Y/N)"]],
                left_on="RM Code", right_on='SKU', how='left'
            )
            if 'SKU' in future_forecast.columns:
                future_forecast.drop(columns=['SKU'], inplace=True)
        else:
            future_forecast["OE_SKU (Y/N)"] = "N"
        future_forecast.fillna({"OE_SKU (Y/N)": "N"}, inplace=True)
        return future_forecast

    def rm_segment_final(self):
        future_forecast = self.oe_sku_mapping()
        future_forecast['RM Segment Final'] = np.where(
            future_forecast['OE_SKU (Y/N)'] == 'N',
            future_forecast['RM Segment (Vol)'],
            'A'
        )
        return future_forecast

    def calculate_cv(self, row, sales_columns):
        monthly_values = row[sales_columns].values.astype(float)
        mean_sales = np.mean(monthly_values)
        std_dev_sales = np.std(monthly_values)
        if mean_sales == 0:
            return 0
        return std_dev_sales / mean_sales

    def handle_outliers_using_median(self, row, sales_columns):
        monthly_values = row[sales_columns].values.astype(float)
        non_zero_values = monthly_values[monthly_values != 0]
        if len(non_zero_values) == 0:
            return row
        Q1 = np.percentile(non_zero_values, 5)
        Q3 = np.percentile(non_zero_values, 95)
        outlier_indices = (monthly_values < Q1) | (monthly_values > Q3)
        if np.any(outlier_indices):
            median_value = np.mean(non_zero_values)
            monthly_values[outlier_indices] = median_value
        row[sales_columns] = monthly_values
        return row

    def handle_outliers(self):
        future_forecast = self.rm_segment_final()
        pattern = r'^\d{2}\.?\d{4}$'
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, str(col))]
        for index, row in future_forecast.iterrows():
            cv = self.calculate_cv(row, sales_columns)
            if cv > 1.0:
                future_forecast.loc[index] = self.handle_outliers_using_median(row, sales_columns)
        return future_forecast

    def variability(self):
        future_forecast = self.handle_outliers()
        pattern = r'^\d{2}\.?\d{4}$'
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, str(col))]
        future_forecast['Mean_RM_Sales'] = future_forecast[sales_columns].mean(axis=1).round(5)
        future_forecast['Std_dev_RM_Sales'] = future_forecast[sales_columns].std(axis=1).round(5)
        # Guard against divide-by-zero when mean is 0
        future_forecast['CV_RM_Sales'] = np.where(
            future_forecast['Mean_RM_Sales'] == 0,
            0,
            (future_forecast['Std_dev_RM_Sales'] / future_forecast['Mean_RM_Sales']).round(5)
        )
        future_forecast["Variability"] = (future_forecast["CV_RM_Sales"] * 100).round(2)
        return future_forecast

    def determine_rm_level(self, var):
        """Return variance level; clamps to last defined level if value exceeds all ranges."""
        variations = self.rm_segmentation.get('variance', {})
        last_level = None
        for variation, range_values in variations.items():
            lower_bound, upper_bound = range_values
            last_level = variation
            if lower_bound <= var <= upper_bound:
                return variation
        return last_level  # fallback — e.g. '3' for CV > 100%

    def rm_segment_level(self):
        future_forecast = self.variability()
        future_forecast["RM_Segment_Level"] = future_forecast["Variability"].apply(self.determine_rm_level)
        return future_forecast

    def segmentation(self):
        future_forecast = self.rm_segment_level()
        # Guard: fill any None values before string concatenation
        future_forecast["RM Segment Final"]  = future_forecast["RM Segment Final"].fillna("C").astype(str)
        future_forecast["RM_Segment_Level"]  = future_forecast["RM_Segment_Level"].fillna("3").astype(str)
        future_forecast["Segmentation"] = future_forecast["RM Segment Final"] + future_forecast["RM_Segment_Level"]
        return future_forecast

    def service_level(self):
        future_forecast = self.segmentation()
        future_forecast["Service_Level(%)"] = future_forecast["Segmentation"].map(self.service_mapping)
        future_forecast = future_forecast.drop_duplicates()
        # Ensure RM_Plant column exists (consumed by supply_formulas.service_level_percentage)
        if 'RM_Plant' not in future_forecast.columns:
            future_forecast['RM_Plant'] = (
                future_forecast['RM Code'].astype('int').astype('str') + "_" +
                future_forecast['Plant Code'].astype('str')
            )
        self.dataframes["rm_segmentation_output"] = future_forecast
        return self.dataframes

    def calculate(self):
        return self.service_level()
