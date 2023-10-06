#!/bin/bash
# 
# This script runs the Neo4j bulk data import.
#
# Place a copy of this script outside this Git Repository and set the environment variables below.
# See instructions to create a Neo4j KG using this script: https://github.com/sbl-sdsc/kg-import#kg-import
#

# Absolute path to Neo4j home directory
#    Add quotes if the path contains spaces, e.g.,
#    export NEO4J_HOME="/Users/User/Library/Application Support/Neo4j Desktop/Application/relate-data/dbmss/dbms-0a85af40-86b9-4245-8d96-f51dba4acdc0"
export NEO4J_HOME="/Users/Peter/Library/Application Support/Neo4j Desktop/Application/relate-data/dbmss/dbms-df0dc0ef-1c96-4129-a292-e9f5caa39614"

# Absolute path to Neo4j bin directory
#    On MacOS: NEO4J_BIN="$NEO4J_HOME"/bin
export NEO4J_BIN="$NEO4J_HOME"/bin

export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=neo4jdemo
export NEO4J_DATABASE=neo4j

# Uncomment the export statement below to set an optional Neo4j Graph Stylesheet (GraSS)
#   A GraSS file can be exported from the Neo4j browser by running the :style command and then clicking the download icon.
#   Example GraSS from this repo:
#   export NEO4J_STYLESHEET_URL=https://raw.githubusercontent.com/sbl-sdsc/kg-import/main/styles/style.grass

#export NEO4J_STYLESHEET_URL=<url_of_neo4j_grass_file>

# Absolute paths to node and relationship metadata file directories
export NEO4J_METADATA=/Users/Peter/GitRepositories/radx-kg/kg/metadata

# Absolute paths to node and relationship data file directories
export NEO4J_DATA=/Users/Peter/GitRepositories/radx-kg/kg/data

# Absolute path to kg-import Git repository
export KGIMPORT_GITREPO=/Users/Peter/GitRepositories/kg-import

# Run the Neo4j bulk data import
$KGIMPORT_GITREPO/scripts/neo4j_bulk_import.sh
