import requests
from bs4 import BeautifulSoup

def get_lot_size(url):
    try:
        # Define headers with a User-Agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        }
        
        # Send GET request with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the li with class starting with PropertyLotSizeMetastyles__StyledPropertyLotSizeMeta
        lot_size_element = soup.find('li', class_=lambda x: x and x.startswith('PropertyLotSizeMetastyles__StyledPropertyLotSizeMeta'))
        
        if not lot_size_element:
            print("Lot size element not found.")
            return None
            
        # Find the span with class meta-value
        meta_value = lot_size_element.find('span', class_='meta-value')
        
        if not meta_value:
            print("Meta value span not found.")
            return None
            
        # Extract the text (e.g., "7,841")
        lot_size = meta_value.get_text(strip=True)
        
        return lot_size
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error processing content: {e}")
        return None

# Example usage
if __name__ == "__main__":
    url = "https://www.realtor.com/realestateandhomes-detail/3036-Larreta_Grand-Prairie_TX_75054_M82019-25487"
    lot_size = get_lot_size(url)
    if lot_size:
        print(f"Lot Size: {lot_size} sqft")
    else:
        print("Failed to retrieve lot size.")