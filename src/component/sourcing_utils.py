import pandas as pd
import statistics
from collections import Counter
import datetime
import numpy as np

class SourcingUtils:
    def __init__(self) -> None:
        pass

    def add_transit_time(self, supply_shipping_df) -> pd.DataFrame:
        try:
            supply_shipping_df['ATA \n(POD)'] = pd.to_datetime(supply_shipping_df['ATA \n(POD)'],
                format='%d-%m-%Y', errors='coerce')
            supply_shipping_df['ATD (POL)'] = pd.to_datetime(supply_shipping_df['ATD (POL)'],
                format='%d-%m-%Y', errors='coerce')
            supply_shipping_df["TT"] = supply_shipping_df["ATA \n(POD)"] - \
                supply_shipping_df["ATD (POL)"]
            supply_shipping_df['TT'] = (supply_shipping_df['ATA \n(POD)'] -
                supply_shipping_df['ATD (POL)']).dt.days
            return supply_shipping_df
        except Exception as e:
            raise e

    def modified_dfs(self, dataframes):
        supply_shipping_df = dataframes["Supply&Shipping_Var"]
        sourcing_df = dataframes["Sourcing_Data"]

        # Adding Transit Time in Supply and Shipping Variation DF
        shipping_tt_df = self.add_transit_time(supply_shipping_df)

        # Modifing and Combining RM and Supplier Code in Sourcing DF
        sourcing_df['RM Code'] = sourcing_df['RM Code'].apply(lambda x: str(int(x))
            if pd.notna(x) and float(x).is_integer() else str(x))
        sourcing_df['Supplier Code'] = sourcing_df['Supplier Code'].apply(lambda x: str(int(x))
            if pd.notna(x) and float(x).is_integer() else str(x))
        sourcing_df['Combined_Key'] = sourcing_df['Plant Code'] + '_' + sourcing_df['RM Code'] + '_' + sourcing_df['Supplier Code']

        # Modifing and Combining RM and Supplier Code in the Supply and Shipping Variation DF
        shipping_tt_df['Material Code'] = shipping_tt_df['Material Code'].apply(
            lambda x: str(int(x))
                if pd.notna(x) and float(x).is_integer()
                else str(x))
        shipping_tt_df['Supplier'] = shipping_tt_df['Supplier'].apply(lambda x: str(int(x))
            if pd.notna(x) and float(x).is_integer() else str(x))
        shipping_tt_df['Combined_Key'] = shipping_tt_df['Plant Code'] + '_' + shipping_tt_df['Material Code'] + '_' + shipping_tt_df['Supplier']

        # Updating Dataframes Dictionary
        dataframes["Supply&Shipping_Var"] = shipping_tt_df
        dataframes["Sourcing_Data"] = sourcing_df
        return dataframes

    def week_to_date(self, week, year):
        # Convert the week and year to a date
        first_day_of_year = datetime.date(year, 1, 1)
        # Get the first Monday of the year
        first_monday = first_day_of_year + datetime.timedelta(days=(7 - first_day_of_year.weekday()) % 7)
        # Calculate the date corresponding to the given week number
        return first_monday + datetime.timedelta(weeks=week - 1)

    def calculate_post_week_diff(self, post_week):
        if not isinstance(post_week, list):  # Check if the post_week is a list
            return np.nan
        try:
            post_week = list(map(str, post_week))
            sorted_weeks = sorted(post_week, key=lambda x: (int(x.split('.')[1]), int(x.split('.')[0])))
            dates = [self.week_to_date(int(week.split('.')[0]), int(week.split('.')[1])) for week in sorted_weeks]
            difference = ((dates[-1] - dates[0]).days // 7) + 1
            return round(difference, 4)
        except Exception as e:
            print(f"Error calculating week diff: {e}")
            return np.nan

    def calculating_post_week_sum(self, post_week):
        if not isinstance(post_week, list):  # Check if the post_week is a list
            return np.nan
        try:
            # Splitting Month and Year from Post Week
            post_week = [str(week).split(".")[0] for week in post_week]
            # Getting Week with its Count in the dictionary format 
            week_count = dict(Counter(post_week))
            # Extracting Dictionary Values to Find its Average
            count_values = week_count.values()
            values_mean = sum(count_values)
            if not values_mean:
                return np.nan
            return round(values_mean, 4)
        except Exception as e:
            print(f"Error calculating week sum: {e}")
            return np.nan

    def calculating_post_week_std(self, post_week):
        try:
            if isinstance(post_week, list):
                # Splitting Month and Year from Post Week
                post_week = [str(week).split(".")[0] for week in post_week]
                # Getting Week with its Count in the dictionary format
                week_count = dict(Counter(post_week))
                # Extracting Dictionary Values to Find its Average
                count_values = list(week_count.values())
                values_avg = np.average(count_values)
                values_std = statistics.stdev(count_values)

                if not values_std:
                    return 1
                return (values_std / values_avg) * 100
            return 1
        except:
            return 1

    def modifing_shipping_interval(self, dataframes) -> pd.DataFrame:
        shipping_interval_df = dataframes["Shipping_Interval"]
        shipping_interval_df['RM Code'] = shipping_interval_df['RM Code'].apply(lambda x: str(int(x))
            if pd.notna(x) and float(x).is_integer() else str(x))
        shipping_interval_df['Supplier'] = shipping_interval_df['Supplier'].apply(lambda x: str(int(x))
            if pd.notna(x) and float(x).is_integer() else str(x))
        shipping_interval_df['Combined_Key'] = shipping_interval_df['Plant Code'] + '_' + shipping_interval_df['RM Code'] + '_' + shipping_interval_df['Supplier']
        return shipping_interval_df

    def remove_unnecessary_cols(self, dataframes)->dict:
        sourcing_df = dataframes["Sourcing_Data"]
        drop_list = ["Combined_Key", "Post Week"]
        sourcing_df.drop(drop_list, axis=1, inplace=True)
        return sourcing_df

    def get_lot_size(self, group):
        # Count frequency of each value
        frequency = group["Movement Qty"].value_counts()
        frequency = frequency[frequency.index >= 0]
        if frequency.empty:
            result = 0
        if frequency.nunique() == 1:
            # If all frequencies are the same, take the minimum value
            result = group["Movement Qty"].min()
        else:
            # If frequencies are different, take the value with the max count
            result = frequency.idxmax()
        return result