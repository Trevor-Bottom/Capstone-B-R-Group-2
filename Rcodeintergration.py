import pandas as pd
import numpy as np

# VIN char key
vin_char_key = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
                'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9, 'S': 2,
                'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9}

# Position multipliers
position_weights = {'1': 8, '2': 7, '3': 6, '4': 5, '5': 4, '6': 3, '7': 2, '8': 10,
                    '9': 0, '10': 9, '11': 8, '12': 7, '13': 6, '14': 5, '15': 4,
                    '16': 3, '17': 2}

# Function to convert letters to integers
def replace_alphas(string, key):
    replaced_alphas = ''.join(str(key[char]) if char in key else char for char in string)
    return replaced_alphas

# Function to produce vin product sum
def multiply_digits(string, weights):
    factor_vector = np.array(list(string), dtype=int)
    product_vector = factor_vector * np.array(list(weights.values()))
    return np.sum(product_vector)

# Load data
current_fleet = "Practice_Fleet.xlsx"
vin_sample = pd.read_excel(current_fleet, sheet_name=1, header=None, usecols="E:G", skiprows=4)
vin_sample.columns = ['Make', 'Model', 'VIN']


# Check for string length and proper characters
vin_sample['valid_LC'] = np.where((vin_sample['VIN'].str.len() == 17) &
                                  (~vin_sample['VIN'].str.contains('I|O|Q', case=False)), 'VALID', 'MANUAL')

# Verify the check digit information
vin_sample['valid_checkdigit'] = vin_sample.apply(lambda row: 'VALID' if row['valid_LC'] == 'VALID' else 'MANUAL', axis=1)

for i, row in vin_sample.iterrows():
    if row['valid_checkdigit'] == 'VALID':
        actual_check_digit = row[2][8]
        auto_vin_check = row[2]
        transformed_vector = replace_alphas(auto_vin_check, vin_char_key)
        vin_sums = multiply_digits(transformed_vector, position_weights)
        predicted_check_digit = vin_sums % 11
        predicted_check_digit = 'X' if predicted_check_digit == 10 else str(predicted_check_digit)
        check_digit_match = actual_check_digit == predicted_check_digit
        vin_sample.at[i, 'valid_checkdigit'] = 'VALID' if check_digit_match else 'MANUAL'

manual_rows = vin_sample.index[vin_sample['valid_checkdigit'] == 'MANUAL']
manual_vin_check = vin_sample.loc[manual_rows, ['VIN']].reset_index(drop=True)

# Load scraped fleet info
scraped_fleet_info = pd.read_csv("scraped_presentation_1000.csv")
scraped_fleet_info['Weight_edit'] = scraped_fleet_info['Weight'].str.strip()
#scraped_fleet_info[['Weight_lowend', 'Weight_highend']] = scraped_fleet_info['Weight_edit'].str.split('-', expand=True)

# Split 'Weight_edit' column into two columns based on '-'
split_weights = scraped_fleet_info['Weight_edit'].str.split('-', expand=True)

# Check if exactly two columns are generated
if len(split_weights.columns) == 2:
    scraped_fleet_info[['Weight_lowend', 'Weight_highend']] = split_weights
else:
    # Handle the case where the split operation doesn't generate two columns
    # For example, you can assign NaN values or drop the 'Weight_lowend' and 'Weight_highend' columns
    # scraped_fleet_info[['Weight_lowend', 'Weight_highend']] = np.nan
    scraped_fleet_info.drop(columns=['Weight_lowend', 'Weight_highend'], inplace=True)


#scraped_fleet_info['Weight_mean'] = np.where(scraped_fleet_info['Weight_highend'].isna(),
                                             #scraped_fleet_info['Weight_lowend'],
                                             #(pd.to_numeric(scraped_fleet_info['Weight_lowend']) +
                                              #pd.to_numeric(scraped_fleet_info['Weight_highend'])) / 2)

# Classification based on weight mean
scraped_fleet_info['Classification1'] = pd.cut(scraped_fleet_info['Weight_mean'],
                                               bins=[-np.inf, 10000, 20000, 33000, np.inf],
                                               labels=['Light Truck', 'Medium Truck', 'Heavy Truck', 'Extra Heavy Truck'])

# Testing for invalid VINS
invalid_vin_rows = scraped_fleet_info.index[scraped_fleet_info['Vehicle.Type'] == "Invalid VIN"]
invalid_vin_check = pd.DataFrame({'row_number': invalid_vin_rows, 'vin_value': scraped_fleet_info.loc[invalid_vin_rows, 'VIN']})
odd_vins = pd.concat([invalid_vin_check['vin_value'], manual_vin_check['vin_value']]).unique()
unique_vins_to_check = np.intersect1d(odd_vins, scraped_fleet_info['VIN'])

# Matching VINs
matching_make_rows = scraped_fleet_info.index[scraped_fleet_info['VIN'].isin(unique_vins_to_check)]
matching_classification_rows = scraped_fleet_info.index[scraped_fleet_info['VIN'].isin(unique_vins_to_check)]

all_vins_to_check = pd.DataFrame({'row_number': matching_make_rows, 'vin_value': unique_vins_to_check})
all_vins_to_check['Classification'] = scraped_fleet_info.loc[matching_classification_rows, 'Classification1']
all_vins_to_check['Make'] = scraped_fleet_info.loc[matching_make_rows, 'Make']
all_vins_to_check['Model'] = scraped_fleet_info.loc[matching_make_rows, 'Model']

# Write to Excel
with pd.ExcelWriter(current_fleet) as writer:
    manual_vin_check.to_excel(writer, sheet_name='Manual', index=False)
    scraped_fleet_info.to_excel(writer, sheet_name='Data', index=False)
