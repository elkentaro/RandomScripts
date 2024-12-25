#!/bin/bash

# Source directory where files are stored
SOURCE_DIR="/path/to/files"

# Loop through all files in the source directory
find "$SOURCE_DIR" -type f | while read -r file; do
    
    # Extract filename and directory
    FILENAME=$(basename "$file")
    FILEDIR=$(dirname "$file")
    FILEEXT="${FILENAME##*.}"
    FILENAME_BASE="${FILENAME%.*}"
    
    # Create a backup directory specific to the file
    BACKUP_DIR="${FILEDIR}/${FILENAME_BASE}_dir"
    CHECKSUM_FILE="${BACKUP_DIR}/.checksum"
    
    # Ensure backup directory and checksum file exist
    mkdir -p "$BACKUP_DIR"
    touch "$CHECKSUM_FILE"
    
    # Calculate current file hash
    CURRENT_HASH=$(md5sum "$file" | awk '{print $1}')
    
    # Read previous hash from the checksum file
    STORED_HASH=$(grep "^$FILENAME " "$CHECKSUM_FILE" | awk '{print $2}')
    
    # Compare hashes
    if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
        # Create a timestamped backup
        TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
        BACKUP_FILE="${BACKUP_DIR}/${FILENAME_BASE}_${TIMESTAMP}.${FILEEXT}"
        
        # Copy the file to the backup directory
        cp "$file" "$BACKUP_FILE"
        echo "Backed up modified file: $file → $BACKUP_FILE"
        
        # Update the checksum file with the new hash
        grep -v "^$FILENAME " "$CHECKSUM_FILE" > "${CHECKSUM_FILE}.tmp"
        echo "$FILENAME $CURRENT_HASH" >> "${CHECKSUM_FILE}.tmp"
        mv "${CHECKSUM_FILE}.tmp" "$CHECKSUM_FILE"
    else
        echo "No changes detected for: $file"
    fi

done
