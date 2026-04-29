import statistics
import math
import pandas as pd
from datetime import datetime
from src.helper import GLOBAL_CONFIG

class DemandVariationUtils:
    def __init__(self) -> None:
        self.maximum_percent_forecast = (GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('Maximum Demand in % of Forecast'))
        self.demand_variation_method = GLOBAL_CONFIG['global_parameters'][0]['forecast'].get('demand_variation_method')
        if self.maximum_percent_forecast is not None:
            self.maximum_percent_forecast = self.maximum_percent_forecast / 100

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
            if month:
                return post_date.month
            return post_date.year
        except:
            return None

    def fetch_month_week_year(self, consumption_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Adds Week, Post Date (formatted), Month, and Year columns to the consumption dataframe.
        '''
        try:
            consumption_df["Week"] = consumption_df["Post Week"].apply(self.fetch_week_no)
            consumption_df["post_date_form"] = consumption_df["Post Date"].apply(self.fetch_post_date)
            consumption_df["Month"] = consumption_df["post_date_form"].apply(self.fetch_post_date_data, args=(True,))
            consumption_df["Year"] = consumption_df["post_date_form"].apply(self.fetch_post_date_data, args=(False,))
            return consumption_df
        except Exception as e:
            raise RuntimeError(f"Error while processing month, week, and year data: {e}")

    def fetch_sorted_consumption_df(self, consumption_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Groups and sums 'Movement Qty' by 'Week', and sorts by 'post_date_form'.
        Returns the sorted dataframe.
        '''
        df_grouped = consumption_df.groupby(['Plant Code', 'Week', 'Month', 'Year'], as_index=False).agg({
            "Movement Qty": "sum",
            "RM Code": "first",
            "post_date_form": "first"
        })
        df_sorted = df_grouped.sort_values(by=['post_date_form'], ascending=True)
        return df_sorted

    @staticmethod
    def fetch_forecast_value(post_date, forecast_df_rm_code: pd.DataFrame):
        '''
        Fetches forecast value from a forecast dataframe based on the year and month of the post date.
        '''
        try:
            if post_date:
                month_str = f"{post_date.month:02d}"
                yearmonth = int(f"{post_date.year}{month_str}")
                if type(forecast_df_rm_code.get(yearmonth)) == pd.Series:
                    return forecast_df_rm_code.get(yearmonth).values[0].round(2)
                return forecast_df_rm_code.get(yearmonth, None)
        except Exception:
            return None

    def add_forecast_col(self, consumption_df: pd.DataFrame, forecast_df_rm_code: pd.DataFrame) -> pd.DataFrame:
        '''
        Adds a 'Forecast' column to the consumption dataframe, using the forecast values based on the post date.
        '''
        # consumption_df['post_date_form'] = pd.to_datetime(consumption_df['post_date_form'], errors='coerce')
        consumption_df["Forecast"] = consumption_df["post_date_form"].apply(
            self.fetch_forecast_value, args=(forecast_df_rm_code,))
        return consumption_df

    def with_skewness_calc(self, consumption_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Calculates demand variation with skewness:
        - Calculates the total movement quantity for each month.
        - Calculates RC By Week as the movement quantity divided by the total movement quantity, multiplied by the forecast.
        - Calculates delta as the difference between movement quantity and RC By Week.
        '''
        total_movement_qty_df = consumption_df.groupby(['Plant Code', 'Month', 'Year'], as_index=False).agg({
            'Movement Qty': 'sum'
        }).rename(columns={"Movement Qty": 'Total'})
        final_output = pd.merge(consumption_df, total_movement_qty_df, on="Month")
        final_output["RC By Week"] = (final_output["Movement Qty"] / final_output["Total"]) * final_output["Forecast"]
        final_output["delta"] = final_output["Movement Qty"] - final_output["RC By Week"]
        return final_output

    def without_skewness_calc(self, consumption_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Calculates demand variation without skewness:
        - Calculates the number of weeks for each month.
        - Calculates RC By Week as the forecast divided by the week count.
        - Calculates delta as the difference between movement quantity and RC By Week.
        '''
        week_count_df = consumption_df.groupby(['Plant Code', 'Month', 'Year'], as_index=False).agg({
            'Week': 'count'
        }).rename(columns={"Week": 'week_count'})
        final_output = pd.merge(consumption_df, week_count_df, on="Month")
        final_output["RC By Week"] = final_output["Forecast"] / final_output["week_count"]
        final_output["delta"] = final_output["Movement Qty"] - final_output["RC By Week"]
        return final_output

    @staticmethod
    def if_less_than_0(delta):
        '''
        Returns None if delta is less than 0, otherwise returns delta.
        '''
        if delta is not None and delta < 0:
            return None
        return delta

    def removing_less_than_0_val(self, final_output_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Sets the delta to None where delta is negative (for "under-forecast" cases).
        '''
        final_output_df["delta"] = final_output_df["delta"].apply(self.if_less_than_0)
        return final_output_df

    def add_percent_to_forecast(self, final_output_df: pd.DataFrame) -> pd.DataFrame:
        '''
        % to forecast is M-Weekly Total (Movement Qty) / RC by week
        '''
        final_output_df['% to forecast'] = final_output_df.apply(
                    lambda row: (row['Movement Qty'] / row['RC By Week']) * 100
                    if pd.notna(row['RC By Week']) and row['RC By Week'] != 0 and pd.notna(row['delta'])
                    else None,
                    axis=1
                )

        return final_output_df

    def revised_actual_consumption(self, final_output_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Revised actual consumption based on the global param - Percent cap for demand variation
        The formula has changed to:
        - If % to forecast > maximum_percent_forecast, RAC = RC By Week * maximum_percent_forecast
        - If % to forecast < maximum_percent_forecast, RAC = Movement Qty
        '''
        final_output_df['Revised Actual Consumption'] = final_output_df.apply(
                    lambda row: (
                        row['RC By Week'] * self.maximum_percent_forecast if pd.notna(row['% to forecast']) and row['% to forecast'] > (self.maximum_percent_forecast * 100) and pd.notna(row['delta'])
                        else row['Movement Qty'] if pd.notna(row['delta'])
                        else None
                    ),
                    axis=1
                )

        return final_output_df

    def new_over_consumption(self, final_output_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Here if the % to forecast if greater than the maximum percent forecast in global param then it will be changed.
        '''
        final_output_df['new over consumption'] = final_output_df['Revised Actual Consumption'] - final_output_df['RC By Week']
        # if self.demand_variation_method=="Under":
        #     final_output_df['new over consumption'] = final_output_df['new over consumption'].apply(lambda x: max(x, 0))
        return final_output_df

    def calculate_weekly_rmse(self, final_output_df: pd.DataFrame) -> dict:
        '''
        Calculates the weekly RMSE (root mean square error) for the RM Code and updates the week_rmse_rm_map.
        '''
        if self.maximum_percent_forecast is not None:
            deltas = final_output_df['new over consumption'].dropna()
            # if self.demand_variation_method=="Under":
            #     deltas = deltas[deltas > 0]
        else:
            deltas = final_output_df['delta'].dropna()
            # if self.demand_variation_method=="Under":
            #     deltas = deltas[deltas > 0]
        if final_output_df.empty:
            week_rmse = 0
        else:
            final_output_df["sq_delta"] = deltas.apply(lambda x:x**2)
            deltas = final_output_df["sq_delta"].dropna()
            if not deltas.empty:
                week_rmse = math.sqrt(statistics.mean(deltas))
            else:
                week_rmse = 0
        return week_rmse
