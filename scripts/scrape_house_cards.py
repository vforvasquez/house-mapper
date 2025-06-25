import json
from bs4 import BeautifulSoup
import re
import os

def load_existing_houses(filename):
    """Load existing houses from JSON file if it exists."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"No existing file found at '{filename}'. Starting fresh.")
        return {}
    except Exception as e:
        print(f"Error loading existing houses from '{filename}': {str(e)}")
        return {}

def parse_house_data(html_file):
    # Read HTML content from file
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{html_file}' not found.")
        return {}
    except Exception as e:
        print(f"Error reading file '{html_file}': {str(e)}")
        return {}
    
    # Create BeautifulSoup object
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Dictionary to store houses from this parse
    houses = {}
    
    # Find property cards with data-test="PropertyListCard-wrapper"
    property_cards = soup.find_all('div', attrs={'data-test': 'PropertyListCard-wrapper'})
    print(f"Found {len(property_cards)} property cards")
    
    valid_cards_processed = 0
    seen_mls_ids = set()
    
    for i, card in enumerate(property_cards, 1):
        try:
            # print(f"Processing card {i}")
            house_data = {}
            
            # Extract Image
            img = card.find('img')
            img_src = ''
            if img and img.get('src'):
                img_src = img.get('src')
                if 'listCardFallBackImage' in img_src:
                    # print(f"Card {i}: Found placeholder image, treating as no image")
                    img_src = ''
            else:
                print(f"cannot find image for {i}")
                
            house_data['image'] = img_src
            
            # Extract Price
            price = card.find('span', {'data-testid': 'data-price-row'})
            house_data['price'] = price.text.strip() if price else ''
            
            # Extract Bedrooms, Bathrooms, Square Feet
            details = card.find('span', class_=re.compile('StyledPropertyCardHomeDetails'))
            if details:
                detail_spans = details.find_all('span')
                house_data['bedrooms'] = ''
                house_data['bathrooms'] = ''
                house_data['square_feet'] = ''
                for span in detail_spans:
                    text = span.text.strip()
                    if 'bds' in text:
                        house_data['bedrooms'] = span.find('b').text.strip() if span.find('b') else ''
                    elif 'ba' in text:
                        house_data['bathrooms'] = span.find('b').text.strip() if span.find('b') else ''
                    elif 'sqft' in text:
                        house_data['square_feet'] = span.find('b').text.strip().replace(',', '') if span.find('b') else ''
            else:
                house_data['bedrooms'] = ''
                house_data['bathrooms'] = ''
                house_data['square_feet'] = ''
            
            # Extract Details URL
            link = card.find('a', class_=re.compile('StyledPropertyCardDataArea'))
            house_data['details_url'] = f"https://www.zillow.com/{link['href']}" if link and 'href' in link.attrs else ''
            
            # Extract Address
            address = link.find('address') if link else None
            house_data['address'] = address.text.strip() if address else ''
            
            # Extract MLS ID
            mls = card.find('div', string=re.compile(r'MLS ID'))
            mls_id = ''
            if mls:
                mls_text = mls.text.strip()
                digits = ''.join(re.findall(r'\d+', mls_text))
                mls_id = digits if digits else ''
                # print(f"Card {i}: MLS ID: {mls_id} (from text: {mls_text})")
            else:
                print(f"Card {i}: No MLS ID found")
            
            # Only process valid cards with unique MLS ID
            if mls_id and mls_id not in seen_mls_ids:
                houses[mls_id] = house_data
                seen_mls_ids.add(mls_id)
                valid_cards_processed += 1
                # print(f"Card {i}: Added/Updated house with MLS ID {mls_id}")
            else:
                print(f"Card {i}: Skipped (No MLS ID or duplicate MLS ID)")
                
        except Exception as e:
            print(f"Card {i}: Error processing: {str(e)}")
            continue
    
    print(f"\nProcessed {valid_cards_processed} valid cards out of {len(property_cards)} total")
    return houses

def save_to_json(data, filename):
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def update_and_save_houses(new_houses, output_file):
    print(f"new_houses: {len(new_houses)}")
    """Load existing houses, update with new data, and save."""
    # Load existing houses
    existing_houses = load_existing_houses(output_file)
    print(f"existing houses: {len(existing_houses)}")
    
    # Update existing houses and append new ones
    updated_count = 0
    new_count = 0
    
    for mls_id, house_data in new_houses.items():
        print(f"mls_id: {mls_id}")
        if mls_id in existing_houses:
            existing_houses[mls_id].update(house_data)
            updated_count += 1
            # print(f"Updated house with MLS ID {mls_id}")
        else:
            existing_houses[mls_id] = house_data
            new_count += 1
            # print(f"Added new house with MLS ID {mls_id}")
    
    print(f"\nUpdated {updated_count} existing houses and added {new_count} new houses")
    
    # Save the updated houses
    save_to_json(existing_houses, output_file)

# Main execution
if __name__ == "__main__":
    # Define paths relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), 'data')
    input_file = os.path.join(data_dir, 'cards.html')
    output_file = os.path.join(data_dir, 'saved_houses.json')
    
    house_data = parse_house_data(input_file)
    update_and_save_houses(house_data, output_file)