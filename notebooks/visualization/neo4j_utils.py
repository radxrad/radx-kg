#!/usr/bin/env python
# coding: utf-8
import os
import subprocess
import shutil
import requests
import gzip
import tarfile
import zipfile
import platform
import time

def download_http(url, filename, directory):
    with requests.get(url, stream=True) as r:
        with open(os.path.join(directory, filename), "wb") as f:
            shutil.copyfileobj(r.raw, f)
            
def untar(filename, directory):
    with tarfile.open(os.path.join(directory, filename)) as tf:
        tf.extractall(path=directory)
    
def unzip(filename, directory):
    with zipfile.ZipFile(os.path.join(directory, filename),"r") as zf:
        zf.extractall(path=directory)


def download_neo4j():
    version = os.getenv("NEO4J_VERSION")
    password = os.getenv("NEO4J_PASSWORD")
    # if install path is not set, install Neo4j into the current directory
    neo4j_install_path = os.getenv("NEO4J_INSTALL_PATH", ".")
    neo4j_home = os.path.join(neo4j_install_path, version)
    neo4j_bin = os.getenv("NEO4J_BIN", os.path.join(neo4j_home, "bin"))
    neo4j_admin = os.path.join(neo4j_bin, "neo4j-admin")
    
    if not os.path.isdir(neo4j_home):
        if platform.system() == "Windows":
            url = f"https://dist.neo4j.org/{version}-windows.zip"
            neo4j_admin = os.path.join(neo4j_bin, "neo4j-admin.bat")
            filename = f"{version}-windows.zip"
            download_http(url, filename, neo4j_install_path)
            unzip(filename, neo4j_install_path)

        else:
            url = f"https://dist.neo4j.org/{version}-unix.tar.gz"
            neo4j_admin = os.path.join(neo4j_bin, "neo4j-admin")
            filename = f"{version}-unix.tar.gz"
            download_http(url, filename, neo4j_install_path)
            untar(filename, neo4j_install_path)

        if os.path.exists(os.path.join(neo4j_install_path, filename)):
            os.remove(os.path.join(neo4j_install_path,filename))

        subprocess.run([neo4j_admin, "dbms", "set-initial-password", password])
                
        if platform.system() == "Windows":
            neo4j = os.path.join(neo4j_bin, "neo4j.bat")
            subprocess.run([neo4j, "install-service"])


def start():
    neo4j_home = os.getenv("NEO4J_HOME")
    neo4j_bin = os.getenv("NEO4J_BIN")
    
    if not os.path.isdir(neo4j_home):
        download_neo4j()
        
    if platform.system() == "Windows":
        neo4j = os.path.join(neo4j_bin, "neo4j.bat")
    else:
        neo4j = os.path.join(neo4j_bin, "neo4j")
                      
    subprocess.run([neo4j, "start"])
    
    check_status()


def stop():
    neo4j_bin = os.getenv("NEO4J_BIN")
    
    if platform.system() == "Windows":
        neo4j = os.path.join(neo4j_bin, "neo4j.bat")
    else:
        neo4j = os.path.join(neo4j_bin, "neo4j")
                             
    subprocess.run([neo4j, "stop"]) 


def check_status():
    # adopted from: https://github.com/neo-technology/neokit/blob/master/neorun.py
    success = False
    start_time = time.time()
    timeout = 60 * 4
    count = 0

    print("Launching server", end="")
    while not success:
        try:
            r = requests.get("http://localhost:7474")
            success = True
        except requests.exceptions.ConnectionError:
            success = False
            
        current_time = time.time()
        if current_time - start_time > timeout:
            print("Failed to start server in 4 mins.")
            return 1

        count += 1
        if count % 10 == 0:
            print(".", end="") 

        time.sleep(0.1)
        
    print(" running.")
    return 0


