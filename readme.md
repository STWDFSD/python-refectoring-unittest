# Testing Instructions

**Current date:** 2025-01-29  

## Overview
This document provides step-by-step instructions for setting up your environment and running tests for the project.

## Instructions for Running the Tests

### 1. Set Up Your Environment
Ensure that you have Python and Node.js installed on your machine. It is recommended to use:
- Python 3.7.0 or higher
- Node v18.19.0 or higher

### 2. Create a Virtual Environment (Optional but Recommended)
Creating a virtual environment helps manage dependencies for your project. To create and activate a virtual environment, follow these steps:

```bash
# Create a virtual environment (for example, named 'venv')
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Required Packages
To install the necessary packages, create a `requirements.txt` file with your dependencies, then run the following command:

```bash
pip install -r requirements.txt
```

### 4. Set Up Backend Environment
You need to run the Express backend you built for test API processing. Execute the following commands:

```bash
npm i -f
node server.js
```

Check if the server is running by visiting [http://localhost:3001](http://localhost:3001) in your web browser.

### 5. Run the Tests
With everything set up, you can now run the tests using `pytest`. Open your terminal, navigate to the directory where your test files are located, and execute:

```bash
pytest test/ -v
```     