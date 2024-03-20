from flask import Flask, request, render_template, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import pandas as pd
import time

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    vin_input = request.form['vin_numbers']
    vin_numbers = vin_input.splitlines() 
    df = scrape_vin_data(vin_numbers)

    df['Vehicle Type'] = df['Vehicle Type'].str.replace('Vehicle Type: ', '')
    df['Body Class'] = df['Body Class'].str.replace('Body Class: ', '')
    df['Weight'] = df['Weight'].str.replace('Gross Vehicle Weight Rating: ', '')
    df['Weight'] = df['Weight'].str.replace(r'.*:\s+', '', regex=True)
    df['Weight'] = df['Weight'].str.replace(r'\(.*?\)', '', regex=True).str.strip()

    df.loc[df['Vehicle Type'].str.contains("Vehicle Type:"), 'Vehicle Type'] = "Invalid VIN"
    df.loc[df['Vehicle Type'] == "Invalid VIN", ['Body Class', 'Weight']] = ""

    df.loc[df['Body Class'].str.contains("Body Class:"), 'Body Class'] = "--"
    df.loc[df['Weight'].str.contains("Gross Vehicle Weight Rating:"), 'Weight'] = "--"

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
            body_class = row['Body Class']
            
            if weight < 10000 and 'truck' not in body_class.lower() and 'pickup' not in body_class.lower() and 'cargo van' not in body_class.lower():
                return 'Private Passengers'
            elif 'cargo van' in body_class.lower():
                return 'Cargo van'
            elif weight <= 10000:
                return 'Light truck'
            elif 10000 < weight <= 20000:
                return 'Medium Truck'
            elif 20000 < weight <= 33000:
                return 'Heavy Truck'
            elif weight > 33000:
                return 'Extra heavy Truck'
            else:
                return 'Other'

    df['Classification'] = df.apply(classify_vehicle, axis=1)

    csv_filename = 'vehicle_data.csv' # Edit this to change the output filename
    df.to_csv(csv_filename, index=False)

    return send_file(csv_filename, as_attachment=True, mimetype='text/csv')

if __name__ == "__main__":
    app.run(debug=True)