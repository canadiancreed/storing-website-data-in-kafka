Website monitoring for Aiven Kafka installations
================================================

This application will allow for users to collect monitoring data on specified websites, and perform the following actions on the collected data

- stores the connection speed to the specified website, status code return, and if there were any matches with the specified regex pattern
- stores the data in the specified topic, creating the topic if it does not exist on the specified kafka instance

Pre-configuration requirements
------------------------------

You can use this code in a containerization technology of your choice, or use it as a lamdba function that is consistently running. The only requirement 
is that it has Python v3 installed. No special libraries were used with this codebase that would need to be installed. Before executing, make sure that 
you have the following configured:

- A kafka installation setup and online through Aiven, a middleware for cloud services that can be hosted on multiple cloud providers. You'll need the project and kakfa service name to save as PROJECT_NAME and SERVICE_Name in config.py
- Having Apache Kafka REST API enabled for your Kafka instance. 
- Create an authentication token and capture the full token. You'll save this in the AUTH_TOKEN variable in config.py
- The URL for the avien API. This is currently api.aiven.io. This is saved as API_URL in config.py

Have both config.py and main.py on the same directory wherever you deploy this application too.

Using the application
---------------------

The application takes three command line variables, two of which are required.

- -w Websites to monitor - This is taken in as a string of comman seperated values. URLS must be fully formed. This is a required field
- -t Topic name - This is the topic that all data will be saved within. This is a required field
- -r Regex Match - This supplies the regex pattern to scan all returned site data. This is an optional field.

Here's a sample that monitors google.com and cbc.ca, storing the data in atopic named test, looking for matches to a regex that matches any instances of Google

> python -w "http://www.google.com,http://cbc.ca" -t test -r "(?:Google)"

Plans for version 2.0
---------------------

- Having auth token stored in a more secure manner, mainly through a secret management system like vault
