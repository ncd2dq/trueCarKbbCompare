'''
This module provides the ability to compare cars on truecar.com to their KBB value, filtering by No accidents and No Damage on their carfax report
'''

year_min = input("Year Minimum -> ") #'2017'
make = input("Make -> ") #'dodge'
model = input("Model -> ") #'challenger'
zip_code = '33063'
listing_max_count = 10

domain_kelly = 'https://www.kbb.com/'

'''
Get results from True Car
'''
import requests
from typing import List, Dict

def getTrueCarResultsUrls(year_min: str, make: str, model: str, max_page_tries: int=10) -> List:
    '''
    Gets all the href urls to cars on all pages for a specific car
    
    @param str year_min: Year of car
    @param str make: Make of car
    @param str model: Model of car
    @param int max_page_tries: Max page count this module will atempt to get car listings from
    
    @return List final_href_urls: Array of urls for all car results
    '''
    list_page_url = "https://www.truecar.com/used-cars-for-sale/listings/{}/{}/year-{}-max/location-pompano-beach-fl/".format(make.lower(), model.lower(), year_min)
    final_href_urls = []
    for i in range(1, max_page_tries):
        if i != 1:
            final_url = list_page_url + "?page={}".format(i)
        else:
            final_url = list_page_url
        print("Getting page {}...".format(i))
        resp = requests.get(final_url)
        if resp.status_code == 200:
            html_text = resp.text
        else:
            break

        all_car_divs = getAllCarDivIndexes(html_text)
        print("Getting all cars on page {}...".format(i))
        all_car_hrefs = [getNextCarHref(html_text, div_index) for div_index in all_car_divs]
        final_href_urls += all_car_hrefs

    return final_href_urls


def getAllCarDivIndexes(resp_text: str) -> List[int]:
    '''
    Find all div tags containing car listings / urls
    
    @param str resp_text: the entire listing page html str

    @return List all_indexes: list of indexes of all car <div> tags on current page
    '''
    all_indexes = []
    key = '<div data-qa="VehicleListing"'

    result = ''
    while result != -1:
        offset = 0
        if len(all_indexes) != 0:
            offset = all_indexes[-1] + 5
        result = resp_text[offset:].find(key)
        if result == -1:
            break
        all_indexes.append(result + offset)

    return all_indexes

def getNextCarHref(resp_text: str, div_index: int) -> str:
    '''
    For a given index, get the very next href
    
    @param str resp_text: the entire listing page html str
    @param int div_index: the index location of the car listing div tag

    @return str: the url of the very next href starting at index @div_index
    '''
    domain_truecar = 'https://www.truecar.com/'
    sliced = resp_text[div_index:]
    href_index = sliced.find('href="')
    href_url = ''
    for i in range(len(sliced[href_index + 6:])):
        character = sliced[href_index + 6 + i]
        if character == '"':
            break
        else:
            href_url += character

    return domain_truecar + href_url[1:]


def checkCarFax(car_urls: List[str]) -> List[Dict]:
    '''
    Converts car_urls to dictionaries and filters out any cars that do not pass the carfax check
    
    @param List car_urls: A list of all car urls
    
    @return List[Dict]: A list of all car dictionaries for only the cars passing the carfax check
    '''
    checked_car_urls = []
    car_count = len(car_urls)
    for index, url in enumerate(car_urls):
        print("Checking carfax for car {}/{}".format(index + 1, car_count))
        carFaxUrlDict = getCarFaxUrl(url)
        if carFaxUrlDict["found"]:
            carFaxDict = filterCarFax(carFaxUrlDict)
            if carFaxDict["CarFax Clean"]:
                carFaxDict["car_url"] = url
                checked_car_urls.append(carFaxDict)
            else:
                pass
        else:
            pass

    return checked_car_urls


