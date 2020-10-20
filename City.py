import pandas as pd
import networkx as nx
from geopy.distance import geodesic
import xml.etree.ElementTree as ET
import requests
import gmplot
import numpy as np
import math

class City:
    def __init__(self, historic_speed):
        self.G = nx.Graph()
        self.historic_speed = historic_speed
        
    def gen_graph(self,road_data, nodes_info):
        '''
        update self.graph from road_data
        input: DataFrame: tsm_link_and_node_info_v2.xlsx
        '''
        #add nodes
        for index, row in nodes_info.iterrows():
            nodes_id = row['Node ID']
            eastings = row["Eastings"]
            northings = row["Northings"]
            long = row['wgsLong']
            lat = row['wgsLat']
            self.G.add_node(int(nodes_id),position=(eastings, northings), wgsposition = (long, lat))

        #add edges
        k = 0
        for index, row in road_data.iterrows():
#             start,end=row["Link ID"].split("-")
#             start,end=int(start),int(end)
            start = int(row['Start_node'])
            end = int(row['End_node'])
            self.G.add_edge(start,end,road_type=row["Road_Type"],region=row["Region"],
                            length=row['Distance'],speed=float("inf"), weight=float("inf"), edge_index = k)
            k += 1

    def update_current_speed(self, url="https://resource.data.one.gov.hk/td/speedmap.xml"):
        try:
            r = requests.get(url = url, params = None).content
        except:
            print("fail to get current speed information!")
            return -1
        root = ET.fromstring(r)
        for child in root:
            try:
                road=child[0].text
                speed=int(child[4].text)
                start,end=road.split("-")
                start,end=int(start),int(end)
                self.G.edges[(start,end)]["speed"]=speed
            except:
                print("fail to get the speed information on road {}-{}".format(start,end))
        return 1
    
    def update_expected_speed(self,timepoint, day = 0, source_url="https://api.data.gov.hk/v1/historical-archive/get-file?url=http%3A%2F%2Fresource.data.one.gov.hk%2Ftd%2Fspeedmap.xml&time="):
        """
        Here, we assume the user will travel at timepoint in day(default = 0).
        
        """
   
        if (timepoint >= 288):
            day += timepoint // 288
            timepoint =  timepoint % 288
   
            
        for edge in self.G.edges():
            edge_index = self.G.edges[edge]['edge_index']
            self.G.edges[edge]['speed'] = self.historic_speed[edge_index, day, timepoint]
            #self.G.edges[edge]['weight'] = math.ceil((self.G.edges[edge]['length']/(self.G.edges[edge]['speed']/3.6+0.000001))/300)
            self.G.edges[edge]['weight'] = math.ceil((self.G.edges[edge]['length']/(self.G.edges[edge]['speed']/3.6+0.000001))/10)

        try:
            for edge in self.G.edges():
                edge_index = self.G.edges[edge]['edge_index']
                self.G.edges[edge]['speed'] = self.historic_speed[edge_index, day, timepoint]
                #self.G.edges[edge]['weight'] = math.ceil((self.G.edges[edge]['length']/(self.G.edges[edge]['speed']/3.6+0.000001))/300)
                self.G.edges[edge]['weight'] = math.ceil((self.G.edges[edge]['length']/(self.G.edges[edge]['speed']/3.6+0.000001))/10)
        except:
            
            print('Error! Edge:', edge, edge_index)
            print('Length', self.G.edges[edge]['length'])
            print('Speed', self.G.edges[edge]['speed'])
                    
    
    def time2idx(self,time):
        
        '''conver time into index to update the speed
            input: time: eg 1430 means 2:30pm
            return: index in the 3rd dimension of historic_speed matrix'''
        hour=int(time/100)
        minute=time%100
        try:
            assert 0<=hour<=24
            assert 0<=minute<=60
        except: 
            print("time input error")
        return hour*12+int(minute/5)
    
    
    def greedy_dynamic_shortest_path(self,source, target, starttime, day = 0):
        '''
        偷懒(heuristic): greedy shortest path
        Algorithm:
        1 set current=source
        2 set path={source}
        3 repeat until current==target:
            update weight
            current <- second node in the shortest path from current to target
            add current into path
        '''
        starttime=self.time2idx(starttime)
        current_time = starttime
        current=source
        path=[current]
        while current!=target:
            self.update_expected_speed(current_time, day = 0)
#             self.update_current_speed()
            current=nx.shortest_path(self.G, source=current, target=target,weight="weight")[1]
#             print(nx.shortest_path(self.G, source=current, target=target))
            path.append(current)
#             print((path[-2], path[-1]))
            current_time += self.G.edges[(path[-2], path[-1])]['weight']           
            
            if (current_time >= 288):
                day += current_time // 288
                current_time =  current_time % 288              

#         return [path, current_time - starttime]
        return path
    
    
    def static_shortest_path(self, source, target, starttime, day = 0):
        """
        Give the travel plan given the traffic situation at the time of setting off.
        The pratical total travel time should be calculated given dynamic traffic situation.abs
        """
        starttime=self.time2idx(starttime)
        current_time = starttime
        current = source

        self.update_expected_speed(current_time, day)
        static_path = nx.shortest_path(self.G, source=current, target=target,weight="weight")
#         return 0 
        i = 1
#         print(static_path)
        while current != target:
                
            if (current_time >= 288):
                day += current_time // 288
                current_time =  current_time % 288
                
            self.update_expected_speed(current_time, day)
            next_node = static_path[i]
            i = i+1
#             print((current, next_node)) 
            current_time += self.G.edges[(current, next_node)]['weight']
            
            if (current_time >= 288):
                day += current_time // 288
                current_time =  current_time % 288
            
            current = next_node
