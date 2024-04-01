from flask import Flask, request, render_template, send_file
import pandas as pd
import time
import numpy as np
import xlrd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from werkzeug.utils import secure_filename

app = Flask(__name__)

def scrape_vin_data(vin_numbers):
    driver = webdriver.Chrome()
    driver.get("https://vpic.nhtsa.dot.gov/decoder/")
    df = pd.DataFrame(columns=['VIN', 'Vehicle Type', 'Body Class', 'Weight'])

    for vin in vin_numbers:
        vin_input = driver.find_element(By.ID, "VIN")
        vin_input.clear()
        vin_input.send_keys(vin)
        decode_button = driver.find_element(By.ID, "btnSubmit")
        decode_button.click()
        time.sleep(0.5) 

        try:
            vehicle_type = driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[2]/div/div[2]/div[2]/div[1]/p[3]").text

            body_class = driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[2]/div/div[2]/div[2]/div[1]/p[7]").text

            if "INCOMPLETE VEHICLE" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/div[1]/div").text
            elif "TRAILER" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/p[2]").text
            elif "MOTORCYCLE" in vehicle_type:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/p[2]").text
            else:
                weight = driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/div[2]/div[2]/div[1]").text

        except (NoSuchElementException, WebDriverException) as e:
            vehicle_type = "Check VIN"
            body_class = ""
            weight = ""
        
        new_row = pd.DataFrame({'VIN': [vin], 'Vehicle Type': [vehicle_type], 'Body Class': [body_class], 'Weight': [weight]})
        df = pd.concat([df, new_row], ignore_index=True)

        driver.refresh()        

    driver.quit()
    return df

def clean_df(df):
    df['Vehicle Type'] = df['Vehicle Type'].str.replace('Vehicle Type: ', '')
    df['Body Class'] = df['Body Class'].str.replace('Body Class: ', '')
    df['Weight'] = df['Weight'].str.replace('Gross Vehicle Weight Rating: ', '')
    df['Weight'] = df['Weight'].str.replace(r'.*:\s+', '', regex=True)
    df['Weight'] = df['Weight'].str.replace(r'\(.*?\)', '', regex=True).str.strip()

    df.loc[df['Vehicle Type'].str.contains("Vehicle Type:"), 'Vehicle Type'] = "Invalid VIN"
    df.loc[df['Vehicle Type'] == "Invalid VIN", ['Body Class', 'Weight']] = ""

    df.loc[df['Body Class'].str.contains("Body Class:"), 'Body Class'] = "--"
    df.loc[df['Weight'].str.contains("Gross Vehicle Weight Rating:"), 'Weight'] = "--"

def read_excel(filepath):
    return pd.read_excel(filepath, sheet_name=1, header=None, names=['VIN'], usecols=[6], skiprows=4)

def classify_vehicle(row):
    if 'Invalid VIN' in row['Vehicle Type']:
        return 'Invalid VIN'
    elif 'TRAILER' in row['Vehicle Type']:
        return 'Trailer'
    elif 'Truck-Tractor' in row['Body Class'] or 'Semi' in row['Body Class']:
        return 'Truck Tractor'
    elif 'Trailer' in row['Body Class']:
        return 'Trailer'
    elif 'Bus' in row['Body Class']:
        return 'Bus'
    else:
        weight = row['Weight'].split(' ')[0].replace(',', '')
        weight = int(weight) if weight.isdigit() else 0

        if weight < 10000 and 'truck' not in row['Body Class'].lower() and 'pickup' not in row['Body Class'].lower():
            return 'Private Passengers'
        elif 'cargo van' in row['Body Class'].lower():
            return 'Cargo van'
        elif weight <= 10000:
            return 'Light truck'
        elif 10000 < weight <= 20000:
            return 'Medium Truck'
        elif 20000 < weight <= 33000:
            return 'Heavy Truck'
        elif weight > 33000:
            return 'Extra Heavy Truck'
        else:
            return 'Other'

@app.route('/')
def index():
    if request.method == 'POST':
        vin_input = request.form['vin_numbers']
        vin_numbers = vin_input.splitlines()

        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        scraped_df = scrape_vin_data(vin_numbers)

        df = pd.read_excel(filepath, sheet_name=1, header=None, names=['VIN'], usecols=[6], skiprows=4)
        classified_df = process_excel(filepath, pd.concat([scraped_df, df], ignore_index=True))

        return send_file(filepath, as_attachment=True)

    return render_template('index.html')

def classify_vehicle(row):
        vin_char_key = { 
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 
            'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9, 'S': 2, 
            'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9 
        } 
        position_weights = {
            1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 10, 9: 0, 10: 9, 
            11: 8, 12: 7, 13: 6, 14: 5, 15: 4, 16: 3, 17: 2 
        } 

        def replace_alphas(string, key): 
            return ''.join(str(key[c]) if c in key else c for c in string) 

        def multiply_digits(string, weights): 
            factors = np.array([int(c) for c in string]) 
            weighted_sum = sum(factors * [weights[i+1] for i in range(len(factors))]) 
            return weighted_sum 

        vin_sample = pd.read_excel(filename, sheet_name=1, header=None, names=['VIN'], usecols=[6], skiprows=4) 
        
        vin_sample['valid_LC'] = np.where( 
            (vin_sample['VIN'].str.len() == 17) & 
            (~vin_sample['VIN'].str.contains('[IOQ]', case=False, regex=True)), 
            'VALID', 'MANUAL' 
        ) 

        def check_digit_validation(row): 
            if row['valid_LC'] == 'VALID': 
                actual_check_digit = row['VIN'][8] 
                transformed_vector = replace_alphas(row['VIN'], vin_char_key) 
                vin_sums = multiply_digits(transformed_vector, position_weights) 
                predicted_check_digit = vin_sums % 11 
                predicted_check_digit = 'X' if predicted_check_digit == 10 else str(predicted_check_digit) 
                return 'VALID' if actual_check_digit == predicted_check_digit else 'MANUAL' 
            else: 
                return 'MANUAL' 

        vin_sample['valid_checkdigit'] = vin_sample.apply(check_digit_validation, axis=1) 

        manual_vin_check = vin_sample[vin_sample['valid_checkdigit'] == 'MANUAL'][['VIN']] 
        manual_vin_check.reset_index(inplace=True) 
        manual_vin_check.rename(columns={'index': 'row_number'}, inplace=True) 

        wb = xlrd.load_workbook(filename) 
        ws = wb.create_sheet(title="Manual") 
        for r in dataframe_to_rows(manual_vin_check, index=False, header=True): 
            ws.append(r) 

        wb.save(filename) 


@app.route('/submit', methods=['POST'])
def submit():
    vin_input = request.form['vin_numbers']
    vin_numbers = vin_input.splitlines() 
    df = scrape_vin_data(vin_numbers)

    

    f = request.files['file']
    filename = secure_filename(f.filename)
    filepath = os.path.join('uploads', filename)
    f.save(filepath)

    with pd.ExcelWriter(filepath, engine='xlrd', mode='a') as writer:  
        manual_vin_check.to_excel(writer, sheet_name='Manual')

    return send_file(filepath, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
