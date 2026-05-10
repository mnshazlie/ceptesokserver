import sys
import os

# 1. Tell Python to look in your 'libs' folder for dependencies
# We use abspath to make sure it works even if you run it from a different folder
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_path, "libs"))

# 2. Now that the path is set, we can import uvicorn and your app
import uvicorn
from main import app

if __name__ == "__main__":
    # 3. Run the server locally
    uvicorn.run(app, host="127.0.0.1", port=2828)
