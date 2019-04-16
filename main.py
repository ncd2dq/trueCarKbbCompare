
'''
truecar.com > price new/used > dodge/charger/33063 > 2017-MAX > IF free car fax report (exclude accident / damage / rental)

kellybluebook.com > price new/used > used > price without added option > buy from a dealer  > fair purchase price (single value)


List top 10, sort by difference between listend and kelly blue book value, url to true car page > output a .txt doc


# Input make / model / min year

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
    Converts car_urls to dictionaries
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
    {'found': True, 'carfax_url': 'https://www.carfax.com/VehicleHistory/p/Report.cfx?vin=2C3CDZFJ9JH236377&amp;csearch=0&amp;partner=GAZ_0', 'CarFax Clean': True, 'car_url': 'https://www.truecar.com/used-cars-for-sale/listing/2C3CDZFJ9JH236377/2018-dodge-challenger/'}
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
    Scrape year make model from url
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
