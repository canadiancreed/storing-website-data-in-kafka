import argparse
import http.client
import json
import random
import re
import requests
import sys
import time

import config

# Collects data from monitored websites, and returns it as a list of dictionary objects
# @sites_to_monitor_list - A list of websites to collect data from
# @response_regex - A regex string to filter response data
# @collected_data - Returns a list of dictionaries of the data collection
# @return - Returns a list of dictionaries containing specific data on each website submitted
def monitor_sites(sites_to_monitor_list, response_regex):

    collected_data = []

    for website in sites_to_monitor_list:
        
        current_website_data = {}

        try:
            res = requests.get(website)

            current_website_data["Elasped"] = res.elapsed
            current_website_data["Status Code"] = res.status_code
            current_website_data["Match Regex"] = response_regex
            current_website_data["Match"] = False

            if res.status_code == 200:
                matchResult = re.search(response_regex, res.text)

                if matchResult is not None:
                    current_website_data["Match"] = True
        except Exception as e:
            print(e)

        collected_data.append(current_website_data)
    
    return collected_data

# Create topic if one doesn't exist with that particular name
# @topic_name - The name of the topic to create in the kafka instance
# @return - Returns a dictioanry showing if the topic exists, and if it does, it's total partitions
def create_topic(topic_name):

    result = {"topic_exist":False}
    partitions = 10

    conn = http.client.HTTPSConnection(config.API_URL)

    payload = "{\"config\":{\"cleanup_policy\":\"delete\",\"compression_type\":\"snappy\",\"delete_retention_ms\":0,\"file_delete_delay_ms\":0,\"flush_messages\":0,\"flush_ms\":0,\"index_interval_bytes\":0,\"max_compaction_lag_ms\":1,\"max_message_bytes\":0,\"message_downconversion_enable\":true,\"message_format_version\":\"0.8.0\",\"message_timestamp_difference_max_ms\":0,\"message_timestamp_type\":\"CreateTime\",\"min_cleanable_dirty_ratio\":1,\"min_compaction_lag_ms\":0,\"min_insync_replicas\":1,\"preallocate\":true,\"retention_bytes\":-1,\"retention_ms\":2562047788015,\"segment_bytes\":14,\"segment_index_bytes\":0,\"segment_jitter_ms\":0,\"segment_ms\":1,\"unclean_leader_election_enable\":true},\"min_insync_replicas\":1,\"partitions\":" + str(partitions) + ",\"replication\":2,\"tags\":[{\"key\":\"string\",\"value\":\"string\"}],\"topic_name\":\"" + topic_name + "\"}"

    headers = {
        'content-type': "application/json",
        'Authorization': "Bearer " + config.AUTH_TOKEN
        }

    conn.request("POST", "/v1/project/" + config.PROJECT_NAME + "/service/" + config.SERVICE_NAME + "/topic", payload, headers)

    res = conn.getresponse()
    data = res.read()
    create_topic_data = json.loads(data)

    if "errors" in create_topic_data:
        sys.exit(create_topic_data['errors'][0]['message'] + ". Please view logs for more details.")
    else:
        result["topic_exist"] = True
        result["partitions"] = partitions

    return result

# Gets topic data if the specified topic exists
# @topic_name - The name of the topic to create in the kafka instance
# @return - Returns a dictioanry showing if the topic exists, and if it does, it's total partitions
def get_topic_data(topic_name):

    result = {"topic_exist":False}

    conn = http.client.HTTPSConnection(config.API_URL)

    headers = { 'Authorization': "Bearer " + config.AUTH_TOKEN }

    conn.request("GET", "/v1/project/" + config.PROJECT_NAME + "/service/" + config.SERVICE_NAME + "/topic", headers=headers)

    res = conn.getresponse()
    data = res.read()
    topic_data_collection = json.loads(data)

    try:
        for topic_data in topic_data_collection['topics']:
            if topic_data['topic_name'] == topic_name:
                result["topic_exist"] = True
                result["partitions"] = topic_data['partitions']
                break
    except Exception:
        sys.exit("Could not get topic data due to " + topic_data_collection['errors'][0]['message'] + ". Shutting down.")

    return result

# Inserts message into kafka topic
# @payload_list - A list of data to insert into the specified topic
# @topic_name - The name of the topic to use
# @partition - The number of the partition to use for inserts
def produce_message(payload_list, topic_name, partition):

    conn = http.client.HTTPSConnection(config.API_URL)

    for payload_entry in payload_list:
        records = "["

        for count, key in enumerate(payload_entry.keys()):
            if count > 0:
                records = records + ","
    
            records = records + "{\"key\":\"" + key + "\",\"partition\":" + partition + ",\"value\":\"" + str(payload_entry[key]) + "\"}"
        
        records = records + "]"

        payload = "{\"format\":\"json\",\"key_schema\":\"stringstringstring\",\"key_schema_id\":1,\"records\":" + records + ",\"value_schema\":\"stringstringstring\",\"value_schema_id\":1}"

        headers = {
            'content-type': "application/json",
            'Authorization': "Bearer " + config.AUTH_TOKEN
            }

        try:
            conn.request("POST", "/v1/project/" + config.PROJECT_NAME + "/service/" + config.SERVICE_NAME + "/kafka/rest/topics/" + topic_name + "/produce", payload, headers)
        except Exception as e:
            sys.exit("Error with payload json contents. " + e + ".")

        res = conn.getresponse()
        data = res.read()
        message_insert_result = json.loads(data)

        if "errors" in message_insert_result:
            sys.exit(message_insert_result['errors'][0]['message'] + ". Please view logs for more details.")

# Parses all command line input, with help and detailed explanation for users
# @return - Returns a collection of submitted command line arguements
def parse_command_line_input():
    parser = argparse.ArgumentParser(
        prog = 'Website Monitoring Tool',
        description = 'Collects data on specified websites.'
    )
    parser.add_argument('-w', '--websites', dest='sites_to_monitor_list', required=True, help='Takes one or more comma delimited website URLs')
    parser.add_argument('-t', '--topic', dest='topic', default='', required=True, help='Specifies which topic to store data within. Will creater if one does not exist.')
    parser.add_argument('-r', '--regex', dest='response_regex', default='', required=False, help='Optional parameter to take regex for response content search')
    
    args = parser.parse_args()

    return args


if __name__ == '__main__':

    args = parse_command_line_input()

    topic_check_result = get_topic_data(args.topic)

    if topic_check_result['topic_exist'] is False:
        topic_check_result = create_topic(args.topic)

    selected_partition = str(random.randint(0, topic_check_result['partitions']))

    # Everything after this line will be wrapped in a while loop, executed every 30 seconds. 
    while True:
        collected_data_list = monitor_sites(args.sites_to_monitor_list.split(','), args.response_regex)

        produce_message(collected_data_list, args.topic, selected_partition)

        time.sleep(30)