def getCarFaxUrl(url: str) -> Dict:
    '''
    Attempts to get free carfax url
    
    @param str url: Url to a specific car page
    
    @return List carFaxUrlDict: A dictionary object that contains a link to the free carfax report
    '''
    carFaxUrlDict = {"found": False, "carfax_url": ""}
    key = "https://www.carfax.com/VehicleHistory"
    resp = requests.get(url).text
    index = resp.find(key)

    if index == -1:
        return carFaxUrlDict
    else:
        carFaxUrlDict["found"] = True
        for character in resp[index:]:
            if character != '"':
                carFaxUrlDict["carfax_url"] += character
            else:
                break

    return carFaxUrlDict

def filterCarFax(carFaxDict: Dict) -> Dict:
    '''
    Attempts to check carfax url against filters
    
    @param Dict carFaxDict: A dictionary that should contain a carfax_url entry
    
    @return Dict carFaxDict: Contains a new key, CarFax Clean, that indicates if it passes all checks
    '''
    exclude = ['"Rental"']
    include = ['"No accidents reported"', '"No damage reported"']

    resp = requests.get(carFaxDict["carfax_url"]).text

    condition = True
    for item in exclude:
        if item in resp:
            condition = False
    for item in include:
        if item not in resp:
            condition = False

    if condition:
        carFaxDict["CarFax Clean"] = True
    else:
        carFaxDict["CarFax Clean"] = False

    return carFaxDict

def getTrueCarPricesAndSylesAndMilage(car_dicts):
    '''
    Gathers car price, style/trim, and mileage from truecar.com for a given car and inserts them into a the dictionaries within
    the list. 
    {'found': True, 'carfax_url': 'https://www.carfax.com/VehicleHistory/p/Report.cfx?vin=2C3CDZFJ9JH236377&amp;csearch=0&amp;partner=GAZ_0', 'CarFax Clean': True, 'car_url': 'https://www.truecar.com/used-cars-for-sale/listing/2C3CDZFJ9JH236377/2018-dodge-challenger/'}
    
    @param List[Dict] car_dicts: car dictionaries containing a car_url for the truecar.com link
    
    @return None
    '''
    # <span class="">$30,200</span>
    key_price = '<span class="">$'
    key_style = '"trimSlug":"'
    key_miles = '"mileage":'
    for index, url in enumerate(car_dicts):
        resp = requests.get(url["car_url"]).text

        index_start = resp.find(key_price)
        index_end = resp[index_start + 1:].find('<')
        price = resp[index_start + len(key_price):index_start + index_end + 1]
        price = price.replace(',', '')
        car_dicts[index]["truecar_price"] = int(price)

        # "styleSlug":"sxt-rwd-automatic"
        index_start = resp.find(key_style)
        index_end = resp[index_start + len(key_style):].find('"')
        style = resp[index_start + len(key_style):index_start + index_end + len(key_style)]
        car_dicts[index]["truecar_style"] = style

        # "mileage":31518,
        index_start = resp.find(key_miles)
        index_end = resp[index_start + len(key_miles):].find(',')
        miles = resp[index_start + len(key_miles):index_start + index_end + len(key_miles)]
        car_dicts[index]["truecar_miles"] = int(miles)


def getTrueCarDetails(car_dicts):
    '''
    Scrape year make model from url of truecar.com
    @param List[Dict] car_dicts: car dictionaries that should contain car_url
    
    @return None
    '''
    # https://www.truecar.com/used-cars-for-sale/listing/2C3CDZFJ9JH236377/2018-dodge-challenger/
    for index, item in enumerate(car_dicts):
        url = car_dicts[index]["car_url"]
        url = url[:-1]
        url_rev = url[::-1]
        last_slash = url_rev.find('/')
        try:
            year, make, model = url[-last_slash:].split('-')
        except Exception as e:
            year, make, model = '2018', 'dodge', 'challenger'
            print("Error with the following url: {}".format(url))
        car_dicts[index]["year"], car_dicts[index]["make"], car_dicts[index]["model"] = year, make, model


