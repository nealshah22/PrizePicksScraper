from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import load_workbook

import undetected_chromedriver as uc

import time
import pandas as pd

############################################################################

driver = uc.Chrome()

###########################################################################


driver.get("https://app.prizepicks.com/")

WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "close")))
driver.find_element(By.CLASS_NAME, "close").click()


ppPlayers = []

# Select Sport
driver.find_element(By.XPATH, "//div[@class='name'][normalize-space()='NBA']").click()
print("clicked NBA")

stat_container = WebDriverWait(driver, 1).until(EC.visibility_of_element_located((By.CLASS_NAME, "stat-container")))

# All categories:
# categories = driver.find_element(By.CSS_SELECTOR, ".stat-container").text.split('\n')

categories = ["Points", "Pts+Rebs+Asts", "Assists", "Rebounds", "3-PT Made", "Pts+Rebs", "Pts+Asts", "Blocked Shots", "Steals", "Rebs+Asts", "Blks+Stls", "Turnovers"]

print(categories)

for category in categories:
    driver.find_element(By.XPATH, f"//div[text()='{category}']").click()
    print("clicked on " + category + " category")
    projectionsPP = WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "pp-container")))
    print("projectionsPP loaded:")
    print(projectionsPP)
    print("\n")

    for projections in projectionsPP:
        projectionsList = WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".projections-list > li")))
    
    for li in projectionsList:
        # Now 'li' represents each <li> element within the projections list.
        # Extract the necessary details from each 'li'.
        names = li.find_element(By.CLASS_NAME, "name").text
        print(names)
        value = li.find_element(By.CLASS_NAME, "score").get_attribute('innerHTML')
        proptype = li.find_element(By.CLASS_NAME, "text").get_attribute('innerHTML')
        
        goblin = "Standard"

        try:
            odds_icon = li.find_element(By.CLASS_NAME, "max-w-none")
            goblin = odds_icon.get_attribute('alt')
            if goblin == "Demon": 
                goblin = "Red"
            elif goblin == "Goblin":
                goblin = "Green"
            
        except:
            print("no goblin")
        
        # Now 'goblin' will be "not standard" if the "odds-icon" div is not empty, and "standard" otherwise.
        players = {
            'Name': names,
            'Value': value,
            'Prop': proptype.replace("<wbr>", ""),
            'Goblin': goblin
        }
        ppPlayers.append(players)

dfProps = pd.DataFrame(ppPlayers)
# CHANGE THE NAME OF THE FILE TO YOUR LIKING
dfProps.to_csv('LineProps.csv')

print("These are all of the props offered by PP.", '\n')
print(dfProps)
print('\n')
