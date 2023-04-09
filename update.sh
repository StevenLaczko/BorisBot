#!/bin/bash
docker-compose down -t 5
# Perform a git pull and capture any error output
if ! git pull 2>&1 >/dev/null; then
      # If there's an error, stop the script and echo the error message
        echo "Error: git pull failed."
          exit 1
fi
# If the git pull succeeds, display a success message
echo "Git pull succeeded."

docker-compose up --build -d