#         return [static_path, current_time - starttime]
        return static_path
    
    def TDSP(self,start,end,starttime):
        '''time-dependent shortest path'''
        starttime=self.time2idx(starttime)
        G_expanded=nx.DiGraph()
        for node in self.G.nodes():
            for j in range(1000):
                G_expanded.add_node((node,j))
        for j in range(1000):
            self.update_expected_speed(starttime+j)
            for edge in self.G.edges():
                travel_time=self.G.edges[edge]['weight']
                G_expanded.add_edge((edge[0],j),(edge[1],travel_time+j),weight=travel_time)
                G_expanded.add_edge((edge[1],j),(edge[0],travel_time+j),weight=travel_time)
        for j in range(1000):
            if nx.has_path(G_expanded, (start,0), (end,j)):
                path=nx.shortest_path(G_expanded, source=(start,0), target=(end,j),weight="weight")
                return list(map(lambda x:x[0],path))
#         print(G_expanded.edges.data())
        return -1
    
    def plot_nodes(self, nodes_set):
        """
        Mark all the nodes in nodes_set on city map.
        """
        try:
            apikey = 'AIzaSyDaQ-bkg4iV5SiaSXxhrD4DHpJv465NwHc' # (your API key here)
            gmap = gmplot.GoogleMapPlotter.from_geocode('Hong Kong', apikey=apikey)
            attractions = []
            label=[]
            for index in nodes_set:
                lat = self.G.nodes[index]['wgsposition'][1]
                long = self.G.nodes[index]['wgsposition'][0]
                label.append(index)
                attractions.append((lat, long))
            attractions = zip(*attractions)
            gmap.scatter(
                *attractions, color = 'orange', label=label,alpha = 0.1, s = 10, ew = 10)
            gmap.draw('plot_nodes.html')    
            return 0
        except:
            print('Plot Error.')
            return -1
    
    def plot_edges(self, edges):
            """
            Plot the edges in list edges on city map.
            """
            apikey = 'AIzaSyDaQ-bkg4iV5SiaSXxhrD4DHpJv465NwHc' # (your API key here)
            gmap = gmplot.GoogleMapPlotter.from_geocode('Hong Kong', apikey=apikey)
            attractions = []
            for index in edges:
                start = index[0]
                end = index[1]
                attractions = []
                lat_start = self.G.nodes[start]['wgsposition'][1]
                long_start = self.G.nodes[start]['wgsposition'][0]
                lat_end = self.G.nodes[end]['wgsposition'][1]
                long_end = self.G.nodes[end]['wgsposition'][0]
                attractions.append((lat_start, long_start))
                attractions.append((lat_end, long_end))
                attractions = zip(*attractions)
                gmap.plot(
                *attractions, color = 'blue', alpha = 0.3, s = 10, ew = 10)
            gmap.draw('plot_edges.html')
    
    
    def plot_shortest_path(self, nodes_set,output):
        """
        Mark the shortest path on city map.
        Nodes_set should be a list, the first node and last node are Source and Target respectively.
        output:file name, eg 'plot_shortest_path.html'
        """
        apikey = 'AIzaSyDaQ-bkg4iV5SiaSXxhrD4DHpJv465NwHc' # (your API key here)
        gmap = gmplot.GoogleMapPlotter.from_geocode('Hong Kong', apikey=apikey)

        try:
            apikey = 'AIzaSyDaQ-bkg4iV5SiaSXxhrD4DHpJv465NwHc' # (your API key here)
            gmap = gmplot.GoogleMapPlotter.from_geocode('Hong Kong', apikey=apikey)
            
            #plot all roads
            attractions = []
            for index in self.G.edges:
                start = index[0]
                end = index[1]
                attractions = []
                lat_start = self.G.nodes[start]['wgsposition'][1]
                long_start = self.G.nodes[start]['wgsposition'][0]
                lat_end = self.G.nodes[end]['wgsposition'][1]
                long_end = self.G.nodes[end]['wgsposition'][0]
                attractions.append((lat_start, long_start))
                attractions.append((lat_end, long_end))
                attractions = zip(*attractions)
                gmap.plot(
                *attractions, color = 'blue', alpha = 0.3, s = 10, ew = 10) 
            
            #plot shortest path
            attractions = []
            last_node = nodes_set[0]
            last_lat = self.G.nodes[last_node]['wgsposition'][1]
            last_long = self.G.nodes[last_node]['wgsposition'][0]
            for index in nodes_set[1: ]:
                lat = self.G.nodes[index]['wgsposition'][1]
                long = self.G.nodes[index]['wgsposition'][0]
                attractions = []
                attractions.append((last_lat, last_long))
                attractions.append((lat, long))
                attractions = zip(*attractions)
                gmap.plot(
                *attractions, color = 'red', alpha = 0.3, s = 10, ew = 10)
                last_lat = lat 
                last_long = long

            source = nodes_set[0]
            lat = self.G.nodes[source]['wgsposition'][1]
            long = self.G.nodes[source]['wgsposition'][0]
            attractions = []
            attractions.append((lat, long))
            attractions = zip(*attractions)
            gmap.scatter(
                *attractions, color = 'orange', alpha = 0.1, s = 10, ew = 10, label = 'O')
            target = nodes_set[-1]
            lat = self.G.nodes[target]['wgsposition'][1]
            long = self.G.nodes[target]['wgsposition'][0]
            attractions = []
            attractions.append((lat, long))
            attractions = zip(*attractions)
            gmap.scatter(
                *attractions, color = 'red', alpha = 0.1, s = 10, ew = 10, label = 'D')
            gmap.draw(output)    
            return 0
        except:
            print('Plot Error.')
            return -1
        