def getKbbPrices(car_dicts):
    '''
    Attempts to match year/make/model/trim/mileage to a KBB price and inserts it into each dictionary
    
    # TODO instead of a mapping, have this directly feed the trim to KBB
    https://www.kbb.com/dodge/challenger/2018/sxt-coupe-2d/?intent=buy-used&mileage=15587&pricetype=retail&condition=good

    sxt-coupe-2d
    sxt-plus-coupe-2d
    gt-coupe-2d
    r-t-coupe-2d
    t-a-coupe-2d
    r-t-plus-coupe-2d
    r-t-shaker-coupe-2d
    r-t-plus-shaker-coupe-2d
    t-a-plus-coupe-2d
    t-a-392-coupe-2d
    r-t-scat-pack-coupe-2d
    392-hemi-scat-pack-shaker-coupe-2d
    srt-392-coupe-2d
    
    @return None
    '''

    mapping = {
    "sxt-coupe-2d": ['sxt'],
    "sxt-plus-coupe-2d": ['sxt-plus'],
    "392-hemi-scat-pack-shaker-coupe-2d": ['392-hemi-scat-pack-shaker'],
    "gt-coupe-2d": ['gt'],
    "r-t-coupe-2d": ['r-t'],
    "r-t-plus-coupe-2d": ['r-t-plus'],
    "r-t-plus-shaker-coupe-2d": ['r-t-plus-shaker'],
    "r-t-scat-pack-coupe-2d": ['r-t-scat-pack'],
    "srt-392-coupe-2d": ['srt-392'],
    "t-a-392-coupe-2d": ['t-a-392'],
    "t-a-coupe-2d": ['t-a'],
    "t-a-plus-coupe-2d": ['t-a-plus'],
    "r-t-shaker-coupe-2d": ['r-t-shaker']
    }

    for index, car in enumerate(car_dicts):
        print("Getting KBB price for car {}/{}".format(index + 1, len(car_dicts)))
        found = False
        for key, value in mapping.items():
            for truecarStyle in value:
                if car["truecar_style"] == truecarStyle:
                    trim = key
                    found = True
                    car_dicts[index]["trim_found"] = True
                    break
        if not found:
            print("Skipping {}, could not find trim {}".format(car["car_url"], car["truecar_style"]))
            car_dicts[index]["trim_found"] = False
            continue

        kbb_url = "https://www.kbb.com/{}/{}/{}/{}/?intent=buy-used&mileage={}&pricetype=retail&condition=good".format(car["make"], car["model"], car["year"],
        trim ,car["truecar_miles"])
        car_dicts[index]["kbb_url"] = kbb_url
        resp = requests.get(kbb_url).text

        key = ";price="
        # ;price=22796&
        index_start = resp.find(key)
        index_end = resp[index_start + len(key):].find('&')
        price = resp[index_start + len(key):index_start + index_end + len(key)]
        car_dicts[index]["kbb_price"] = int(price)

def getResults(car_dicts):
    '''
    Changes data labels to something more human readable and sorts the output by price delta (truecar price - kbb price)
    
    @return List[Dict] new_list: All cars with new data labels and price delta
    '''

    new_list = []
    for car in car_dicts:
        if car["trim_found"]:
            new_car_dict = {
                "Year": car["year"],
                "Make": car["make"],
                "Model": car["model"],
                "Kbb Price": car["kbb_price"],
                "Truecar Price": car["truecar_price"],
                "Mileage": car["truecar_miles"],
                "Truecar URL": car["car_url"],
                "Carfax URL": car["carfax_url"],
                "Kbb URL": car["kbb_url"]
            }
            new_car_dict["Price Delta"] = int(new_car_dict["Truecar Price"]) - int(new_car_dict["Kbb Price"])
            new_list.append(new_car_dict)

    new_list = sorted(new_list, key= lambda car: car["Price Delta"])

    return new_list


if __name__ == "__main__":
    try:
        car_urls = getTrueCarResultsUrls(year_min, make, model)
        car_dicts = checkCarFax(car_urls)
        getTrueCarPricesAndSylesAndMilage(car_dicts)
        getTrueCarDetails(car_dicts)
        getKbbPrices(car_dicts)
        slimmed_data = getResults(car_dicts)


        print("Found {} cars".format(len(slimmed_data)))
        for car in slimmed_data:
            print(car)
            print('\n')
     except Exception as e:
        print(e)
        input("Press enter to quit")
