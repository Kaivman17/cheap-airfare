import requests
import sys

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

import schedule
import time

def check_flights():
    url ='https://www.google.com/flights/explore/#explore;f=JFK,EWR,LGA;t=r-Europe-0x46ed8886cfadda85%253A0x72ef99e6b3fcf079;li=3;lx=5;d=2018-01-13'
    driver = webdriver.PhantomJS()
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36")
    driver = webdriver.PhantomJS(desired_capabilities=dcap,service_args=['--ignore-ssl-errors=true'])
    driver.implicitly_wait(20)
    driver.get(url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located(By.CSS_selector, 'span.CTPFVNB-v-c'))

    s = BeautifulSoup(driver.page_source, 'lxml')

    best_price_tags = s.findAll('div', 'CTPFVNB-w-e')

    # check if scrape worked - alert if it fails and shutdown
    if len(best_price_tags) < 4:
        print('Failed to Load Page Data')
        requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/Odv6pQyTv4Jxn3ackE31h',
                        data={'value1': 'script', 'value2': 'failed', 'value3': ''})

        sys.exit(0)
    else:
        print('Successfully Loaded Page Data')

    best_prices = []
    for tag in best_price_tags:
        best_prices.append(int(tag.text.replace('$','').replace(',','')))

    best_height_tags = s.findAll('div', 'CTPFVNB-w-f')

    best_heights = []
    for t in best_height_tags:
        best_heights.append(float(t.attrs['style']\
              .split('height:')[1].replace('px;','')))

    pph = np.array(best_price) / np.array(best_height)

    cities = s.findAll('div', 'CTPFVNB-w-o')

    hlist = []
    for bar in cities[0].findAll('div', 'CTPFVNB-w-x'):
        hlist.append(float(bar['style'].split('height: ')[1].replace('px;',''))*pph)

    fares = pd.DataFrame(hlist, columns=['price'])

    px = [x for x in fares['price']]
    ff = pd.DataFrame(px, columns=['fare']).reset_index()

    X = StandardScaler().fit_transform(ff)
    db = DBSCAN(eps=.5, min_samples=1).fit(X)
    labels = db.labels_
    clusters = len(set(labels))
    unique_labels = set(labels)

    pf = pd.concat([ff, pd.DataFrame(db.labels_,columns=['cluster'])], axis=1)
    rf = pf.groupby('cluster')['fare'].agg(['min','count']).sort_values('min', ascending=True)

    # set up our rules
    # must have more than one cluster
    # cluster min must be equal to lowest price fare
    # cluster size must be less than 10th percentile
    # cluster must be $100 less the next lowest-priced cluster
    if clusters > 1\
        and ff['fare'].min() == rf.iloc[0]['min']\
        and rf.iloc[0]['count'] < rf['count'].quantile(.10)\
        and rf.iloc[0]['fare'] + 100 < rf.iloc[1]['fare']:
            city = s.find('span', 'CTPFVNB-v-c').text
            fare = s.find('div', 'CTPFVNB-w-e').text
            requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/Odv6pQyTv4Jxn3ackE31h',
                data = {'value1': city, 'value2': fare, 'value3': ''})
    else:
        print('no alert triggered')

    # set up the scheduler to run code every 60 min
    schedule.every(60).minutes.do(check_flights)

    while 1:
        schedule.run_pending()
        time.sleep(1)

print('Successfully Build')
