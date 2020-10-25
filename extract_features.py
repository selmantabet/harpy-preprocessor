# HARPY Joy JSON Feature Extraction V3.2b
#
# Designed by: Selman Tabet
#
# Changelog:
#
# [CODE]
#
# - Compartmentalized MAC mapper and extract feature functions under separate function definitions rather than a single script.
# - Execution may now be done via CLI by calling HARPY.py and adding the required arguments. Pass parameter -h or --help for details.
# - Improved path concatenation for POSIX/NT interoperability.
#

import os
import json
import datetime
import csv
import sys
import pandas as pd
from ipwhois import IPWhois
'''
Features List:
-------------
Total Sleep Time: is the total time of no activity
---------------------------------------------------------------------------------------
Total Active Time: is the total time of activity
---------------------------------------------------------------------------------------
Total Flow Volume: number of bytes (sent/received) by the IoT device
---------------------------------------------------------------------------------------
Flow Rate: Total Flow Volume / Total Active Time
---------------------------------------------------------------------------------------
Average Packet Size (number of bytes sent/received / number of packets sent/recieved)
---------------------------------------------------------------------------------------
Number of servers (excluding DNS (53) and NTP (123))
---------------------------------------------------------------------------------------
RDAP Registration Name along with number of flows for each resolved name. Stored as dict.
---------------------------------------------------------------------------------------
Number of protocols (based on destination port number)
---------------------------------------------------------------------------------------
Number of unique DNS requests. (based on qn and rn in joy tool)
DNS Interval: total time for using DNS
---------------------------------------------------------------------------------------
NTP interval: total time for using NTP
'''

'''
1- Select the period
2- Select the input file (2016, 2018, or all)
3- Add an extension to the input file name to indicate the period such as _1Min, _10Min, and so on.
4- Make sure only one day_co loop out of the 3 loops is commented out (1-21 for 2016, 21-48 for 2018, 1-48 for all)
'''

