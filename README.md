# RADx Digital Assets Knowledge Graph

**[WORK IN PROGRESS]**

The RADx Digital Assets Knowledge Graph (radx-kg) collects and links assets from the National Institutes of Health (NIH) [Rapid Acceleration of Diagnostics (RADx®)](https://www.nih.gov/research-training/medical-research-initiatives/radx). The goal of the RADx initiative is to speed innovation in the development, commercialization, and implementation of technologies for COVID-19 testing.

The RADx initiative includes the follwing projects:
- [RADx Radical (RADx-rad)](https://www.nih.gov/research-training/medical-research-initiatives/radx/radx-programs#radx-rad)
- [RADx Digital Health Technologies (RADx-DHT)](https://www.nih.gov/news-events/news-releases/nih-awards-contracts-develop-innovative-digital-health-technologies-covid-19)
- [RADx Tech (RADx-TECH)](https://www.nih.gov/research-training/medical-research-initiatives/radx/radx-programs#radx-tech)
- [RADx Underserved Populations (RADx-UP)](https://www.nih.gov/research-training/medical-research-initiatives/radx/radx-programs#radx-up)

The radx-kg links the following assets:
- [Funding Opportunities](kg/data/nodes/FundingOpportunity.csv)
- Funding Agencies
- [Grants](kg/data/nodes/Grant.csv)
- [Researchers](kg/data/nodes/Researcher.csv)
- [Organizations](kg/data/nodes/Organization.csv)
- Publications
- Datasets
- Patents
- Emergency Use Authorizations (EUAs)
- Software Products

## Directories and Files
data - Grant, dbGaP, and PI information about the RADx projects
kg - Node and relationship data and metadata files to create the Knowledge Graph
scripts - Contains a script to create a Neo4j Knowledge Graph from the files in the kg directory

## Citation
RADx-Rad Discoveries & Data: Consortium Coordination Center (DCC), radx-kg - Knowledge Graph of RADx electronic artifacts, Available online: https://github.com/radxrad/radx-kg (2023).

## Funding
Development of this application was supported by the OFFICE OF THE DIRECTOR, NATIONAL INSTITUTES OF HEALTH:

**RADx-Rad Discoveries & Data: Consortium Coordination Center Program Organization** ([7U24LM013755](https://reporter.nih.gov/project-details/10745886))