def parse_grass_file(grass_filename):
    # TODO try to use CSS library to parse this file.
    # TODO support grass files in JSON format, e.g., see  https://github.com/neo4j/neo4j-browser/blob/master/src/shared/services/grassUtils.ts
    
    styles = []
    node_default_style = {'diameter': '50px', 'color': '#A5ABB6', 'border-color': '#9AA1AC', 'border-width': '2px', 
                          'text-color-internal': '#FFFFFF', 'font-size': '10px', 'defaultCaption': '<id>', 'caption': 'name'}
    relationship_default_style = {'color': '#A5ABB6', 'shaft-width': '1px', 'font-size': '8px', 'padding': '3px', 
                                  'text-color-external': '#000000', 'text-color-internal': '#FFFFFF'}

    with open(grass_filename) as fp:
        lines = fp.readlines()
        for line in lines:
            line = line.strip()
            # start of a new block
            if '{' in line[-1]:
                style = node_default_style.copy()
                if line.startswith('node'):
                    style = node_default_style.copy()
                    style['type'] = 'node'
                    style['label'] = 'none'
                    if line.startswith('node.'):
                        label = line.split('{')[0]
                        label = label.replace('node.', '')
                        style['label'] = label.strip()
                if line.startswith('relationship'):
                    style = relationship_default_style.copy()
                    style['type'] = 'relationship'
                    style['label'] = 'none'
                    if line.startswith('relationship.'):
                        label = line.split('{')[0]
                        label = label.replace('relationship.', '')
                        style['label'] = label.strip()
                        
            # end of a block, store style
            elif '}' == line:
                 styles.append(style)
                    
            # within a block, capture style attribute
            else:
                items = line.split(':')
                key = items[0]
                value = items[1].strip()
                value = value.replace('{', '')
                value = value.replace('}', '')
                value = value.replace(';', '')
                value = value.replace('"', '')
                style[items[0]] = value
                
    return styles

def grass2dataframe(grass_filename):
    import pandas as pd
    neo4j_styles = parse_grass_file(grass_filename)
    df = pd.DataFrame(neo4j_styles)
    df.fillna('', inplace=True)
    
    return df

def neo4j2cytoscape_style(neo4j_styles):
    styles = []
    for style in neo4j_styles:
        if style.get('type') == 'node' and style.get('label') != 'none':
            styles.append({'selector': 'node[label="' + style.get('label') + '"]', 
                           'style': {'label': 'data(' + style.get('caption') + ')', 
                                     'font-size': style.get('font-size'),
                                     'background-color': style.get('color'), 
                                     'height': style.get('diameter'), 
                                     'width': style.get('diameter'),
                                     'text-max-width': style.get('diameter'),
                                     'text-wrap': 'wrap', 
                                     'text-valign': 'center', 
                                     'border-width': style.get('border-width'), 
                                     'border-color': style.get('border-color')
  
                                    }
                          }
                         )
        elif style.get('type') == 'node' and style.get('label') == 'none':
            styles.append({'selector': 'node', 
                           'style': {'label': 'data(' + style.get('caption') + ')', 
                                     'font-size': style.get('font-size'),
                                     'background-color': style.get('color'), 
                                     'height': style.get('diameter'), 
                                     'width': style.get('diameter'),
                                     'text-max-width': style.get('diameter'),
                                     'text-wrap': 'wrap', 
                                     'text-valign': 'center', 
                                     'border-width': style.get('border-width'), 
                                     'border-color': style.get('border-color')
                                    }
                          }
                         )
        # https://github.com/cytoscape/ipycytoscape/blob/master/examples/Ipycytoscape%20from%20Scratch.ipynb
        elif style.get('type') == 'relationship' and style.get('label') != 'none':
            styles.append({'selector': 'edge[name="' + style.get('label') + '"]', 
                           'style': {'label': 'data(' + style.get('caption') + ')',
                                     'font-size': style.get('font-size'),
                                     'line-color': style.get('color'),
                                     'width': style.get('shaft-width'),
                                     'target-arrow-color': style.get('color'),
                                     'text-rotation': 'autorotate', 
                                     'curve-style': 'bezier', 
                                     'target-arrow-shape': 'triangle',
                                     'target-arrow-color': style.get('color')
                                    }
                          }
                         )
        elif style.get('type') == 'relationship' and style.get('label') == 'none':
            styles.append({'selector': 'edge', 
                           'style': {'label': 'data(name)',
                                     'font-size': style.get('font-size'),
                                     'line-color': style.get('color'),
                                     'width': style.get('shaft-width'),
                                     'target-arrow-color': style.get('color'),
                                     'text-rotation': 'autorotate', 
                                     'curve-style': 'bezier', 
                                     'target-arrow-shape': 'triangle',
                                     'target-arrow-color': style.get('color')
                                    }
                          }
                         )
            
    return styles


def draw_graph(subgraph, grass_filename):
    import ipycytoscape
    neo4j_styles = parse_grass_file(grass_filename)
    cytoscape_styles = neo4j2cytoscape_style(neo4j_styles)
    widget = ipycytoscape.CytoscapeWidget()
    widget.graph.add_graph_from_neo4j(subgraph)
    widget.set_style(cytoscape_styles)
    
    return widget