def extract_features(path, interval_time): # Installation path and and integer interval length in minutes.
    print("Selected time interval: " + str(interval_time) + " minutes")
    period_time = 60 * interval_time  #Convert from minutes to seconds
    app_directory = path
    features_file_name = os.path.join(app_directory, 'csv_files', 'output_' + str(interval_time) + 'm.csv')

    # Prepare writer to write extracted features for device_co
    features_csv = open(features_file_name, 'w')
    features_writer = csv.writer(features_csv, delimiter=',')

    features_writer.writerow(['total_sleep_time', 'total_active_time', 'total_flow_volume', 'flow_rate', 'avg_packet_size', 'num_servers', 'num_protocols', 'uniq_dns', 'dns_interval', 'ntp_interval', 'device_co', 'rdap_asn'])
    overall_ports_dict = {}
    overall_dns_dict = {}
    whois_record = {}

    for device_co in range(1, 32):    
        # Process all days for device_co
        #for day_co in range(1, 6):
        for day_co in range(1, 21):     # for 2016 dataset
            # Read flows from flows file containing 1 day data
            flows_file_name = os.path.join(app_directory, 'json_files', str(day_co) + '_' + str(device_co) + '.json')
            print('Processing ' + flows_file_name + ' ...')
            flows_file = open(flows_file_name, 'r')
            flows = flows_file.readlines()
            flows_file.close()

            # Features list
            total_sleep_time = 0
            total_active_time = 0

            total_flow_volume = 0
            total_packets = 0

            servers_dic = {}
            rdap_asn_record = {"Not Resolved":0}
            ports_dic = {}
            dns_query_dic = {}

            dns_interval = 0
            ntp_interval = 0
        
            # Time management variables
            prev_end_time = 0
            period_start_time = 0
            period_flow_co = 0

            # Skip the first record, which stores Joy configurations used
            nu_of_flows = len(flows)
            for flow_co in range(1, nu_of_flows):
                # Collect features
                #print(flow_co)
                flow_data = json.loads(flows[flow_co])
                # Get times
                cur_start_time = datetime.datetime.utcfromtimestamp(flow_data['time_start'])
                cur_end_time = datetime.datetime.utcfromtimestamp(flow_data['time_end'])
                cur_total_seconds = int( (cur_end_time - cur_start_time).total_seconds() )
                total_active_time += cur_total_seconds
            
                # Get number of bytes and number of packets going out
                total_flow_volume += int(flow_data['bytes_out'])
                total_packets += int(flow_data['num_pkts_out'])
                # Get number of bytes and number of packets going in
                if 'bytes_in' in flow_data:
                    total_flow_volume += int(flow_data['bytes_in'])
                    total_packets += int(flow_data['num_pkts_in'])
            
                # Get source port
                #if flow_data['sp'] is not None:
                #    port = int(flow_data['sp'])
                #    if port not in ports_dic:
                #        ports_dic[port] = 1
                #    else:
                #        ports_dic[port] += 1

                # Get destination port
                port = 0
                if flow_data['dp'] is not None:
                    port = int(flow_data['dp'])
                    if port not in ports_dic:
                        ports_dic[port] = 1
                    else:
                        ports_dic[port] += 1
                    '''
                    # Overall ports dictionary
                    if port not in overall_ports_dict:
                        overall_ports_dict[port] = 1
                    else:
                        overall_ports_dict[port] += 1
                    '''
                    if port == 53:
                        dns_interval += cur_total_seconds
                    elif port == 123:
                        ntp_interval += cur_total_seconds

                # Get the server and WHOIS Record
                if port != 53 and port != 123:
                    server = flow_data['da']
                    if server not in whois_record:
                        try:
                            ip_query = IPWhois(server)
                            RDAP = ip_query.lookup_rdap(depth=1)
                            server_id = RDAP["asn_description"]
                            whois_record[server] = server_id
                        except:
                            server_id = "Not Resolved"
                    else:
                        server_id = whois_record[server]

                    if server not in servers_dic:
                        rdap_asn_record[server_id] = 1
                        servers_dic[server] = 1
                    else:
                        servers_dic[server] += 1
                        rdap_asn_record[server_id] += 1
                    
                # Get DNS query
                if 'dns' in flow_data:
                    for dns_query in flow_data['dns']:
                        #print(dns_query)
                        query = ''
                        if 'qn' in dns_query:
                            query = dns_query['qn']
                        elif 'rn' in dns_query:
                            query = dns_query['rn']
                    
                        if query != '':
                            if query not in dns_query_dic:
                                dns_query_dic[query] = 1
                            else:
                                dns_query_dic[query] += 1
                            '''
                            # Overall dns query dictionary
                            if query not in overall_dns_dict:
                                overall_dns_dict[query] = 1
                            else:
                                overall_dns_dict[query] += 1
                            '''

                if flow_co == 1:
                    period_start_time = cur_start_time
            
                if period_flow_co == 0:
                    period_flow_co = 1
                else:
                    period_flow_co += 1
                    cur_sleep_time = int( (cur_start_time - prev_end_time).total_seconds() )
                    # Could be 0 for overlapping flows (device is active)
                    if cur_sleep_time > 0:
                        total_sleep_time += cur_sleep_time

                    if (int( (cur_end_time - period_start_time).total_seconds() ) >= period_time):  # or (flow_co == (nu_of_flows-1)):
                        # Finalize features computations
                        flow_rate = 0
                        if total_active_time > 0:
                            flow_rate = total_flow_volume / total_active_time
                        avg_packet_size = 0
                        if total_packets > 0:
                            avg_packet_size = total_flow_volume / total_packets

                        # Save features
                        features_writer.writerow([total_sleep_time, total_active_time, total_flow_volume, flow_rate, avg_packet_size, len(servers_dic), len(ports_dic), len(dns_query_dic), dns_interval, ntp_interval, device_co, rdap_asn_record])
                    
                        # Reinitialize features
                        total_sleep_time = 0
                        total_active_time = 0
                        total_flow_volume = 0
                        total_packets = 0
                        servers_dic = {}
                        rdap_asn_record = {"Not Resolved":0}
                        ports_dic = {}
                        dns_query_dic = {}
                        dns_interval = 0
                        ntp_interval = 0
                        period_flow_co = 0
                        period_start_time = cur_end_time

                prev_end_time = cur_end_time


    features_csv.close()
    return features_file_name



def mac_map(mac_source, mac_target, output):
    print("Mapping MACs...")
    mac_src = pd.read_csv(mac_source)
    mapping = pd.read_csv(mac_target)
    mapped = mapping.merge(mac_src, on='device_co', how='left').rename(columns={'MAC Address':'MAC_address'})
    mapped.to_csv(output,index=False)
    print("Done.")
    return 0

'''
stats_csv = open(stats_file_name, 'w')
stats_writer = csv.writer(stats_csv, delimiter=',')
stats_writer.writerow([overall_ports_dict, overall_dns_dict])
stats_csv.close()
'''