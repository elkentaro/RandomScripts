#!/bin/bash

# File paths
INPUT_FILE="amazon_list.csv"
OUTPUT_FILE="amazon_list_updated.csv"
TEMP_FILE="price_check_log.html"

# User-Agent to simulate a browser request
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"

# Function to fetch price from an Amazon URL
fetch_price() {
  local url="$1"
  
  # Download the HTML content
  curl -s -A "$USER_AGENT" "$url" -o "$TEMP_FILE"
  
  # Extract the first price instance from the HTML
  local price=$(grep -oP '<span class="a-price-whole">\K[0-9,]+' "$TEMP_FILE" | sed 's/,//g' | head -n 1)
  
  # Return the price or empty string if not found
  echo "$price"
}

# Function to monitor prices
monitor_prices() {
  echo "Checking prices..."
  echo "URL,Product Name,Price,Change" > "$OUTPUT_FILE"  # Prepare the output file with a "Change" column
  
  while IFS=, read -r url product_name old_price; do
    if [[ "$url" == "URL" ]]; then
      continue  # Skip the header row
    fi
    
    # Fetch the current price
    current_price=$(fetch_price "$url")
    
    # Validate the fetched price
    if [[ -z "$current_price" ]]; then
      echo "Could not fetch price for $product_name. Skipping..."
      continue
    fi
    
    echo "Product: $product_name"
    echo "Old Price: $old_price"
    echo "Current Price: $current_price"
    
    # Compare prices and determine the change
    if (( current_price < old_price )); then
      change="drop"
      echo "Price drop detected for $product_name: ¥$old_price → ¥$current_price"
    elif (( current_price > old_price )); then
      change="increase"
      echo "Price increased for $product_name: ¥$old_price → ¥$current_price"
    else
      change="no change"
      echo "No price change for $product_name."
    fi
    
    # Append the updated product details and change status to the output file
    echo "$url,$product_name,$current_price,$change" >> "$OUTPUT_FILE"
  done < "$INPUT_FILE"
}

# Run the price monitoring function
monitor_prices
echo "Price monitoring complete. Updated prices saved to $OUTPUT_FILE."
