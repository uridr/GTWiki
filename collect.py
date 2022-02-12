from SPARQLWrapper import SPARQLWrapper, JSON
from collections import deque
from bs4 import BeautifulSoup

import requests
import json
import sys

# GLOBALS
wikipedia_endpoint_url = "https://en.wikipedia.org/wiki/REPLACE"
wikidata_endpoint_url  = "https://query.wikidata.org/sparql"
query = """PREFIX entity: <http://www.wikidata.org/entity/>
PREFIX property: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?subjectLabel ?predicateLabel ?object ?objectLabel
WHERE
{
?property rdf:type wikibase:Property .
?subject ?predicate ?object.
?property ?ref ?predicate.
?property rdfs:label ?predicateLabel.
?subject rdfs:label ?subjectLabel.
?object rdfs:label ?objectLabel.
FILTER (LANG(?subjectLabel) = 'en').
FILTER (LANG(?predicateLabel) = 'en').
FILTER (LANG(?objectLabel) = 'en').
VALUES(?subject) {(entity:REPLACE)}
}
"""
visit_entities = set([])
MAX_DEPTH = int(sys.argv[3])

def writeJSON2File(file, data):
	with open(file, 'w') as outfile:
		json.dump(data, outfile)

def backupOperation(rdf_file, text_file, version, iterations):
	rdf_name = './data/rdf_file_v' + str(version) + '_' + str(iterations) + '.json'
	writeJSON2File(rdf_name,rdf_file)

	text_name = './data/text_file_v' + str(version) + '_' + str(iterations) + '.json'
	writeJSON2File(text_name,text_file)

	print("Backup Operation Completed: Version("+str(version)+") Iteration("+str(iterations)+")")


# return the text in a list of paragraphs
def getWikiIntro(soup):

	intro_text = []
	paragraphs = 0
	for paragraph in soup.select('p'):
		text = paragraph.getText()

		if len(text) > 200:
			intro_text.append(paragraph.getText())
			paragraphs +=1

		if paragraphs == 4: break 

	return intro_text
	

def getSoup(url):                                                   # Try/Catch block to prevent Bad Content being processed.
	try:
		response = requests.get(url)     				
		return BeautifulSoup(response.text, "html.parser")                  
	except:
		print("Error: Bad Content, skipping link. Do not stop.")
		return None                                                 # Return None if the URL could not be processed. The Crawler will understand.

# return the main text content in a wikipedia page given a name
def getText(entity):
	# TODO
	url = wikipedia_endpoint_url.replace("REPLACE", entity)
	soup = getSoup(url)
	text = getWikiIntro(soup)
	return text

# return all the outgoing relations from a given entity in wikidata id
def getRDF(entity_id):
	# adjust user agent; see https://w.wiki/CX6
	user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
	sparql = SPARQLWrapper(wikidata_endpoint_url, agent=user_agent) 	
	
	entity_query = query.replace("REPLACE", entity_id)

	sparql.setQuery(entity_query)
	sparql.setReturnFormat(JSON)
	rdf = sparql.query().convert()

	return rdf['results']['bindings']

# returns new entities never scrapped before in the triplet form of node datastructure
def getNewEntities(rdf, entity_queue, depth):
	nodes = []
	if depth < MAX_DEPTH:
		for triplet in rdf:
			entity_id = triplet['object']['value'].replace('http://www.wikidata.org/entity/','')
			entity = triplet['objectLabel']['value']

			if entity_id not in visit_entities: 
				entity_queue.appendleft((entity_id, entity, depth + 1))
				visit_entities.add(entity_id)

	return entity_queue


# crawling: BFS policy
def explore(node, version):
	iterations = 0
	text_file = {}
	rdf_file  = {}

	entity_queue = deque()
	entity_queue.appendleft(node)            

	while len(entity_queue):
		try:
			entity_id, entity, depth = entity_queue.pop()

			rdf  = getRDF(entity_id)
			text = getText(entity)

			# both are identified with the same uid
			rdf_file[entity_id]  = rdf
			text_file[entity_id] = text

			entity_queue = getNewEntities(rdf, entity_queue, depth)

			if iterations % 10 == 0:
				backupOperation(rdf_file, text_file, version, iterations)
				rdf_file  = {}
				text_file = {}

			iterations += 1
		except:
			print("Error Occured: ID("+entity_id+")")

	backupOperation(rdf_file, text_file, version, iterations)


def main():
	# nodes as datastructure: (wikidata_id, wikipedia_name_page, depth)
	nodes 	= [(sys.argv[1], sys.argv[2], 0)]
	version = 1

	for origin_node in nodes:
		explore(origin_node, version)
		version += 1

	visit_json = {"visit_entities": list(visit_entities)}
	writeJSON2File("./data/visit_entities.json", visit_json)

if __name__ == '__main__':
	main()







