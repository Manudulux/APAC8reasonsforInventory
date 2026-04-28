import statistics, pandas as pd
from datetime import datetime
import re

class DailySalesUtils:
    @staticmethod
    def fetch_week_no(post_week_val: str):
        '''
        Extract week number from a string format (e.g., "1.0").
        Returns None if the input is invalid.
        '''
        try:
            return int(str(post_week_val).split(".")[0])
        except ValueError:
            return None

    @staticmethod
    def fetch_post_date(post_date: str):
        '''
        Convert string post date in the format "dd.mm.yyyy" to a Python date object.
        Returns None if the conversion fails.
        '''
        try:
            return datetime.strptime(post_date, "%d.%m.%Y").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def fetch_post_date_data(post_date:datetime, month:bool):
        '''
        Fetching Month and Year and Then Adding those columns into Consumption DF
        '''
        try:
            if post_date:
                if month:
                    return post_date.month
                return post_date.year
        except:
            return None

    def fetch_month_week_year(self, rm_code,plant_code, consumption_df: pd.DataFrame) -> float:
        '''
        Adds Week, Post Date (formatted), Month, and Year columns to the consumption dataframe.
        '''
        try:
            rm_consumption_df = consumption_df[(consumption_df["RM Code"]==rm_code) & (consumption_df['Plant Code'] == plant_code)]
            if rm_consumption_df.empty:
                return None
            rm_consumption_df["Week"] = rm_consumption_df["Post Week"].apply(self.fetch_week_no)
            rm_consumption_df["post_date_form"] = rm_consumption_df["Post Date"].apply(self.fetch_post_date)
            rm_consumption_df["Month"] = rm_consumption_df["post_date_form"].apply(self.fetch_post_date_data, args=(True,))
            rm_consumption_df["Year"] = rm_consumption_df["post_date_form"].apply(self.fetch_post_date_data, args=(False,))
            df_grouped = rm_consumption_df.groupby(['Week', 'Month', 'Year'], as_index=False).agg({
            "Movement Qty": "sum",
            "RM Code": "first",
            "post_date_form": "first"
        })
            df_sorted = df_grouped.sort_values(by=['post_date_form'], ascending=True)
            average_weekly = statistics.mean(df_sorted["Movement Qty"])*-1
            if average_weekly:
                return average_weekly/7
            return average_weekly
        except Exception as e:
            raise RuntimeError(f"Error while processing month, week, and year data: {e}")
        
    def total_sales_forecast(self, future_df):
        future_df.columns = future_df.columns.astype("str")
        pattern = r'^\d{2}.?\d{4}$'
        sales_columns = [col for col in future_df.columns if re.match(pattern, col)]
        future_df['Total_RM_Sales'] = future_df[sales_columns].sum(axis=1).round(5)
        return future_df
