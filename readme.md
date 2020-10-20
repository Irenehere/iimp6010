# Course project for IIMP6010

## Introduction

This is a project for dynamic optimal route planning in Hong Kong based on real-time traffic data.

Traffic data is provided by [DATA.GOV.HK](https://data.gov.hk/sc-data/dataset/hk-td-sm_1-traffic-speed-map).

We implemente three algorithms for dynamic optimal route planning: static dijkstra algorithm,  Time-dependent shoretest path(TDSP)algorithm, 
Dynamic Routing Planning (DRP) algorithm.

We visualize our result through [gmplot](https://github.com/gmplot/gmplot).

(See iimp6010proj.ipynb for detailed documentation and usage.)

## requirements
* numpy
* pandas
* networkx
* geopy
* requests
* gmplot

## Usage demo
(See iimp6010proj.ipynb for detailed documentation and usage.)

* import package

`from City import *`

* new a city object

`city=City(historic_speed)`

* generate graph

`city.gen_graph(road_data_with_distance, nodes_info)`

* see available nodes

`print(city.G.nodes.data())`

* see available edges

`print(city.G.edges.data())`

* static mode

`path = city.static_shortest_path(source,target,time) 
#time format: hour+minute,eg 715, 1430,etc`

* online mode

`path=city.greedy_dynamic_shortest_path(source,target,time)`

* offline mode

`path=city.TDSP(source,target,time)`

* visualize nodes

`city.plot_nodes(city.G.nodes())
#default output: 'plot_nodes.html' under the same directory of this file`

* visualize roads

`city.plot_edges(city.G.edges())
#default output: 'plot_edges.html' under the same directory of this file`

* visualize shortest path

`city.plot_shortest_path(path,'plot_shortest_path.html')`
