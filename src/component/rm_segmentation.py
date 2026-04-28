from src.component.generate_rm_input import generate_rm_input_file
import numpy as np
import re
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
        self.value = GLOBAL_CONFIG['global_parameters'][0]['price_conversion']['USD_value'] * (10**6)
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
        pattern = r'^\d{2}.?\d{4}$'
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, col)]
        future_forecast['Total_RM_Sales'] = future_forecast[sales_columns].sum(axis=1).round(5)
        self.actual_inventory["RM_Plant"] = self.actual_inventory['CODE'].astype('int').astype('str') + "_" + self.actual_inventory['Plant Code'].astype('str')
        code_map = dict(zip(self.actual_inventory['RM_Plant'], self.actual_inventory['MAP']))
        qty_map = dict(zip(self.actual_inventory['RM_Plant'], self.actual_inventory['QTY']))
        future_forecast['RM_Plant'] = future_forecast['RM Code'].astype('int').astype('str') + "_" + future_forecast['Plant Code'].astype('str')
        future_forecast['MAP'] = future_forecast['RM_Plant'].map(code_map)
        future_forecast['QTY'] = future_forecast['RM_Plant'].map(qty_map)
        self.actual_inventory.drop(columns='RM_Plant', inplace=True)
        return future_forecast
       
    def year_req_val(self):
        # Get the future forecast from the total sales
        future_forecast = self.total_rmsales()

        # For each Plant Code, calculate "Year Req Val"
        future_forecast["Year Req Val"] = round(((future_forecast["Total_RM_Sales"] * future_forecast["MAP"]) / self.value), 4)
        
        # Group by 'Plant Code' and sort by 'Year Req Val' within each group
        future_forecast = future_forecast.groupby('Plant Code').apply(
            lambda group: group.sort_values(by='Year Req Val', ascending=False)
        ).reset_index(drop=True)

        return future_forecast

    def cummulative_contribution(self):
        future_forecast = self.year_req_val()

        # Calculate the total 'Year Req Val' per 'Plant Code'
        total_y23_per_plant = future_forecast.groupby('Plant Code')['Year Req Val'].sum()

        # Calculate the cumulative contribution for each Plant Code separately
        def calculate_contribution(group):
            total_y23 = total_y23_per_plant[group.name]  # Get the total for this particular Plant Code
            group["Contribution"] = (group["Year Req Val"].cumsum() / total_y23) * 100
            group["Contribution"] = group["Contribution"].round(2)
            return group

        # Apply the contribution calculation for each plant group
        future_forecast = future_forecast.groupby('Plant Code').apply(calculate_contribution).reset_index(drop=True)

        return future_forecast


    def determine_rm_segment(self, contribution):
        segments = self.rm_segmentation.get('segment')
        for segment, range_values in segments.items():
            lower_bound, upper_bound = range_values
            if lower_bound <= contribution <= upper_bound:
                return segment
        
    def rm_seg_volume(self):
        future_forecast = self.cummulative_contribution()
        future_forecast["RM Segment (Vol)"] = future_forecast["Contribution"].apply(self.determine_rm_segment)
        return future_forecast
        
    def oe_sku_mapping(self):
        future_forecast = self.rm_seg_volume()
        future_forecast = future_forecast.merge(self.product_master[["SKU","OE_SKU (Y/N)"]], left_on="RM Code", right_on='SKU', how='left')
        future_forecast.drop(columns=['SKU'], inplace=True)
        future_forecast.fillna({"OE_SKU (Y/N)": "N"}, inplace=True)
        return future_forecast
        
    def rm_segment_final(self):
        future_forecast = self.oe_sku_mapping()
        future_forecast['RM Segment Final'] = np.where(future_forecast['OE_SKU (Y/N)'] == 'N', future_forecast['RM Segment (Vol)'], 'A')
        return future_forecast
    
    def calculate_cv(self, row, sales_columns):
        monthly_values = row[sales_columns].values  # Exclude RM Code, Plant Code, and Variability
        mean_sales = np.mean(monthly_values)
        std_dev_sales = np.std(monthly_values)
        if mean_sales == 0:  # Prevent division by zero
            return 0
        return std_dev_sales / mean_sales
        
    def handle_outliers_using_median(self, row, sales_columns):
        # Extract the monthly values (using the dynamically selected columns)
        monthly_values = row[sales_columns].values

        # Exclude zero values for median calculation (do not include zeros in the median calculation)
        non_zero_values = monthly_values[monthly_values != 0]

        # Calculate Q1, Q3, and IQR based on non-zero values
        if len(non_zero_values) > 0:  # Ensure there are non-zero values to calculate median
            Q1 = np.percentile(non_zero_values, 5)
            Q3 = np.percentile(non_zero_values, 95)
            lower_bound = Q1
            upper_bound = Q3
        else:
            # If no non-zero values are available, return the row unchanged
            return row

        # Identify the outliers (values outside the IQR bounds)
        outlier_indices = (monthly_values < lower_bound) | (monthly_values > upper_bound)

        # If outliers are found, replace them with the median of non-zero values
        if np.any(outlier_indices):
            # Calculate median of non-zero values for imputation
            if len(non_zero_values) > 0:
                median_value = np.mean(non_zero_values)  # Median of non-zero values
            else:
                median_value = 0  # If no non-zero values, set median_value to 0 (you can choose another strategy)

            # Replace outliers with the median value
            monthly_values[outlier_indices] = median_value

        # Update the row with the modified values
        row[sales_columns] = monthly_values
        return row
    
    def handle_outliers(self):
        future_forecast = self.rm_segment_final()
        pattern = r'^\d{2}.?\d{4}$'
        # Dynamically select columns that match the pattern for monthly sales
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, col)]
        for index, row in future_forecast.iterrows():
            cv = self.calculate_cv(row, sales_columns)
            if cv > 1.0:
                future_forecast.loc[index] = self.handle_outliers_using_median(row, sales_columns)
        return future_forecast
            
    def variability(self):
        future_forecast = self.handle_outliers()
        pattern = r'^\d{2}.?\d{4}$'
        sales_columns = [col for col in future_forecast.columns if re.match(pattern, col)]
        future_forecast['Mean_RM_Sales'] =future_forecast[sales_columns].mean(axis=1).round(5)
        future_forecast['Std_dev_RM_Sales'] =future_forecast[sales_columns].std(axis=1).round(5)
        future_forecast['CV_RM_Sales'] = (future_forecast['Std_dev_RM_Sales'] /future_forecast['Mean_RM_Sales']).round(5)
        future_forecast["Variability"] =future_forecast["CV_RM_Sales"]*100
        future_forecast["Variability"] = future_forecast["Variability"].round(2)
        return future_forecast             
    
    def determine_rm_level(self, var):
        variations = self.rm_segmentation.get('variance')
        for variation, range_values in variations.items():
            lower_bound, upper_bound = range_values
            if lower_bound <= var <= upper_bound:
                return variation

    def rm_segment_level(self):
        future_forecast = self.variability()
        future_forecast["RM_Segment_Level"] = future_forecast["Variability"].apply(self.determine_rm_level)
        return future_forecast
        
    def segmentation(self):
        future_forecast = self.rm_segment_level()
        future_forecast["Segmentation"] = future_forecast["RM Segment Final"] + future_forecast["RM_Segment_Level"]
        return future_forecast

    def service_level(self):
        future_forecast = self.segmentation()
        future_forecast["Service_Level(%)"] = future_forecast["Segmentation"].map(self.service_mapping)
        future_forecast = future_forecast.drop_duplicates()
        self.dataframes["rm_segmentation_output"] = future_forecast
        return self.dataframes
    
    def calculate(self):
        return self.service_level()
